from datetime import date

import pytest
from factories import make_track

from musictags.domain.models import Album, Artist, Track, parse_release_date
from musictags.domain.naming import clean_name, suggest_track_name, track_filename
from musictags.domain.tags import track_tags


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
        "ARTIST": "BLACKPINK",
        "ARTISTS": "BLACKPINK",
        "DATE": "2020-10-02",
        "TITLE": "Ice Cream",
        "TRACKNUMBER": "3",
        "TRACKTOTAL": "8",
    }


def test_track_tags_leaves_date_empty_when_release_date_unknown():
    assert track_tags(make_track(release_date=None))["DATE"] == ""


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
