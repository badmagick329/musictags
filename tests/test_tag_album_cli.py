import re
from dataclasses import replace
from pathlib import Path

import pytest
from factories import make_album, make_track

import musictags.__main__ as entry
from musictags.domain.ranking import RankedAlbum
from musictags.domain.source import SourceFile
from musictags.features.tag_album.cli import ConsoleInteraction, format_preview
from musictags.features.tag_album.preview import (
    Clash,
    Mark,
    Preview,
    PreviewRow,
    StrayTagCount,
    TagChange,
)
from musictags.features.tag_album.use_case import (
    AlbumChoice,
    AlbumLink,
    EditRow,
    PreviewCommand,
    RowEdit,
)

ANSI = re.compile(r"\033\[\d+m")
MIDNIGHT_ID = "2Kbn6hMdh6bD50FmLB0eHb"


def plain(text: str) -> str:
    return ANSI.sub("", text)


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


def source(name: str, length: float = 180.0) -> SourceFile:
    return SourceFile(Path(name), length, None, None, None, None, None, None, None)


def row(number, name, track=None, mark=Mark.SKIP, new_name=None) -> PreviewRow:
    return PreviewRow(number, source(name), track, mark, new_name or name)


def test_preview_shows_album_changes_rows_strays_and_clashes():
    album = make_album(name="MIDNIGHT SIGNAL", artist="NOVA", total_tracks=14)
    track = replace(make_track(name="MIDNIGHT SIGNAL - English Ver."), album=album)
    preview = Preview(
        album=album,
        album_changes=(
            TagChange("ALBUMARTIST", "NOVA & ORBIT", "NOVA"),
            TagChange("ALBUM", None, "MIDNIGHT SIGNAL"),
        ),
        rows=(
            row(
                1,
                "01. MIDNIGHT SIGNAL (English Ver.).flac",
                track,
                Mark.SURE,
                "01 MIDNIGHT SIGNAL - English Ver..flac",
            ),
            row(2, "02 Same.flac", track, Mark.UNSURE),
            row(3, "03 Chosen.flac", track, Mark.CHOSEN),
            row(4, "Bonus.flac"),
        ),
        stray=(StrayTagCount("COMMENT", 14), StrayTagCount("WWW", 3)),
        clashes=(Clash("02 Same.flac", (2, 4)),),
    )

    lines = plain(format_preview(preview)).splitlines()

    assert "  ALBUMARTIST: NOVA & ORBIT → NOVA" in lines
    assert "  ALBUM: (none) → MIDNIGHT SIGNAL" in lines
    assert "  1 ✓    01. MIDNIGHT SIGNAL (English Ver.).flac → 01 MIDNIGHT SIGNAL - English Ver..flac" in lines
    assert "         #1 MIDNIGHT SIGNAL - English Ver." in lines
    # An unchanged name is shown once, without an arrow.
    assert "  2 ?    02 Same.flac" in lines
    assert "  3 ✓    03 Chosen.flac" in lines
    # A skipped row has no track line.
    assert lines[lines.index("  4 skip Bonus.flac") + 1] == ""
    assert "Stray tags to remove: COMMENT ×14, WWW ×3" in lines
    assert "Rows 2 and 4 would both be named 02 Same.flac" in lines


def test_preview_without_changes_or_strays_says_so():
    preview = Preview(make_album(), (), (row(1, "a.flac"),), (), ())

    text = plain(format_preview(preview))

    assert "Album tags: unchanged" in text
    assert "Stray tags to remove: none" in text


def ranked(*albums):
    return [RankedAlbum(a, 0.0) for a in albums]


def test_choose_album_by_number_after_bad_input(answers, capsys):
    first, second = make_album(name="One"), make_album(name="Two")
    answers("0", "zzz", " 2 ")

    assert ConsoleInteraction().choose_album(ranked(first, second), "A", "B") is second

    out = plain(capsys.readouterr().out)
    assert "1: Artist - One (2020-08-28) [album] 10 tracks" in out
    assert "Index out of range" in out
    assert "Not a Spotify album link, URI or ID: 'zzz'" in out


@pytest.mark.parametrize(
    "typed",
    [
        MIDNIGHT_ID,
        f"https://open.spotify.com/intl-ja/album/{MIDNIGHT_ID}?si=abc",
        f"spotify:album:{MIDNIGHT_ID}",
    ],
)
def test_choose_album_accepts_a_pasted_link(answers, typed):
    answers(typed)
    assert ConsoleInteraction().choose_album(ranked(make_album()), "A", "B") == AlbumLink(
        MIDNIGHT_ID
    )


@pytest.mark.parametrize(("typed", "expected"), [("N", AlbumChoice.EDIT_SEARCH), ("q", AlbumChoice.QUIT)])
def test_choose_album_commands(answers, typed, expected):
    answers(typed)
    assert ConsoleInteraction().choose_album(ranked(make_album()), "A", "B") is expected


def test_choose_album_with_nothing_found(answers, capsys):
    prompts = answers("1", "n")

    assert ConsoleInteraction().choose_album([], "NOVA", "MIDNIGHT") is AlbumChoice.EDIT_SEARCH

    out = capsys.readouterr().out
    assert "No albums found for artist:NOVA album:MIDNIGHT" in out
    assert "Index out of range" in out
    assert prompts[0] == "Paste an album link, edit the search (n) or quit (q): "


