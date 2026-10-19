import copy
from datetime import date

import pytest
import spotipy

from musictags.domain.models import Album, Artist, Track
from musictags.infrastructure.spotify import SpotifyCatalog, tracks_from_search

# Trimmed from a real /v1/search?type=track response.
ICE_CREAM = {
    "album": {
        "album_type": "single",
        "artists": [{"name": "BLACKPINK", "type": "artist"}],
        "external_urls": {"spotify": "https://open.spotify.com/album/2VBb4LRcRSACOfJWRUgVZl"},
        "id": "2VBb4LRcRSACOfJWRUgVZl",
        "name": "Ice Cream (with Selena Gomez)",
        "release_date": "2020-08-28",
        "release_date_precision": "day",
        "total_tracks": 1,
        "type": "album",
    },
    "artists": [
        {"name": "BLACKPINK", "type": "artist", "uri": "spotify:artist:41MozSoPIsD1dJM0CLPjZF"},
        {"name": "Selena Gomez", "type": "artist", "uri": "spotify:artist:0C8ZW7ezQVs4URX5aX7Kqx"},
    ],
    "disc_number": 1,
    "duration_ms": 175813,
    "id": "4sVhXWKRMYtYV8ARMcuqXo",
    "name": "Ice Cream (with Selena Gomez)",
    "popularity": 70,
    "track_number": 1,
    "type": "track",
}


def response(*items):
    return {"tracks": {"href": "https://api.spotify.com/v1/search", "items": list(items)}}


def test_maps_recorded_track():
    assert tracks_from_search(response(ICE_CREAM)) == [
        Track(
            name="Ice Cream (with Selena Gomez)",
            track_number=1,
            disc_number=1,
            length=175.813,
            artists=(Artist("BLACKPINK"), Artist("Selena Gomez")),
            album=Album(
                id="2VBb4LRcRSACOfJWRUgVZl",
                name="Ice Cream (with Selena Gomez)",
                artists=(Artist("BLACKPINK"),),
                album_type="single",
                release_date=date(2020, 8, 28),
                total_tracks=1,
            ),
        )
    ]


def test_pads_coarse_release_dates():
    item = copy.deepcopy(ICE_CREAM)
    item["album"].update(release_date="1999", release_date_precision="year")
    [track] = tracks_from_search(response(item))
    assert track.album.release_date == date(1999, 1, 1)


def test_missing_optional_fields_fall_back_to_defaults():
    item = {"album": {"id": "2VBb4LRcRSACOfJWRUgVZl", "artists": []}, "artists": [{}]}
    [track] = tracks_from_search(response(item))
    assert track == Track(
        name="",
        track_number=0,
        disc_number=0,
        length=0.0,
        artists=(Artist(""),),
        album=Album(
            id="2VBb4LRcRSACOfJWRUgVZl",
            name="",
            artists=(),
            album_type="",
            release_date=None,
            total_tracks=0,
        ),
    )


def test_empty_result_list():
    assert tracks_from_search(response()) == []


@pytest.mark.parametrize(
    "bad",
    [
        None,
        {},
        {"tracks": None},
        {"tracks": {"items": None}},
        response("not an object"),
        response({**ICE_CREAM, "artists": []}),
        response({**ICE_CREAM, "artists": None}),
        response({k: v for k, v in ICE_CREAM.items() if k != "album"}),
        response({**ICE_CREAM, "track_number": "one"}),
        response({**ICE_CREAM, "duration_ms": None}),
        response({**ICE_CREAM, "album": {**ICE_CREAM["album"], "id": None}}),
        response({**ICE_CREAM, "album": {**ICE_CREAM["album"], "artists": None}}),
    ],
)
def test_rejects_malformed_responses(bad):
    with pytest.raises(RuntimeError, match="Spotify returned an invalid response"):
        tracks_from_search(bad)


class FakeSpotipy:
    def __init__(self, result=None, error=None):
        self.result = result if result is not None else response(ICE_CREAM)
        self.error = error
        self.calls = []

    def search(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.result


def test_search_builds_query_with_year():
    client = FakeSpotipy()
    tracks = SpotifyCatalog(client).search_tracks("BLACKPINK", "Ice Cream", 2020)

    assert client.calls == [
        {"q": "year:2020 artist:BLACKPINK track:Ice Cream", "limit": 20, "type": "track"}
    ]
    assert [t.name for t in tracks] == ["Ice Cream (with Selena Gomez)"]


def test_search_omits_year_when_not_given():
    client = FakeSpotipy()
    SpotifyCatalog(client).search_tracks("BLACKPINK", "Ice Cream", None)
    assert client.calls[0]["q"] == "artist:BLACKPINK track:Ice Cream"


def test_search_error_names_status_and_spotify_message():
    error = spotipy.SpotifyException(
        401,
        -1,
        "https://api.spotify.com/v1/search?q=x&type=track:\n The access token expired",
    )
    search = SpotifyCatalog(FakeSpotipy(error=error))

    with pytest.raises(RuntimeError) as info:
        search.search_tracks("a", "b", None)

    assert str(info.value) == "Spotify search failed (401): The access token expired"


def test_search_error_without_message():
    error = spotipy.SpotifyException(502, -1, "https://api.spotify.com/v1/search:\n None")
    with pytest.raises(RuntimeError, match=r"^Spotify search failed \(502\): No response body$"):
        SpotifyCatalog(FakeSpotipy(error=error)).search_tracks("a", "b", None)
