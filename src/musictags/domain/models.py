from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass(frozen=True)
class Artist:
    name: str


@dataclass(frozen=True)
class Album:
    # Spotify's album ID, used to fetch the album's tracks.
    id: str
    name: str
    # Spotify's album artists, kept apart from each track's artists because
    # the two lists can differ in order (album "NOVA, ORBIT" holds tracks by
    # "ORBIT, NOVA").
    artists: tuple[Artist, ...]
    album_type: str
    release_date: Optional[date]
    total_tracks: int


@dataclass(frozen=True)
class Track:
    name: str
    track_number: int
    disc_number: int
    # Seconds, so it compares directly with a file's length from mutagen.
    length: float
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
