from typing import Any, Optional

import spotipy
from spotipy import SpotifyClientCredentials

from musictags.domain.models import Album, Artist, Track, parse_release_date

# Spotify's own default page size; spotipy would otherwise ask for 10.
SEARCH_LIMIT = 20


class SpotifyTrackSearch:
    def __init__(self, client: spotipy.Spotify):
        self._client = client

    @classmethod
    def from_credentials(
        cls, client_id: Optional[str], client_secret: Optional[str]
    ) -> "SpotifyTrackSearch":
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
        query = f"year:{year} " if year else ""
        query += f"artist:{artist} track:{name}"
        try:
            response = self._client.search(
                q=query, limit=SEARCH_LIMIT, type="track"
            )
        except spotipy.SpotifyException as exc:
            raise RuntimeError(
                f"Spotify search failed ({exc.http_status}): {_spotify_message(exc)}"
            ) from exc
        return tracks_from_search(response)


def _spotify_message(exc: spotipy.SpotifyException) -> str:
    # spotipy prefixes the message with the request URL ("<url>:\n <message>").
    message = str(exc.msg).split(":\n ", 1)[-1].strip()
    return message if message and message != "None" else "No response body"


def tracks_from_search(response: Any) -> list[Track]:
    """Map a /v1/search?type=track response to domain tracks.

    The response is untrusted: anything missing that the domain depends on
    raises RuntimeError rather than surfacing later as a KeyError.
    """
    tracks = _field(response, "tracks", dict, "search response")
    items = _field(tracks, "items", list, "tracks")
    return [_track(item) for item in items]


def _track(data: Any) -> Track:
    if not isinstance(data, dict):
        raise _invalid("track item is not an object")
    artists = _field(data, "artists", list, "track")
    if not artists:
        raise _invalid("track has no artists")
    return Track(
        name=_text(data, "name"),
        track_number=_number(data, "track_number"),
        artists=tuple(_artist(a) for a in artists),
        album=_album(_field(data, "album", dict, "track")),
    )


def _artist(data: Any) -> Artist:
    if not isinstance(data, dict):
        raise _invalid("artist is not an object")
    return Artist(name=_text(data, "name"))


def _album(data: dict) -> Album:
    return Album(
        name=_text(data, "name"),
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
