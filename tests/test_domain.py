import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
from factories import make_track

from musictags.domain.models import Album, Artist, Track, parse_release_date
from musictags.domain.naming import clean_name, suggest_track_name, track_filename
from musictags.domain.tags import stray_tags, track_tags
from musictags.infrastructure.spotify import albums_from_search, tracks_from_album_page

FIXTURES = Path(__file__).parent / "fixtures" / "spotify"


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_track_tags_maps_every_field():
    track = Track(
        name="Ice Cream",
        track_number=3,
        disc_number=1,
        length=175.813,
        artists=(Artist("BLACKPINK"), Artist("Selena Gomez")),
        album=Album(
            id="71O60S5gIJSIAhdnrDIh3N",
            name="THE ALBUM",
            artists=(Artist("BLACKPINK"),),
            album_type="album",
            release_date=date(2020, 10, 2),
            total_tracks=8,
        ),
    )

    assert track_tags(track) == {
        "ALBUM": "THE ALBUM",
        "ALBUMARTIST": "BLACKPINK",
        "ARTIST": "BLACKPINK",
        "ARTISTS": "BLACKPINK",
        "DATE": "2020-10-02",
        "TITLE": "Ice Cream",
        "TRACKNUMBER": "3",
        "TRACKTOTAL": "8",
    }


def test_track_tags_leaves_date_empty_when_release_date_unknown():
    assert track_tags(make_track(release_date=None))["DATE"] == ""


def test_track_tags_leaves_album_artist_empty_when_album_has_no_artists():
    track = make_track()
    track = replace(track, album=replace(track.album, artists=()))

    assert track_tags(track)["ALBUMARTIST"] == ""


def test_late_night_moves_artist_is_track_main_artist_and_album_artist_is_albums():
    # Spotify credits the tracks "ORBIT, NOVA" but the album "NOVA, ORBIT";
    # each tag must follow its own credit.
    [album] = albums_from_search(fixture("search_albums_nova_late_night_moves.json"))
    tracks = tracks_from_album_page(fixture("album_tracks_late_night_moves.json"), album)

    for track in tracks:
        tags = track_tags(track)
        assert (tags["ARTIST"], tags["ALBUMARTIST"]) == ("ORBIT", "NOVA")


# The tags a Genie FLAC arrives with, upper-cased as read.
GENIE_SOURCE_TAGS = {
    "ALBUM": ("LATE NIGHT MOVES",),
    "ALBUMTITLE": ("LATE NIGHT MOVES",),
    "ALBUMARTIST": ("NOVA / ORBIT",),
    "ARTIST": ("NOVA / ORBIT",),
    "TITLE": ("LATE NIGHT MOVES",),
    "TRACKNUMBER": ("1",),
    "TRACKTOTAL": ("2",),
    "DISCNUMBER": ("1",),
    "DISCTOTAL": ("1",),
    "DATE": ("2025.03.14",),
    "YEAR": ("2025",),
    "TRCK": ("1/2",),
    "COMMENT": ("지니뮤직",),
    "COPYRIGHT": ("해당곡의 저작권자",),
    "GENRE": ("Dance",),
    "LABEL": ("CJ ENM",),
    "LYRICS": ("",),
    "WWW": ("https://www.genie.co.kr",),
}


def test_stray_tags_finds_genie_residue():
    assert sorted(stray_tags(GENIE_SOURCE_TAGS, {})) == sorted(
        ["COMMENT", "WWW", "TRCK", "ALBUMTITLE", "YEAR", "LYRICS", "COPYRIGHT"]
    )


def test_stray_tags_keeps_real_copyright_and_lyrics():
    tags = {
        **GENIE_SOURCE_TAGS,
        "COPYRIGHT": ("(P) 2025 CJ ENM",),
        "LYRICS": ("Midnight signal",),
    }

    assert sorted(stray_tags(tags, {})) == ["ALBUMTITLE", "COMMENT", "TRCK", "WWW", "YEAR"]


@pytest.mark.parametrize(
    "values", [("",), ("  ",), ("", " \t"), ("해당곡의 저작권자", "")]
)
def test_stray_tags_removes_blank_or_placeholder_copyright(values):
    assert stray_tags({"COPYRIGHT": values}, {}) == ["COPYRIGHT"]


def test_stray_tags_keeps_key_with_any_real_value():
    assert stray_tags({"COPYRIGHT": ("해당곡의 저작권자", "(P) 2025 CJ ENM")}, {}) == []


def test_stray_tags_never_removes_a_key_about_to_be_written():
    source = {"TITLE": ("",), "YEAR": ("2025",), "LYRICS": ("",)}

    # TITLE (blank) and YEAR (always stray) are overwritten, not removed, and
    # keys match case-insensitively. LYRICS's new value is empty ("leave as
    # is"), so its blank tag is still stray.
    assert stray_tags(source, {"title": "Song", "YEAR": "2026", "LYRICS": ""}) == ["LYRICS"]


@pytest.mark.parametrize(
    ("value", "precision", "expected"),
    [
        ("2020-08-28", "day", date(2020, 8, 28)),
        ("2020-08", "month", date(2020, 8, 1)),
        ("2020", "year", date(2020, 1, 1)),
        ("2020-13-01", "day", None),
        ("2020", "day", None),
        ("", "", None),
        ("not a date", "year", None),
    ],
)
def test_parse_release_date(value, precision, expected):
    assert parse_release_date(value, precision) == expected


@pytest.mark.parametrize(
    ("stem", "expected"),
    [
        ("01. Title", "Title"),
        ("01 - Title", "Title"),
        ("01 Title", "Title"),
        ("1.Title", "Title"),
        ("Title", "Title"),
        ("Title - Part 2", "Title - Part 2"),
        ("", ""),
    ],
)
def test_suggest_track_name(stem, expected):
    assert suggest_track_name(stem) == expected


def test_clean_name_replaces_characters_windows_forbids():
    assert clean_name('a<b>c:d"e/f\\g|h?i*j') == "a_b_c_d_e_f_g_h_i_j"


def test_clean_name_keeps_ordinary_punctuation():
    assert clean_name("Don't Stop (Remix) - Live!") == "Don't Stop (Remix) - Live!"


@pytest.mark.parametrize(
    ("number", "name", "expected"),
    [
        (3, "Who: Me?", "03 Who_ Me_.flac"),
        (12, "Twelve", "12 Twelve.flac"),
        (101, "Long", "101 Long.flac"),
    ],
)
def test_track_filename(number, name, expected):
    assert track_filename(number, name, ".flac") == expected
