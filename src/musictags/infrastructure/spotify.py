from typing import Any, Callable, Optional

import spotipy
from spotipy import SpotifyClientCredentials

from musictags.domain.models import Album, Artist, Track, parse_release_date

# Spotify's own default page size; spotipy would otherwise ask for 10.
SEARCH_LIMIT = 20
# The most tracks Spotify returns per album_tracks page.
ALBUM_TRACKS_PAGE = 50


class SpotifyCatalog:
    def __init__(self, client: spotipy.Spotify):
        self._client = client

    @classmethod
    def from_credentials(
        cls, client_id: Optional[str], client_secret: Optional[str]
    ) -> "SpotifyCatalog":
        # spotipy's credentials manager fetches and refreshes the token itself.
        return cls(
            spotipy.Spotify(
                client_credentials_manager=SpotifyClientCredentials(
                    client_id=client_id, client_secret=client_secret
                )
            )
        )

    def search_tracks(
        self, artist: str, name: str, year: Optional[int] = None
    ) -> list[Track]:
        query = _year_filter(year) + f"artist:{artist} track:{name}"
        response = _call(
            self._client.search, q=query, limit=SEARCH_LIMIT, type="track"
        )
        return tracks_from_search(response)

    def search_albums(
        self, artist: str, album: str, year: Optional[int] = None
    ) -> list[Album]:
        query = _year_filter(year) + f"artist:{artist} album:{album}"
        response = _call(
            self._client.search, q=query, limit=SEARCH_LIMIT, type="album"
        )
        return albums_from_search(response)

    def album(self, album_id: str) -> Album:
        return album_from_response(_call(self._client.album, album_id))

    def album_tracks(self, album: Album) -> list[Track]:
        tracks: list[Track] = []
        while True:
            page = _call(
                self._client.album_tracks,
                album.id,
                limit=ALBUM_TRACKS_PAGE,
                offset=len(tracks),
            )
            items = tracks_from_album_page(page, album)
            tracks += items
            if page.get("next") is None:
                return tracks
            # An empty page that claims more would re-request the same offset forever.
            if not items:
                raise _invalid("album tracks page is empty but has a next page")


def _year_filter(year: Optional[int]) -> str:
    return f"year:{year} " if year else ""


def _call(method: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    try:
        return method(*args, **kwargs)
    except spotipy.SpotifyException as exc:
        raise RuntimeError(
            f"Spotify search failed ({exc.http_status}): {_spotify_message(exc)}"
        ) from exc


def _spotify_message(exc: spotipy.SpotifyException) -> str:
    # spotipy prefixes the message with the request URL ("<url>:\n <message>").
    message = str(exc.msg).split(":\n ", 1)[-1].strip()
    return message if message and message != "None" else "No response body"


# Every response is untrusted: anything missing that the domain depends on
# raises RuntimeError rather than surfacing later as a KeyError.


def tracks_from_search(response: Any) -> list[Track]:
    """Map a /v1/search?type=track response to domain tracks."""
    tracks = _field(response, "tracks", dict, "search response")
    items = _field(tracks, "items", list, "tracks")
    return [_track(item, None) for item in items]


def albums_from_search(response: Any) -> list[Album]:
    """Map a /v1/search?type=album response to domain albums."""
    albums = _field(response, "albums", dict, "search response")
    items = _field(albums, "items", list, "albums")
    return [_album(item) for item in items]


def album_from_response(response: Any) -> Album:
    """Map a /v1/albums/{id} response to a domain album, ignoring its tracks."""
    return _album(response)


def tracks_from_album_page(page: Any, album: Album) -> list[Track]:
    """Map one /v1/albums/{id}/tracks page; its items carry no album object."""
    items = _field(page, "items", list, "album tracks page")
    return [_track(item, album) for item in items]


def _track(data: Any, album: Optional[Album]) -> Track:
    if not isinstance(data, dict):
        raise _invalid("track item is not an object")
    artists = _field(data, "artists", list, "track")
    if not artists:
        raise _invalid("track has no artists")
    if album is None:
        album = _album(_field(data, "album", dict, "track"))
    return Track(
        name=_text(data, "name"),
        track_number=_number(data, "track_number"),
        disc_number=_number(data, "disc_number"),
        length=_number(data, "duration_ms") / 1000,
        artists=tuple(_artist(a) for a in artists),
        album=album,
    )


def _artist(data: Any) -> Artist:
    if not isinstance(data, dict):
        raise _invalid("artist is not an object")
    return Artist(name=_text(data, "name"))


def _album(data: Any) -> Album:
    if not isinstance(data, dict):
        raise _invalid("album is not an object")
    album_id = _text(data, "id")
    # Without an ID the album's tracks cannot be fetched.
    if not album_id:
        raise _invalid("album has no 'id'")
    return Album(
        id=album_id,
        name=_text(data, "name"),
        artists=tuple(_artist(a) for a in _field(data, "artists", list, "album")),
        album_type=_text(data, "album_type"),
        release_date=parse_release_date(
            _text(data, "release_date"), _text(data, "release_date_precision")
        ),
        total_tracks=_number(data, "total_tracks"),
    )


def _field(data: Any, key: str, kind: type, owner: str) -> Any:
    value = data.get(key) if isinstance(data, dict) else None
    if not isinstance(value, kind):
        raise _invalid(f"{owner} has no '{key}' {kind.__name__}")
    return value


def _text(data: dict, key: str) -> str:
    value = data.get(key)
    return value if isinstance(value, str) else ""


def _number(data: dict, key: str) -> int:
    try:
        return int(data.get(key, 0))
    except (TypeError, ValueError):
        raise _invalid(f"'{key}' is not a number") from None


def _invalid(reason: str) -> RuntimeError:
    return RuntimeError(f"Spotify returned an invalid response: {reason}")
