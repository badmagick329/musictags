from pathlib import Path

import pytest

from musictags.domain.source import (
    ReleaseHints,
    SourceFile,
    derive_release_hints,
    parse_date_year,
    parse_folder_name,
    parse_leading_number,
    parse_number,
)


def source_file(name: str = "01 Song.flac", length: float = 180.0, **tags: str) -> SourceFile:
    return SourceFile.from_tags(
        Path(name), length, {key.upper(): (value,) for key, value in tags.items()}
    )


def genie_album() -> list[SourceFile]:
    """Mirrors the Genie download of 250314 MIDNIGHT SIGNAL."""
    files = []
    for number in range(1, 15):
        artist = "ORBIT & NOVA & ORBIT RIN" if number >= 12 else "NOVA & ORBIT"
        files.append(
            source_file(
                f"{number:02}. Song {number}.flac",
                ALBUM="MIDNIGHT SIGNAL",
                ALBUMTITLE="MIDNIGHT SIGNAL",
                ALBUMARTIST="NOVA & ORBIT",
                ARTIST=artist,
                TITLE=f"Song {number}",
                TRACKNUMBER=str(number),
                TRACKTOTAL="14",
                DATE="2025.03.14",
                YEAR="2025",
                # Genie's TRCK is wrong and must never win over TRACKNUMBER.
                TRCK=f"{number}/25",
            )
        )
    return files


def qq_album() -> list[SourceFile]:
    """Mirrors the QQ Music download of 260520 LATE NIGHT MOVES."""
    return [
        source_file(
            f"{number:02} Song {number}.flac",
            ALBUM="LATE NIGHT MOVES",
            ALBUMARTIST="NOVA / ORBIT",
            ARTIST="ORBIT",
            ARTISTS="ORBIT",
            TRACKNUMBER=str(number),
            TRACKTOTAL="4",
            DATE="2026-05-20",
        )
        for number in range(1, 5)
    ]


def test_genie_album_gives_album_first_artist_year_and_count():
    assert derive_release_hints(genie_album(), "250314 MIDNIGHT SIGNAL") == ReleaseHints(
        album="MIDNIGHT SIGNAL", artist="NOVA", year=2025, track_count=14
    )


def test_qq_album_splits_slash_joined_album_artist():
    assert derive_release_hints(qq_album(), "260520 LATE NIGHT MOVES") == ReleaseHints(
        album="LATE NIGHT MOVES", artist="NOVA", year=2026, track_count=4
    )


def test_untagged_files_fall_back_to_folder_name():
    files = [source_file(f"{n:02} Song.flac") for n in range(1, 15)]

    assert derive_release_hints(files, "250314 MIDNIGHT SIGNAL") == ReleaseHints(
        album="MIDNIGHT SIGNAL", artist=None, year=2025, track_count=14
    )


def test_tags_win_over_folder_name():
    files = [source_file(ALBUM="Real Name", DATE="2019-01-01")]

    hints = derive_release_hints(files, "250314 Folder Name")

    assert (hints.album, hints.year) == ("Real Name", 2019)


def test_most_common_album_wins_over_odd_file():
    files = [
        source_file(ALBUM="Odd"),
        source_file(ALBUM="Main"),
        source_file(ALBUM="Main"),
    ]

    assert derive_release_hints(files, "Folder").album == "Main"


def test_artist_falls_back_to_artist_tag_and_splits_comma():
    files = [source_file(ARTIST="IU, SUGA"), source_file(ARTIST="IU, SUGA")]

    assert derive_release_hints(files, "Folder").artist == "IU"


def test_album_artist_wins_over_more_common_artist():
    files = [
        source_file(ALBUMARTIST="Lead"),
        source_file(ARTIST="Guest"),
        source_file(ARTIST="Guest"),
    ]

    assert derive_release_hints(files, "Folder").artist == "Lead"


def test_year_falls_back_to_year_tag():
    files = [source_file(DATE="unknown", YEAR="2024")]

    assert derive_release_hints(files, "Folder").year == 2024


def test_empty_folder_counts_no_tracks():
    assert derive_release_hints([], "250314 MIDNIGHT SIGNAL").track_count == 0


@pytest.mark.parametrize(
    ("folder_name", "expected"),
    [
        ("250314 MIDNIGHT SIGNAL", (2025, "MIDNIGHT SIGNAL")),
        ("260520 LATE NIGHT MOVES", (2026, "LATE NIGHT MOVES")),
        ("MIDNIGHT SIGNAL", (None, "MIDNIGHT SIGNAL")),
        # Not a real date, so the digits belong to the album name.
        ("991399 Luftballons", (None, "991399 Luftballons")),
        ("2025 Album", (None, "2025 Album")),
        ("250314", (None, "250314")),
    ],
)
def test_parse_folder_name(folder_name, expected):
    assert parse_folder_name(folder_name) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1", 1),
        ("01", 1),
        ("1/14", 1),
        (" 3 / 14 ", 3),
        ("12/", 12),
        ("0", None),
        ("", None),
        ("A1", None),
        ("1-14", None),
        (None, None),
    ],
)
def test_parse_number(value, expected):
    assert parse_number(value) == expected


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("01. Title.flac", 1),
        ("14 Title.flac", 14),
        ("Title.flac", None),
        ("00 Intro.flac", None),
    ],
)
def test_parse_leading_number(filename, expected):
    assert parse_leading_number(filename) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2025.03.14", 2025),
        ("2026-05-20", 2026),
        ("2025-10", 2025),
        ("2025", 2025),
        ("24.10.2025", None),
        ("20250314", None),
        (None, None),
    ],
)
def test_parse_date_year(value, expected):
    assert parse_date_year(value) == expected


def test_track_number_tolerates_total_and_ignores_trck():
    file = source_file("05. Song.flac", TRACKNUMBER="1/14", TRCK="8/25")

    assert file.track_number == 1


def test_track_number_falls_back_to_filename():
    assert source_file("07. Song.flac").track_number == 7
    assert source_file("07. Song.flac", TRACKNUMBER="x").track_number == 7


def test_disc_number_tolerates_total_but_never_uses_filename():
    assert source_file("01 Song.flac", DISCNUMBER="2/2").disc_number == 2
    assert source_file("01 Song.flac").disc_number is None


def test_blank_tags_are_missing():
    file = source_file(ALBUM="  ", TITLE="")

    assert (file.album, file.title) == (None, None)


def test_keeps_raw_tags_read_only():
    file = SourceFile.from_tags(
        Path("01 Song.flac"), 1.0, {"WWW": ("a", "b"), "TITLE": ("Song",)}
    )

    assert file.tags == {"WWW": ("a", "b"), "TITLE": ("Song",)}
    with pytest.raises(TypeError):
        file.tags["WWW"] = ("c",)  # type: ignore[index]
