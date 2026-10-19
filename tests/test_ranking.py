import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from musictags.domain.models import Album, Artist
from musictags.domain.ranking import RankedAlbum, rank_albums
from musictags.domain.source import ReleaseHints
from musictags.infrastructure.spotify import albums_from_search
from factories import make_album

FIXTURES = Path(__file__).parent / "fixtures" / "spotify"


def search_fixture(name: str) -> list[Album]:
    return albums_from_search(json.loads((FIXTURES / name).read_text(encoding="utf-8")))


@pytest.fixture
def midnight_candidates() -> list[Album]:
    """The real album and the Cover Duo cover single, cover first so the
    ranking, not Spotify's order, has to put the album on top."""
    albums = search_fixture("search_albums_midnight_signal_no_artist.json")
    real = next(a for a in albums if a.name == "MIDNIGHT SIGNAL")
    cover = next(a for a in albums if a.name == "Midnight Signal (Cover)")
    assert cover.artists[0].name == "Cover Duo"
    assert (cover.total_tracks, cover.release_date) == (1, date(2025, 12, 8))
    return [cover, real]


@pytest.mark.parametrize("artist", ["NOVA", None])
def test_cover_single_ranks_below_the_real_album(midnight_candidates, artist):
    hints = ReleaseHints(album="MIDNIGHT SIGNAL", artist=artist, year=2025, track_count=14)

    ranked = rank_albums(hints, midnight_candidates)

    assert [r.album.name for r in ranked] == ["MIDNIGHT SIGNAL", "Midnight Signal (Cover)"]
    assert ranked[0].score > ranked[1].score


def test_artist_matches_any_album_artist_case_insensitively():
    # Spotify lists LATE NIGHT MOVES under "NOVA, ORBIT"; the hint may be either.
    joint = replace(make_album(name="Song"), artists=(Artist("NOVA"), Artist("ORBIT")))
    other = make_album(name="Song", artist="Someone Else")
    hints = ReleaseHints(album="Song", artist="orbit", year=None, track_count=3)

    ranked = rank_albums(hints, [other, joint])

    assert ranked[0].album is joint


def test_track_count_and_year_break_a_name_tie():
    single = make_album(name="Song", total_tracks=1, release_date=date(2024, 5, 1), album_id="a")
    album = make_album(name="Song", total_tracks=12, release_date=date(2025, 5, 1), album_id="b")
    wrong_year = make_album(
        name="Song", total_tracks=12, release_date=date(2019, 5, 1), album_id="c"
    )
    hints = ReleaseHints(album="Song", artist="Artist", year=2025, track_count=12)

    ranked = rank_albums(hints, [single, wrong_year, album])

    assert [r.album.id for r in ranked] == ["b", "c", "a"]


def test_ties_keep_spotify_order():
    first = make_album(album_id="first")
    second = make_album(album_id="second")
    hints = ReleaseHints(album=None, artist=None, year=None, track_count=3)

    ranked = rank_albums(hints, [first, second])

    assert ranked == [RankedAlbum(first, 0.0), RankedAlbum(second, 0.0)]


def test_unknown_release_date_gets_no_year_credit():
    undated = make_album(release_date=None, album_id="undated")
    dated = make_album(release_date=date(2020, 1, 1), album_id="dated")
    hints = ReleaseHints(album=None, artist=None, year=2020, track_count=3)

    ranked = rank_albums(hints, [undated, dated])

    assert [r.album.id for r in ranked] == ["dated", "undated"]
