from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass(frozen=True)
class Artist:
    name: str


@dataclass(frozen=True)
class Album:
    name: str
    album_type: str
    release_date: Optional[date]
    total_tracks: int


@dataclass(frozen=True)
class Track:
    name: str
    track_number: int
    # Never empty: the first artist names the file's ARTIST tag.
    artists: tuple[Artist, ...]
    album: Album

    @property
    def main_artist(self) -> Artist:
        return self.artists[0]


def parse_release_date(value: str, precision: str) -> Optional[date]:
    """Parse a release date that may only be known to the month or year.

    Coarse dates are padded to the first day of their period so every album
    gets a comparable date; anything unparseable becomes None (no DATE tag).
    """
    if precision == "month":
        value += "-01"
    elif precision == "year":
        value += "-01-01"
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None
