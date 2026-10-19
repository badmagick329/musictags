import re
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from types import MappingProxyType
from typing import Optional

# Source tags as read from a file: upper-cased Vorbis key -> its values.
SourceTags = Mapping[str, tuple[str, ...]]

# "1" or "1/14"; shops write either form into TRACKNUMBER and DISCNUMBER.
_NUMBER_REGEX = re.compile(r"\s*(\d+)\s*(?:/\s*\d*\s*)?")
_LEADING_DIGITS_REGEX = re.compile(r"(\d+)")
# DATE as "2025.03.14", "2026-05-20", "2025-10" or "2025".
_DATE_YEAR_REGEX = re.compile(r"\s*(\d{4})(?:[.-]\d{1,2}){0,2}\s*")
# The owner's folder convention: "250314 MIDNIGHT SIGNAL" is 2025-03-14.
_FOLDER_DATE_REGEX = re.compile(r"(\d{6})\s+(.*)")
# Joint credits such as "NOVA & ORBIT" or "NOVA / ORBIT".
_ARTIST_SEPARATOR_REGEX = re.compile(r" & | / |, ")


@dataclass(frozen=True)
class SourceFile:
    """One file's source tags and length, read once before anything changes.

    The parsed fields are None when the tag is missing or unparseable. `tags`
    keeps every raw value so later steps (preview, stray-tag removal) can show
    and compare the file's current tags without reading it again.
    """

    path: Path
    length: float
    track_number: Optional[int]
    disc_number: Optional[int]
    title: Optional[str]
    album: Optional[str]
    album_artist: Optional[str]
    artist: Optional[str]
    year: Optional[int]
    # Excluded from the hash because a mapping is unhashable.
    tags: SourceTags = field(default_factory=lambda: MappingProxyType({}), hash=False)

    @classmethod
    def from_tags(cls, path: Path, length: float, tags: SourceTags) -> "SourceFile":
        """Parse a file's source tags; `tags` keys must already be upper-cased."""
        return cls(
            path=path,
            length=length,
            track_number=parse_number(_first(tags, "TRACKNUMBER"))
            or parse_leading_number(path.name),
            disc_number=parse_number(_first(tags, "DISCNUMBER")),
            title=_first(tags, "TITLE"),
            album=_first(tags, "ALBUM"),
            album_artist=_first(tags, "ALBUMARTIST"),
            artist=_first(tags, "ARTIST"),
            year=parse_date_year(_first(tags, "DATE"))
            or parse_number(_first(tags, "YEAR")),
            tags=MappingProxyType(dict(tags)),
        )


@dataclass(frozen=True)
class ReleaseHints:
    """What the album folder says about its release, for the Spotify album
    search and as prompt defaults. `artist` is the first of a joint credit,
    because Spotify lists only that artist as the album artist."""

    album: Optional[str]
    artist: Optional[str]
    year: Optional[int]
    track_count: int


def derive_release_hints(files: Sequence[SourceFile], folder_name: str) -> ReleaseHints:
    folder_year, folder_album = parse_folder_name(folder_name)
    artist = _most_common(f.album_artist for f in files) or _most_common(
        f.artist for f in files
    )
    year = _most_common(f.year for f in files)
    return ReleaseHints(
        album=_most_common(f.album for f in files) or folder_album,
        artist=_ARTIST_SEPARATOR_REGEX.split(artist)[0].strip() if artist else None,
        year=year if year is not None else folder_year,
        track_count=len(files),
    )


def parse_number(value: Optional[str]) -> Optional[int]:
    """Parse "1" or "1/14" to 1; zero and anything else become None."""
    if value is None:
        return None
    match = _NUMBER_REGEX.fullmatch(value)
    number = int(match.group(1)) if match else 0
    return number or None


def parse_leading_number(filename: str) -> Optional[int]:
    """The track number in a filename such as "01. Title.flac"."""
    match = _LEADING_DIGITS_REGEX.match(filename)
    number = int(match.group(1)) if match else 0
    return number or None


def parse_date_year(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    match = _DATE_YEAR_REGEX.fullmatch(value)
    return int(match.group(1)) if match else None


def parse_folder_name(folder_name: str) -> tuple[Optional[int], Optional[str]]:
    """Split "250314 MIDNIGHT SIGNAL" into (2025, "MIDNIGHT SIGNAL").

    A prefix that is not a real YYMMDD date is kept as part of the album name,
    since some album names start with digits.
    """
    match = _FOLDER_DATE_REGEX.fullmatch(folder_name.strip())
    if match:
        digits = match.group(1)
        # The owner's convention reads YY as 20YY.
        year = 2000 + int(digits[:2])
        try:
            date(year, int(digits[2:4]), int(digits[4:]))
        except ValueError:
            pass
        else:
            return year, match.group(2).strip() or None
    return None, folder_name.strip() or None


def _first(tags: SourceTags, key: str) -> Optional[str]:
    """The first non-blank value of a tag, stripped."""
    for value in tags.get(key, ()):
        if value.strip():
            return value.strip()
    return None


def _most_common(values: Iterable):
    """Ties go to the value seen first, i.e. the lowest-numbered file."""
    counts = Counter(v for v in values if v is not None)
    return counts.most_common(1)[0][0] if counts else None
