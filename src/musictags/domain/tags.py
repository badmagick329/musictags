from musictags.domain.models import Track


def track_tags(track: Track) -> dict[str, str]:
    """Vorbis comments for a FLAC file. An empty value means "leave as is"."""
    date_value = (
        track.album.release_date.strftime("%Y-%m-%d")
        if track.album.release_date
        else ""
    )
    return {
        "ALBUM": track.album.name,
        "ARTIST": track.main_artist.name,
        "ARTISTS": track.main_artist.name,
        "DATE": date_value,
        "TITLE": track.name,
        "TRACKNUMBER": str(track.track_number),
        "TRACKTOTAL": str(track.album.total_tracks),
    }
