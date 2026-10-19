import json
from pathlib import Path
from typing import Optional

import pytest

from musictags.domain.album_match import (
    SURE_TITLE_SIMILARITY,
    FileMatch,
    MatchConfidence,
    match_album,
    normalise_title,
    title_similarity,
)
from musictags.domain.models import Track
from musictags.domain.source import SourceFile
from musictags.infrastructure.spotify import albums_from_search, tracks_from_album_page
from factories import make_track

FIXTURES = Path(__file__).parent / "fixtures" / "spotify"

# Genie's titles and file lengths for 250314 MIDNIGHT SIGNAL, in track order.
# Genie writes Spotify's " - X" and "[feat. Y]" as " (X)" and "(Feat. Y)".
GENIE_MIDNIGHT = [
    ("MIDNIGHT SIGNAL (English Ver.)", 173.41),
    ("K.L.M (Kinder Louder Mood) (Feat. ORBIT GEM) (English Ver.)", 216.05),
    ("ENGINE (English Ver.)", 175.75),
    ("Over The Wall (ORBIT) (English Ver.)", 214.72),
    ("MIDNIGHT SIGNAL (Chinese Ver.)", 173.41),
    ("K.L.M (Kinder Louder Mood) (Feat. ORBIT GEM) (Chinese Ver.)", 216.05),
    ("ENGINE (Chinese Ver.)", 175.76),
    ("Over The Wall (ORBIT) (Chinese Ver.)", 214.71),
    ("FEVER (LEO & MIA) (English Edit)", 170.65),
    ("FEVER (LEO & MIA) (Spanish Edit)", 170.65),
    ("ECHO (RIN & SOL & KAI)", 255.15),
    ("Some Old Friend", 184.23),
    ("Gray Goose", 186.69),
    ("Drift", 195.95),
]


def album_tracks(search_fixture: str, tracks_fixture: str) -> list[Track]:
    search = json.loads((FIXTURES / search_fixture).read_text(encoding="utf-8"))
    album = albums_from_search(search)[0]
    page = json.loads((FIXTURES / tracks_fixture).read_text(encoding="utf-8"))
    return tracks_from_album_page(page, album)


@pytest.fixture
def midnight_tracks() -> list[Track]:
    return album_tracks(
        "search_albums_nova_midnight_signal.json", "album_tracks_midnight_signal.json"
    )


@pytest.fixture
def late_night_tracks() -> list[Track]:
    return album_tracks(
        "search_albums_nova_late_night_moves.json", "album_tracks_late_night_moves.json"
    )


def source_file(
    title: Optional[str], length: float, track_number: Optional[int], disc_number=None
) -> SourceFile:
    return SourceFile(
        path=Path(f"{track_number or 0:02}. {title}.flac"),
        length=length,
        track_number=track_number,
        disc_number=disc_number,
        title=title,
        album="MIDNIGHT SIGNAL",
        album_artist="NOVA & ORBIT",
        artist="NOVA & ORBIT",
        year=2025,
    )


def genie_files(numbers: Optional[list[int]] = None) -> list[SourceFile]:
    """The Genie files in track order, optionally carrying other track numbers."""
    numbers = numbers or list(range(1, 15))
    return [
        source_file(title, length, number)
        for (title, length), number in zip(GENIE_MIDNIGHT, numbers)
    ]


def assert_one_to_one(results: list[FileMatch]) -> None:
    tracks = [id(r.track) for r in results if r.track is not None]
    assert len(tracks) == len(set(tracks))


def assert_own_versions_sure(results: list[FileMatch], files: list[SourceFile], tracks):
    """Each Genie file i (track order) is paired, sure, with Spotify track i."""
    by_title = {title: index for index, (title, _) in enumerate(GENIE_MIDNIGHT)}
    assert [r.file for r in results] == files
    for result in results:
        assert result.confidence is MatchConfidence.SURE, result
        assert result.track is tracks[by_title[result.file.title]], result
    assert_one_to_one(results)


@pytest.mark.parametrize(
    "genie, spotify",
    [
        ("MIDNIGHT SIGNAL (English Ver.)", "MIDNIGHT SIGNAL - English Ver."),
        (
            "K.L.M (Kinder Louder Mood) (Feat. ORBIT GEM) (English Ver.)",
            "K.L.M (Kinder Louder Mood) [feat. ORBIT GEM] - English Ver.",
        ),
        ("FEVER (LEO & MIA) (English Edit)", "FEVER (LEO & MIA) - English Edit"),
        ("ECHO (RIN & SOL & KAI)", "ECHO - RIN & SOL & KAI"),
        ("Some Old Friend", "Some Old Friend"),
        ("Song (ft. X)", "Song [featuring X]"),
        ("Don’t Stop", "DON'T STOP"),
    ],
)
def test_normalise_title_makes_shop_and_spotify_styles_equal(genie, spotify):
    assert normalise_title(genie) == normalise_title(spotify)


def test_language_versions_are_not_similar_enough_to_be_sure(midnight_tracks):
    # The closest pair in the album: the long shared prefix dilutes the
    # difference, which is what SURE_TITLE_SIMILARITY must stay above.
    english, chinese = midnight_tracks[1].name, midnight_tracks[5].name
    assert title_similarity(english, chinese) < SURE_TITLE_SIMILARITY


