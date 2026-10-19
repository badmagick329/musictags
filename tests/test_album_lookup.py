import copy
import json
from datetime import date
from pathlib import Path

import pytest
import spotipy

from musictags.domain.models import Album, Artist
from musictags.infrastructure.spotify import (
    SpotifyCatalog,
    album_from_response,
    albums_from_search,
    tracks_from_album_page,
)

FIXTURES = Path(__file__).parent / "fixtures" / "spotify"

MIDNIGHT_ID = "2Kbn6hMdh6bD50FmLB0eHb"
LATE_NIGHT_ID = "AiM6aoPb3alX9Sosg4uZZq"

MIDNIGHT_SIGNAL = Album(
    id=MIDNIGHT_ID,
    name="MIDNIGHT SIGNAL",
    artists=(Artist("NOVA"),),
    album_type="album",
    release_date=date(2025, 3, 14),
    total_tracks=14,
)
LATE_NIGHT_MOVES = Album(
    id=LATE_NIGHT_ID,
    name="LATE NIGHT MOVES",
    artists=(Artist("NOVA"), Artist("ORBIT")),
    album_type="single",
    release_date=date(2026, 5, 20),
    total_tracks=4,
)


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_maps_album_search():
    assert albums_from_search(
        fixture("search_albums_nova_midnight_signal.json")
    ) == [MIDNIGHT_SIGNAL]
    assert albums_from_search(
        fixture("search_albums_nova_late_night_moves.json")
    ) == [LATE_NIGHT_MOVES]


def test_album_search_without_artist_also_finds_cover_single():
    albums = albums_from_search(fixture("search_albums_midnight_signal_no_artist.json"))
    assert [(a.name, a.artists, a.total_tracks) for a in albums] == [
        ("MIDNIGHT SIGNAL", (Artist("NOVA"),), 14),
        ("Midnight Signal (Cover)", (Artist("Cover Duo"),), 1),
    ]


def test_maps_album_lookup():
    assert album_from_response(fixture("album_midnight_signal.json")) == MIDNIGHT_SIGNAL


def test_maps_midnight_signal_tracks():
    tracks = tracks_from_album_page(
        fixture("album_tracks_midnight_signal.json"), MIDNIGHT_SIGNAL
    )

    assert [(t.disc_number, t.track_number, t.name, t.length) for t in tracks] == [
        (1, 1, "MIDNIGHT SIGNAL - English Ver.", 173.413),
        (1, 2, "K.L.M (Kinder Louder Mood) [feat. ORBIT GEM] - English Ver.", 216.053),
        (1, 3, "ENGINE - English Ver.", 175.746),
        (1, 4, "Over The Wall (ORBIT) - English Ver.", 214.72),
        (1, 5, "MIDNIGHT SIGNAL - Chinese Ver.", 173.413),
        (1, 6, "K.L.M (Kinder Louder Mood) [feat. ORBIT GEM] - Chinese Ver.", 216.053),
        (1, 7, "ENGINE - Chinese Ver.", 175.76),
        (1, 8, "Over The Wall (ORBIT) - Chinese Ver.", 214.706),
        (1, 9, "FEVER (LEO & MIA) - English Edit", 170.653),
        (1, 10, "FEVER (LEO & MIA) - Spanish Edit", 170.653),
        (1, 11, "ECHO - RIN & SOL & KAI", 255.146),
        (1, 12, "Some Old Friend", 184.226),
        (1, 13, "Gray Goose", 186.693),
        (1, 14, "Drift", 195.946),
    ]
    assert tracks[1].artists == (Artist("NOVA"), Artist("ORBIT GEM"))
    assert tracks[11].artists == (Artist("NOVA"), Artist("ORBIT RIN"))
    assert all(t.album == MIDNIGHT_SIGNAL for t in tracks)


def test_late_night_moves_keeps_track_and_album_artist_order_apart():
    tracks = tracks_from_album_page(
        fixture("album_tracks_late_night_moves.json"), LATE_NIGHT_MOVES
    )

    assert [(t.track_number, t.name, t.length) for t in tracks] == [
        (1, "LATE NIGHT MOVES", 190.0),
        (2, "I Wander", 160.0),
        (3, "LATE NIGHT MOVES (Chinese Ver.)", 190.0),
        (4, "I Wander (Chinese Ver.)", 160.0),
    ]
    assert {t.artists for t in tracks} == {(Artist("ORBIT"), Artist("NOVA"))}
    assert tracks[0].album.artists == (Artist("NOVA"), Artist("ORBIT"))


class FakeSpotipy:
    """Serves album_tracks from a list of items, `page_size` at a time."""

    def __init__(self, track_items=(), page_size=50, error=None, pages=None):
        self.track_items = list(track_items)
        self.page_size = page_size
        self.error = error
        self.pages = pages
        self.calls = []

    def _maybe_fail(self):
        if self.error:
            raise self.error

    def search(self, **kwargs):
        self.calls.append(("search", kwargs))
        self._maybe_fail()
        return fixture("search_albums_nova_midnight_signal.json")

    def album(self, album_id):
        self.calls.append(("album", album_id))
        self._maybe_fail()
        return fixture("album_midnight_signal.json")

    def album_tracks(self, album_id, limit, offset):
        self.calls.append(("album_tracks", album_id, limit, offset))
        self._maybe_fail()
        if self.pages is not None:
            return self.pages.pop(0)
        end = offset + min(limit, self.page_size)
        more = end < len(self.track_items)
        return {
            "items": self.track_items[offset:end],
            "next": "https://api.spotify.com/v1/albums/x/tracks?offset=..." if more else None,
        }


