"""The preview: what applying the chosen album would change, built without I/O.

Everything here is pure so the preview's content (and the rules that block
applying it) can be tested apart from the console.
"""

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Optional

from musictags.domain.album_match import FileMatch, MatchConfidence
from musictags.domain.models import Album, Track
from musictags.domain.naming import track_filename
from musictags.domain.source import SourceFile
from musictags.domain.tags import album_tags, stray_tags, track_tags

# The album-level tags shown once above the rows; every written file gets the
# same value for each.
ALBUM_LEVEL_KEYS = ("ALBUM", "ALBUMARTIST", "DATE", "TRACKTOTAL")


class Mark(Enum):
    SURE = auto()
    UNSURE = auto()
    # Assigned by the user while editing the preview; shown like SURE because
    # the user has decided.
    CHOSEN = auto()
    # Unmatched by the album match or skipped by the user: left untouched.
    SKIP = auto()


@dataclass(frozen=True)
class Assignment:
    """One file and the track it will be tagged from; `track` is None exactly
    when the mark is SKIP."""

    file: SourceFile
    track: Optional[Track]
    mark: Mark


@dataclass(frozen=True)
class PreviewRow:
    # 1-based, as shown to the user and typed in `e N`.
    number: int
    file: SourceFile
    track: Optional[Track]
    mark: Mark
    # Equal to the current name when the file is skipped or renaming is off.
    new_name: str

    @property
    def old_name(self) -> str:
        return self.file.path.name

    @property
    def written(self) -> bool:
        return self.track is not None


@dataclass(frozen=True)
class TagChange:
    key: str
    # None when no file has the tag.
    old: Optional[str]
    new: str


@dataclass(frozen=True)
class StrayTagCount:
    key: str
    # How many of the files to be written lose this tag.
    files: int


@dataclass(frozen=True)
class Clash:
    """Rows whose files would end up with the same name."""

    name: str
    rows: tuple[int, ...]


@dataclass(frozen=True)
class Preview:
    album: Album
    album_changes: tuple[TagChange, ...]
    rows: tuple[PreviewRow, ...]
    stray: tuple[StrayTagCount, ...]
    clashes: tuple[Clash, ...]


def assignments_from_match(matches: Iterable[FileMatch]) -> list[Assignment]:
    marks = {MatchConfidence.SURE: Mark.SURE, MatchConfidence.UNSURE: Mark.UNSURE}
    return [
        Assignment(m.file, m.track, marks[m.confidence])
        if m.track is not None
        else Assignment(m.file, None, Mark.SKIP)
        for m in matches
    ]


def build_preview(album: Album, assignments: Sequence[Assignment], rename: bool) -> Preview:
    rows = tuple(
        PreviewRow(
            number=index,
            file=a.file,
            track=a.track,
            mark=a.mark,
            new_name=_new_name(a, rename),
        )
        for index, a in enumerate(assignments, 1)
    )
    files = [a.file for a in assignments]
    return Preview(
        album=album,
        album_changes=tuple(album_tag_changes(files, album)),
        rows=rows,
        stray=tuple(stray_summary(rows)),
        clashes=tuple(find_clashes(rows)),
    )


def album_tag_changes(files: Sequence[SourceFile], album: Album) -> list[TagChange]:
    """Album-level tags that change, old being the most common source value.

    The most common value stands for the album because one odd file should
    not hide (or invent) a change that applies to all of them.
    """
    new_tags = album_tags(album)
    changes = []
    for key in ALBUM_LEVEL_KEYS:
        new = new_tags[key]
        # An empty value is left as is by the writer, so nothing changes.
        if not new:
            continue
        old = _most_common(_first_value(f, key) for f in files)
        if old != new:
            changes.append(TagChange(key, old, new))
    return changes


def stray_summary(rows: Iterable[PreviewRow]) -> list[StrayTagCount]:
    """Stray tags over the files to be written, in first-seen order."""
    counts: Counter[str] = Counter()
    for row in rows:
        if row.track is not None:
            counts.update(stray_tags(row.file.tags, track_tags(row.track)))
    # Counter keeps insertion order, i.e. first file, then source tag order.
    return [StrayTagCount(key, n) for key, n in counts.items()]


def find_clashes(rows: Iterable[PreviewRow]) -> list[Clash]:
    """Groups of rows whose files would share a name once applied.

    Every file counts, including skipped ones that keep their current name, so
    a new name equal to a file that stays put is a clash too. Names compare
    case-insensitively because Windows does.
    """
    by_name: dict[str, list[PreviewRow]] = {}
    for row in rows:
        by_name.setdefault(row.new_name.casefold(), []).append(row)
    return [
        Clash(group[0].new_name, tuple(r.number for r in group))
        for group in by_name.values()
        if len(group) > 1
    ]


def rename_steps(rows: Sequence[PreviewRow]) -> list[tuple[Path, str]]:
    """(current path, new name) renames, ordered so none overwrites a file.

    Requires a preview without clashes. A file may be renamed to the current
    name of another file that is itself renamed (tracks numbered differently
    from their files), so such a target waits until that file has moved; a
    cycle of them goes through a temporary name.
    """
    pending = [
        (row.file.path, row.new_name)
        for row in rows
        if row.written and row.new_name != row.old_name
    ]
    steps: list[tuple[Path, str]] = []
    temp_count = 0
    while pending:
        occupied = {path.name.casefold() for path, _ in pending}
        for index, (path, new_name) in enumerate(pending):
            # A case-only rename of a file targets its own current name.
            if new_name.casefold() not in occupied or new_name.casefold() == path.name.casefold():
                steps.append((path, new_name))
                del pending[index]
                break
        else:
            path, new_name = pending[0]
            temp_count += 1
            temp = path.with_name(f".musictags-rename-{temp_count}{path.suffix}")
            steps.append((path, temp.name))
            pending[0] = (temp, new_name)
    return steps


def _new_name(assignment: Assignment, rename: bool) -> str:
    track, file = assignment.track, assignment.file
    if track is None or not rename:
        return file.path.name
    return track_filename(track.track_number, track.name, file.path.suffix)


def _first_value(file: SourceFile, key: str) -> Optional[str]:
    for value in file.tags.get(key, ()):
        if value.strip():
            return value.strip()
    return None


def _most_common(values: Iterable[Optional[str]]) -> Optional[str]:
    """Ties go to the value seen first; None when no file has a value."""
    counts = Counter(v for v in values if v is not None)
    return counts.most_common(1)[0][0] if counts else None
