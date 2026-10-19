from datetime import date
from typing import Optional

from musictags.domain.models import Album, Artist, Track


def make_album(
    name: str = "Album",
    artist: str = "Artist",
    release_date: Optional[date] = date(2020, 8, 28),
    album_type: str = "album",
    total_tracks: int = 10,
    album_id: str = "0123456789abcdefABCDEF",
) -> Album:
    return Album(
        id=album_id,
        name=name,
        artists=(Artist(artist),),
        album_type=album_type,
        release_date=release_date,
        total_tracks=total_tracks,
    )


def make_track(
    name: str = "Song",
    track_number: int = 1,
    artist: str = "Artist",
    album: str = "Album",
    release_date: Optional[date] = date(2020, 8, 28),
    album_type: str = "album",
    total_tracks: int = 10,
    disc_number: int = 1,
    length: float = 180.0,
) -> Track:
    return Track(
        name=name,
        track_number=track_number,
        disc_number=disc_number,
        length=length,
        artists=(Artist(artist),),
        album=make_album(
            name=album,
            artist=artist,
            release_date=release_date,
            album_type=album_type,
            total_tracks=total_tracks,
        ),
    )
