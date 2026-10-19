"""Rank Spotify album candidates against the release hints, best first."""

from collections.abc import Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Optional

from musictags.domain.album_match import title_similarity
from musictags.domain.models import Album
from musictags.domain.source import ReleaseHints

# Artist and album name identify the release, so they weigh most.
ARTIST_WEIGHT = 1.0
ALBUM_NAME_WEIGHT = 1.0
# The track count separates the album from singles, covers and compilations
# that share its name, but deluxe editions and missing files make it differ
# on the right album too, so it only supports the name.
TRACK_COUNT_WEIGHT = 0.5
# The year is the weakest hint: it may come from the folder name, and Spotify
# dates re-releases by their own release.
YEAR_WEIGHT = 0.25


@dataclass(frozen=True)
class RankedAlbum:
    album: Album
    score: float


def rank_albums(hints: ReleaseHints, candidates: Sequence[Album]) -> list[RankedAlbum]:
    """Score every candidate; best first, ties kept in Spotify's order.

    A hint that is missing scores nothing for every candidate, so it neither
    helps nor hurts any of them.
    """
    ranked = [RankedAlbum(album, _album_score(hints, album)) for album in candidates]
    # sorted() is stable, so equal scores keep Spotify's relevance order.
    return sorted(ranked, key=lambda r: -r.score)


def _album_score(hints: ReleaseHints, album: Album) -> float:
    score = 0.0
    if hints.artist is not None:
        score += ARTIST_WEIGHT * _artist_similarity(hints.artist, album)
    if hints.album is not None:
        score += ALBUM_NAME_WEIGHT * title_similarity(hints.album, album.name)
    if hints.track_count == album.total_tracks:
        score += TRACK_COUNT_WEIGHT
    if hints.year is not None and _year(album) == hints.year:
        score += YEAR_WEIGHT
    return score


def _artist_similarity(artist: str, album: Album) -> float:
    # The hint is the first of a joint credit, which may be any of Spotify's
    # album artists, so the best of them counts.
    wanted = artist.strip().casefold()
    return max(
        (SequenceMatcher(None, wanted, a.name.strip().casefold()).ratio() for a in album.artists),
        default=0.0,
    )


def _year(album: Album) -> Optional[int]:
    return album.release_date.year if album.release_date is not None else None
