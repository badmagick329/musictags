import re
from pathlib import Path
from typing import Optional, Union

from musictags.domain.album_link import parse_album_id
from musictags.domain.models import Album, Track
from musictags.domain.ranking import RankedAlbum
from musictags.features.tag_album.preview import Clash, Mark, Preview, PreviewRow
from musictags.features.tag_album.use_case import (
    AlbumChoice,
    AlbumLink,
    EditRow,
    PreviewCommand,
    RowEdit,
)
from musictags.features.tag_tracks.cli import format_album, get_artist_name
from musictags.presentation.colors import Color, colorize

_EDIT_REGEX = re.compile(r"e\s*(\d+)")

_MARKS: dict[Mark, tuple[Color, str]] = {
    Mark.SURE: ("GREEN", "✓"),
    Mark.CHOSEN: ("GREEN", "✓"),
    Mark.UNSURE: ("YELLOW", "?"),
    Mark.SKIP: ("RED", "skip"),
}
# Wide enough for "skip", so names line up whatever the mark.
_MARK_WIDTH = 4


def format_candidate(album: Album) -> str:
    artists = colorize("YELLOW", ", ".join(a.name for a in album.artists))
    return f"{artists} - {format_album(album)} {album.total_tracks} tracks"


def format_mark(mark: Mark) -> str:
    color, text = _MARKS[mark]
    return colorize(color, text.ljust(_MARK_WIDTH))


def format_row(row: PreviewRow) -> list[str]:
    """A row's lines: the filename (old → new when it changes), then the track."""
    name = row.old_name
    if row.new_name != row.old_name:
        name += f" → {colorize('GREEN', row.new_name)}"
    lines = [f"{row.number:>3} {format_mark(row.mark)} {name}"]
    indent = " " * (4 + _MARK_WIDTH + 1)
    if row.track is not None:
        lines.append(f"{indent}#{row.track.track_number} {colorize('BLUE', row.track.name)}")
    return lines


def format_preview(preview: Preview) -> str:
    lines = ["", f"Album: {format_candidate(preview.album)}", ""]
    if preview.album_changes:
        lines.append("Album tags:")
        for change in preview.album_changes:
            old = change.old if change.old is not None else "(none)"
            lines.append(f"  {change.key}: {old} → {colorize('GREEN', change.new)}")
    else:
        lines.append("Album tags: unchanged")
    lines += ["", "Files:"]
    for row in preview.rows:
        lines += format_row(row)
    lines.append("")
    if preview.stray:
        stray = ", ".join(f"{s.key} ×{s.files}" for s in preview.stray)
        lines.append(f"Stray tags to remove: {stray}")
    else:
        lines.append("Stray tags to remove: none")
    for clash in preview.clashes:
        lines.append(colorize("RED", format_clash(clash)))
    return "\n".join(lines)


def format_clash(clash: Clash) -> str:
    rows = ", ".join(str(n) for n in clash.rows[:-1]) + f" and {clash.rows[-1]}"
    together = "both" if len(clash.rows) == 2 else "all"
    return f"Rows {rows} would {together} be named {clash.name}"


def format_length(seconds: float) -> str:
    minutes, rest = divmod(round(seconds), 60)
    return f"{minutes}:{rest:02}"


def _ask_with_default(label: str, default: Optional[str]) -> str:
    """Enter keeps `default`; without one, an answer is required."""
    shown = f" [{default}]" if default else ""
    while True:
        answer = input(f"{label}{shown}: ").strip()
        if answer:
            return answer
        if default:
            return default


class ConsoleInteraction:
    def show_no_files(self, folder: Path) -> None:
        print(f"No flac files found at {folder}")

    def ask_artist(self) -> str:
        return get_artist_name()

    def ask_album_name(self) -> str:
        return _ask_with_default("Enter album name", None)

    def choose_album(
        self, ranked: list[RankedAlbum], artist: str, album_name: str
    ) -> Union[Album, AlbumLink, AlbumChoice]:
        print()
        if ranked:
            for i, candidate in enumerate(ranked, 1):
                print(f"{i}: {format_candidate(candidate.album)}")
            prompt = "\nSelect album by number, paste an album link, edit the search (n) or quit (q): "
        else:
            print(f"No albums found for artist:{artist} album:{album_name}")
            prompt = "Paste an album link, edit the search (n) or quit (q): "
        while True:
            answer = input(prompt).strip()
            if answer.lower() == "n":
                return AlbumChoice.EDIT_SEARCH
            if answer.lower() == "q":
                return AlbumChoice.QUIT
            if answer.isdigit():
                index = int(answer)
                if 1 <= index <= len(ranked):
                    return ranked[index - 1].album
                print("Index out of range")
                continue
            try:
                return AlbumLink(parse_album_id(answer))
            except ValueError as error:
                print(error)

    def edit_search(self, artist: str, album_name: str) -> tuple[str, str]:
        return _ask_with_default("Artist", artist), _ask_with_default("Album", album_name)

    def show_error(self, message: str) -> None:
        print(colorize("RED", message))

    def show_preview(self, preview: Preview) -> None:
        print(format_preview(preview))

    def ask_preview_command(self, row_count: int) -> Union[PreviewCommand, EditRow]:
        prompt = "\nApply (a), edit a row (e N), back to the album list (p) or quit (q): "
        while True:
            answer = input(prompt).strip().lower()
            if answer == "a":
                return PreviewCommand.APPLY
            if answer == "p":
                return PreviewCommand.BACK_TO_ALBUMS
            if answer == "q":
                return PreviewCommand.QUIT
            match = _EDIT_REGEX.fullmatch(answer)
            if match and 1 <= int(match.group(1)) <= row_count:
                return EditRow(int(match.group(1)))
            print("Invalid input")

    def ask_row_edit(
        self, row: PreviewRow, tracks: list[Track]
    ) -> Union[Track, RowEdit]:
        print(f"\nRow {row.number}: {row.old_name}")
        for i, track in enumerate(tracks, 1):
            print(f"{i}: {colorize('BLUE', track.name)} ({format_length(track.length)})")
        print(f"File length: {format_length(row.file.length)}")
        prompt = "Album track number, skip the file (s), search Spotify (/) or keep the row (Enter): "
        while True:
            answer = input(prompt).strip().lower()
            if answer == "":
                return RowEdit.KEEP
            if answer == "s":
                return RowEdit.SKIP
            if answer == "/":
                return RowEdit.SEARCH
            if answer.isdigit() and 1 <= int(answer) <= len(tracks):
                return tracks[int(answer) - 1]
            print("Invalid input")

    def refuse_apply(self, clashes: tuple[Clash, ...]) -> None:
        print(colorize("RED", "\nCannot apply while files would share a name:"))
        for clash in clashes:
            print(colorize("RED", f"  {format_clash(clash)}"))

    def announce_applied(self, written: int, renamed: int) -> None:
        print(f"Tagged {written} files, renamed {renamed}.")
