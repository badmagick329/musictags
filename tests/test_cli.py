from datetime import date

import pytest
from factories import make_track

from musictags.__main__ import build_parser
from musictags.features.tag_tracks.cli import (
    ConsoleInteraction,
    format_track,
    get_folder,
    get_year,
)
from musictags.features.tag_tracks.use_case import Choice


@pytest.fixture
def answers(monkeypatch):
    """Feed scripted lines to input() and record the prompts shown."""
    prompts = []

    def feed(*lines):
        queue = list(lines)

        def fake_input(prompt=""):
            prompts.append(prompt)
            return queue.pop(0)

        monkeypatch.setattr("builtins.input", fake_input)
        return prompts

    return feed


def test_format_track_matches_existing_colour_scheme():
    track = make_track(
        name="Ice Cream",
        track_number=3,
        artist="BLACKPINK",
        album="THE ALBUM",
        release_date=date(2020, 10, 2),
    )
    assert format_track(track) == (
        "\033[33mBLACKPINK\033[0m - \033[34mIce Cream\033[0m - "
        "\033[32mTHE ALBUM\033[0m (\033[31m2020-10-02\033[0m) [album] #3"
    )


def test_format_track_leaves_out_unknown_release_date():
    line = format_track(make_track(album="THE ALBUM", release_date=None))
    assert "\033[32mTHE ALBUM\033[0m [album]" in line
    assert "None" not in line


@pytest.mark.parametrize(
    ("typed", "expected"),
    [
        ("", Choice.USE_SUGGESTION),
        ("   ", Choice.USE_SUGGESTION),
        ("u", Choice.USE_SUGGESTION),
        ("s", Choice.SKIP),
        ("  Ice Cream ", "Ice Cream"),
        ("S", "S"),
    ],
)
def test_ask_track_name(answers, typed, expected):
    prompts = answers(typed)
    assert ConsoleInteraction().ask_track_name("01. Ice Cream", "Ice Cream") == expected
    assert prompts == [
        "\nFilename: 01. Ice Cream\nSuggestion: Ice Cream\n"
        "Enter track name, use suggestion (u), or skip (s): "
    ]


@pytest.mark.parametrize(
    ("typed", "expected"),
    [("", Choice.SEARCH_AGAIN), ("anything", Choice.SEARCH_AGAIN), (" S ", Choice.SKIP)],
)
def test_ask_after_no_results(answers, typed, expected):
    prompts = answers(typed)
    assert ConsoleInteraction().ask_after_no_results("Artist", "Song") == expected
    assert prompts == [
        "\nCould not find track information for: artist:Artist track:Song\n"
        "Press enter to search again or skip (s): "
    ]


def test_choose_track_rejects_bad_input_until_valid_index(answers, capsys):
    tracks = [make_track(name="One"), make_track(name="Two")]
    answers("x", "0", "3", " 2 ")

    assert ConsoleInteraction().choose_track(tracks) is tracks[1]

    out = capsys.readouterr().out
    assert out.count("Invalid input") == 1
    assert out.count("Index out of range") == 2
    assert f"1: {format_track(tracks[0])}\n2: {format_track(tracks[1])}" in out


@pytest.mark.parametrize(("typed", "expected"), [("N", Choice.SEARCH_AGAIN), ("s", Choice.SKIP)])
def test_choose_track_commands(answers, typed, expected):
    answers(typed)
    assert ConsoleInteraction().choose_track([make_track()]) is expected


@pytest.mark.parametrize(("typed", "expected"), [("2020", 2020), ("", None), ("soon", None)])
def test_get_year(answers, typed, expected):
    answers(typed)
    assert get_year() == expected


def test_get_folder_messages(tmp_path, capsys):
    file = tmp_path / "a.flac"
    file.write_bytes(b"")

    assert get_folder(str(tmp_path)) == tmp_path
    assert get_folder(str(tmp_path / "missing")) is None
    assert get_folder(str(file)) is None
    assert capsys.readouterr().out == "Folder does not exist\nPath is not a folder\n"


def test_parser_reads_year_as_int():
    args = build_parser().parse_args(["album", "-a", "BLACKPINK", "-y", "2020", "-sr"])
    assert (args.album_folder, args.artist, args.year, args.skip_renaming) == (
        "album", "BLACKPINK", 2020, True,
    )


def test_parser_rejects_non_numeric_year():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["album", "-y", "twenty"])