def test_midnight_signal_pairs_every_file_with_its_own_version(midnight_tracks):
    files = genie_files()

    results = match_album(files, midnight_tracks)

    assert_own_versions_sure(results, files, midnight_tracks)


def test_late_night_moves_is_all_sure(late_night_tracks):
    # The old per-file flow already rewrote these titles to Spotify's names.
    files = [
        source_file("LATE NIGHT MOVES", 190.02, 1),
        source_file("I Wander", 159.98, 2),
        source_file("LATE NIGHT MOVES (Chinese Ver.)", 190.01, 3),
        source_file("I Wander (Chinese Ver.)", 160.03, 4),
    ]

    results = match_album(files, late_night_tracks)

    assert [r.confidence for r in results] == [MatchConfidence.SURE] * 4
    assert [r.track for r in results] == late_night_tracks


def test_shuffled_track_numbers_still_match_by_title_and_length(midnight_tracks):
    files = genie_files(numbers=list(range(14, 0, -1)))

    results = match_album(files, midnight_tracks)

    assert_own_versions_sure(results, files, midnight_tracks)


def test_language_versions_are_separated_by_title_when_numbers_are_swapped(
    midnight_tracks,
):
    # English 1-4 carry the Chinese numbers 5-8 and the other way round, so
    # number agreement points every same-length pair at the wrong version.
    files = genie_files(numbers=[5, 6, 7, 8, 1, 2, 3, 4, 10, 9, 11, 12, 13, 14])

    results = match_album(files, midnight_tracks)

    assert_own_versions_sure(results, files, midnight_tracks)


def test_results_follow_file_order_not_track_order(midnight_tracks):
    files = list(reversed(genie_files()))

    results = match_album(files, midnight_tracks)

    assert_own_versions_sure(results, files, midnight_tracks)


def test_a_file_missing_from_the_release_is_unmatched(midnight_tracks):
    # "Drift" is still free, but nothing about the bonus track resembles it.
    bonus = source_file("Bonus Track", 240.5, 14)
    files = genie_files()[:13] + [bonus]

    results = match_album(files, midnight_tracks)

    assert results[-1] == FileMatch(bonus, None, MatchConfidence.UNMATCHED, 0.0)
    assert_own_versions_sure(results[:13], files[:13], midnight_tracks)


def test_an_extra_file_is_unmatched_once_every_track_is_taken(midnight_tracks):
    # Same length and a near title, so only one-to-one assignment stops it.
    extra = source_file("MIDNIGHT SIGNAL (Japanese Ver.)", 173.41, 15)
    files = genie_files() + [extra]

    results = match_album(files, midnight_tracks)

    assert results[-1].confidence is MatchConfidence.UNMATCHED
    assert results[-1].track is None
    assert_own_versions_sure(results[:14], files[:14], midnight_tracks)


def test_an_extra_spotify_track_goes_unused(midnight_tracks):
    files = genie_files()[:13]

    results = match_album(files, midnight_tracks)

    assert_own_versions_sure(results, files, midnight_tracks)
    assert midnight_tracks[13] not in [r.track for r in results]


def test_another_language_version_is_assigned_but_unsure(midnight_tracks):
    english = source_file("MIDNIGHT SIGNAL (English Ver.)", 173.41, 1)
    chinese_track = midnight_tracks[4]

    [result] = match_album([english], [chinese_track])

    assert result.track is chinese_track
    assert result.confidence is MatchConfidence.UNSURE


def test_a_length_outside_two_seconds_is_unsure():
    file = source_file("Song", 185.0, 1)
    track = make_track(name="Song", length=180.0)

    [result] = match_album([file], [track])

    assert result.track is track
    assert result.confidence is MatchConfidence.UNSURE


def test_files_without_titles_match_by_length_and_number_but_never_sure(
    midnight_tracks,
):
    files = [
        source_file(None, length, number)
        for number, (_, length) in enumerate(GENIE_MIDNIGHT, 1)
    ]

    results = match_album(files, midnight_tracks)

    assert [r.track for r in results] == midnight_tracks
    assert {r.confidence for r in results} == {MatchConfidence.UNSURE}


def test_a_file_without_title_or_close_length_is_unmatched():
    file = source_file(None, 240.0, 1)

    [result] = match_album([file], [make_track(length=180.0)])

    assert result.confidence is MatchConfidence.UNMATCHED


def test_disc_number_disagreement_withholds_the_number_bonus():
    # Two discs with the same track number and no title to tell them apart:
    # only the disc number can decide.
    disc_one = make_track(name="Song", track_number=1, disc_number=1, length=180.0)
    disc_two = make_track(name="Song", track_number=1, disc_number=2, length=180.0)
    file = source_file(None, 180.0, 1, disc_number=2)

    [result] = match_album([file], [disc_one, disc_two])

    assert result.track is disc_two


def test_no_tracks_leaves_every_file_unmatched():
    results = match_album(genie_files()[:2], [])

    assert [r.confidence for r in results] == [MatchConfidence.UNMATCHED] * 2