def test_edit_search_keeps_defaults_on_enter(answers):
    prompts = answers("", "MIDNIGHT")

    assert ConsoleInteraction().edit_search("NOVA", "MIDNIGHT SIGNAL") == (
        "NOVA",
        "MIDNIGHT",
    )
    assert prompts == ["Artist [NOVA]: ", "Album [MIDNIGHT SIGNAL]: "]


def test_ask_album_name_requires_an_answer(answers):
    answers("", "  Album ")
    assert ConsoleInteraction().ask_album_name() == "Album"


@pytest.mark.parametrize(
    ("typed", "expected"),
    [
        ("a", PreviewCommand.APPLY),
        (" P ", PreviewCommand.BACK_TO_ALBUMS),
        ("q", PreviewCommand.QUIT),
        ("e 3", EditRow(3)),
        ("e14", EditRow(14)),
    ],
)
def test_preview_commands(answers, typed, expected):
    answers(typed)
    assert ConsoleInteraction().ask_preview_command(14) == expected


def test_preview_command_rejects_bad_input(answers, capsys):
    answers("e 0", "e 15", "x", "e", "e 2")

    assert ConsoleInteraction().ask_preview_command(14) == EditRow(2)
    assert capsys.readouterr().out.count("Invalid input") == 4


def test_row_edit_choices(answers, capsys):
    tracks = [make_track(name="One", length=61.4), make_track(name="Two")]
    edited = row(5, "05 x.flac")
    ui = ConsoleInteraction()

    answers("0", "3", "2")
    assert ui.ask_row_edit(edited, tracks) is tracks[1]
    out = plain(capsys.readouterr().out)
    assert "Row 5: 05 x.flac" in out
    assert "1: One (1:01)" in out
    assert out.count("Invalid input") == 2

    answers("s")
    assert ui.ask_row_edit(edited, tracks) is RowEdit.SKIP
    answers("/")
    assert ui.ask_row_edit(edited, tracks) is RowEdit.SEARCH
    answers("")
    assert ui.ask_row_edit(edited, tracks) is RowEdit.KEEP


def test_refuse_apply_names_every_clash(capsys):
    ConsoleInteraction().refuse_apply((Clash("01 A.flac", (1, 2, 3)),))
    assert "Rows 1, 2 and 3 would all be named 01 A.flac" in plain(capsys.readouterr().out)


# The entry point: argument handling and dispatch to the two flows.


@pytest.mark.parametrize(
    "argv",
    [
        ["album", "--per-track", "--album", MIDNIGHT_ID],
        ["album", "--per-track", "--dry-run"],
    ],
)
def test_per_track_rejects_album_and_dry_run(argv, capsys):
    with pytest.raises(SystemExit) as exit_info:
        entry.parse_args(argv)
    assert exit_info.value.code == 2
    assert "cannot be used with --per-track" in capsys.readouterr().err


def test_parser_reads_the_album_first_flags():
    args = entry.parse_args(["album", "--album", MIDNIGHT_ID, "--dry-run", "-y", "2025"])
    assert (args.per_track, args.album, args.dry_run, args.year) == (
        False, MIDNIGHT_ID, True, 2025,
    )


@pytest.fixture
def wired(monkeypatch, tmp_path):
    """Run main() with both flows replaced by recorders; returns the calls."""
    calls = []

    class Recorder:
        def __init__(self, name):
            self.name = name

        def __call__(self, *args, **kwargs):
            calls.append((self.name, args, kwargs))

    monkeypatch.setattr(entry, "load_dotenv", lambda: None)
    monkeypatch.setattr(entry.SpotifyCatalog, "from_credentials", lambda *a: "catalog")
    monkeypatch.setattr(entry.TagTracks, "run", lambda self, *a, **k: Recorder("per_track")(*a, **k))
    monkeypatch.setattr(entry.TagAlbum, "run", lambda self, *a, **k: Recorder("album")(*a, **k))
    (tmp_path / "01 a.flac").write_bytes(b"")
    return calls, tmp_path


def test_album_first_is_the_default(wired):
    calls, folder = wired

    entry.main([str(folder), "-a", "NOVA", "-sr", "--album", f"spotify:album:{MIDNIGHT_ID}"])

    assert calls == [(
        "album",
        (folder,),
        {"artist": "NOVA", "year": None, "album_id": MIDNIGHT_ID, "rename": False, "dry_run": False},
    )]


def test_per_track_runs_tag_tracks(wired):
    calls, folder = wired

    entry.main([str(folder), "--per-track", "-a", "NOVA", "-y", "2025"])

    assert calls == [("per_track", ([folder / "01 a.flac"], "NOVA", 2025), {"rename": True})]


def test_an_invalid_album_link_exits_with_its_message(wired, capsys):
    calls, folder = wired

    with pytest.raises(SystemExit) as exit_info:
        entry.main([str(folder), "--album", "not-a-link"])

    assert exit_info.value.code == 1
    assert capsys.readouterr().out == "Not a Spotify album link, URI or ID: 'not-a-link'\n"
    assert calls == []


def test_a_runtime_error_prints_its_message_not_a_traceback(wired, monkeypatch, capsys):
    _, folder = wired

    def fail(self, *args, **kwargs):
        raise RuntimeError("Spotify search failed (401): Invalid access token")

    monkeypatch.setattr(entry.TagAlbum, "run", fail)

    with pytest.raises(SystemExit) as exit_info:
        entry.main([str(folder)])

    assert exit_info.value.code == 1
    assert capsys.readouterr().out == "Spotify search failed (401): Invalid access token\n"
