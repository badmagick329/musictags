from datetime import date
from typing import Optional

from musictags.domain.models import Album, Artist, Track


def make_track(
    name: str = "Song",
    track_number: int = 1,
    artist: str = "Artist",
    album: str = "Album",
    release_date: Optional[date] = date(2020, 8, 28),
    album_type: str = "album",
    total_tracks: int = 10,
) -> Track:
    return Track(
        name=name,
        track_number=track_number,
        artists=(Artist(artist),),
        album=Album(
            name=album,
            album_type=album_type,
            release_date=release_date,
            total_tracks=total_tracks,
        ),
    )