def midnight_items():
    return fixture("album_tracks_midnight_signal.json")["items"]


def test_search_albums_builds_query_with_year():
    client = FakeSpotipy()
    albums = SpotifyCatalog(client).search_albums("NOVA", "MIDNIGHT SIGNAL", 2025)

    assert client.calls == [
        (
            "search",
            {"q": "year:2025 artist:NOVA album:MIDNIGHT SIGNAL", "limit": 20, "type": "album"},
        )
    ]
    assert albums == [MIDNIGHT_SIGNAL]


def test_search_albums_omits_year_when_not_given():
    client = FakeSpotipy()
    SpotifyCatalog(client).search_albums("NOVA", "MIDNIGHT SIGNAL", None)
    assert client.calls[0][1]["q"] == "artist:NOVA album:MIDNIGHT SIGNAL"


def test_album_fetches_by_id():
    client = FakeSpotipy()
    assert SpotifyCatalog(client).album(MIDNIGHT_ID) == MIDNIGHT_SIGNAL
    assert client.calls == [("album", MIDNIGHT_ID)]


def test_album_tracks_reads_every_page():
    client = FakeSpotipy(midnight_items(), page_size=10)
    tracks = SpotifyCatalog(client).album_tracks(MIDNIGHT_SIGNAL)

    assert [t.track_number for t in tracks] == list(range(1, 15))
    assert client.calls == [
        ("album_tracks", MIDNIGHT_ID, 50, 0),
        ("album_tracks", MIDNIGHT_ID, 50, 10),
    ]


def test_album_tracks_single_page():
    client = FakeSpotipy(midnight_items())
    tracks = SpotifyCatalog(client).album_tracks(MIDNIGHT_SIGNAL)
    assert len(tracks) == 14
    assert len(client.calls) == 1


def test_album_tracks_rejects_empty_page_claiming_more():
    client = FakeSpotipy(pages=[{"items": [], "next": "https://api.spotify.com/v1/more"}])
    with pytest.raises(RuntimeError, match="Spotify returned an invalid response"):
        SpotifyCatalog(client).album_tracks(MIDNIGHT_SIGNAL)


@pytest.mark.parametrize(
    "call",
    [
        lambda c: c.search_albums("a", "b", None),
        lambda c: c.album(MIDNIGHT_ID),
        lambda c: c.album_tracks(MIDNIGHT_SIGNAL),
    ],
    ids=["search_albums", "album", "album_tracks"],
)
def test_spotify_errors_name_status_and_message(call):
    error = spotipy.SpotifyException(
        400, -1, "https://api.spotify.com/v1/albums/x:\n Invalid base62 id"
    )
    with pytest.raises(RuntimeError) as info:
        call(SpotifyCatalog(FakeSpotipy(error=error)))
    assert str(info.value) == "Spotify search failed (400): Invalid base62 id"


def search_with(*items):
    return {"albums": {"items": list(items)}}


ALBUM_ITEM = fixture("search_albums_nova_midnight_signal.json")["albums"]["items"][0]


@pytest.mark.parametrize(
    "bad",
    [
        None,
        {},
        {"tracks": {"items": []}},
        {"albums": None},
        {"albums": {"items": None}},
        search_with("not an object"),
        search_with({**ALBUM_ITEM, "id": None}),
        search_with({**ALBUM_ITEM, "id": ""}),
        search_with({**ALBUM_ITEM, "artists": None}),
        search_with({**ALBUM_ITEM, "artists": ["NOVA"]}),
        search_with({**ALBUM_ITEM, "total_tracks": "fourteen"}),
    ],
)
def test_rejects_malformed_album_search(bad):
    with pytest.raises(RuntimeError, match="Spotify returned an invalid response"):
        albums_from_search(bad)


def test_rejects_malformed_album_lookup():
    with pytest.raises(RuntimeError, match="Spotify returned an invalid response"):
        album_from_response({"name": "MIDNIGHT SIGNAL"})


TRACK_ITEM = midnight_items()[0]


@pytest.mark.parametrize(
    "bad",
    [
        None,
        {"items": None},
        {"items": ["not an object"]},
        {"items": [{**TRACK_ITEM, "artists": []}]},
        {"items": [{**TRACK_ITEM, "duration_ms": "long"}]},
        {"items": [{**TRACK_ITEM, "disc_number": None}]},
    ],
)
def test_rejects_malformed_album_tracks_page(bad):
    with pytest.raises(RuntimeError, match="Spotify returned an invalid response"):
        tracks_from_album_page(copy.deepcopy(bad), MIDNIGHT_SIGNAL)
