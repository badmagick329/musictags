from collections.abc import Mapping

from musictags.domain.models import Track
from musictags.domain.source import SourceTags

# Shop residue that is stale or meaningless once musictags has tagged a file,
# whatever its value.
ALWAYS_STRAY_KEYS = frozenset(
    {
        # Store branding such as Genie's "지니뮤직", not a note about the music.
        "COMMENT",
        # Store page URLs.
        "WWW",
        # An ID3-style duplicate of TRACKNUMBER/TRACKTOTAL ("1/2") that goes
        # stale when those are rewritten.
        "TRCK",
        # Duplicates of ALBUM and DATE that would disagree with Spotify's
        # values once those are written.
        "ALBUMTITLE",
        "YEAR",
    }
)

# Values a shop writes in place of real content. A key whose every value is
# one of these carries no information, so it is removed; real values in the
# same key are kept.
PLACEHOLDER_VALUES: Mapping[str, frozenset[str]] = {
    # Genie's "this song's copyright holder" instead of the actual holder.
    "COPYRIGHT": frozenset({"해당곡의 저작권자"}),
}


def track_tags(track: Track) -> dict[str, str]:
    """Vorbis comments for a FLAC file. An empty value means "leave as is"."""
    date_value = (
        track.album.release_date.strftime("%Y-%m-%d")
        if track.album.release_date
        else ""
    )
    # The mapper allows an album with no artists; then the shop's value stays.
    album_artist = track.album.artists[0].name if track.album.artists else ""
    return {
        "ALBUM": track.album.name,
        "ALBUMARTIST": album_artist,
        "ARTIST": track.main_artist.name,
        "ARTISTS": track.main_artist.name,
        "DATE": date_value,
        "TITLE": track.name,
        "TRACKNUMBER": str(track.track_number),
        "TRACKTOTAL": str(track.album.total_tracks),
    }


def stray_tags(source_tags: SourceTags, new_tags: Mapping[str, str]) -> list[str]:
    """Keys of `source_tags` to remove when `new_tags` are written, in source order.

    `source_tags` keys must be upper-cased, as `SourceTags` are. A key that
    `new_tags` sets to a non-empty value is never stray: writing overwrites it,
    so removing it too would be redundant, and leaving it out keeps this list
    to what the file actually loses (what a preview should show). A key whose
    new value is empty is left as is by the writer, so it is still judged here;
    a blank one is removed rather than kept as an empty tag.
    """
    overwritten = {key.upper() for key, value in new_tags.items() if value}
    return [
        key
        for key, values in source_tags.items()
        if key not in overwritten and _is_stray(key, values)
    ]


def _is_stray(key: str, values: tuple[str, ...]) -> bool:
    if key in ALWAYS_STRAY_KEYS:
        return True
    # A blank value is as empty as a placeholder, so a mix of the two is stray.
    placeholders = PLACEHOLDER_VALUES.get(key, frozenset())
    return all(not value or value in placeholders for value in map(str.strip, values))
