"""Album match: pair each source file with at most one track of the chosen album.

Every (file, track) pair gets a score from title similarity, length and track
number; pairs are then assigned one-to-one, best first. Greedy assignment is
not optimal in general, but albums have at most a few dozen tracks and a
correct pair scores well above its rivals, so the best pair is almost always
the right one to take first.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher
from enum import Enum
from typing import Optional

from musictags.domain.models import Track
from musictags.domain.source import SourceFile

# Title similarity dominates the score: it is the only signal that separates
# language versions, which share a length to within 0.014 s.
TITLE_WEIGHT = 1.0
# Length confirms a title and is the main signal for files without one.
LENGTH_WEIGHT = 0.5
# A length difference at which the length stops counting at all. Source files
# match Spotify to ~0.1 s, so 10 s is well past any honest difference while
# still giving partial credit to a slightly different master.
LENGTH_SCALE_SECONDS = 10.0
# A track number only supports a match, never decides it: shops and deluxe
# editions renumber tracks. It is half the smallest gap in title similarity
# between two language versions in MIDNIGHT SIGNAL (K.L.M English vs Chinese,
# 1.0 vs 0.902), so a swapped number can never outvote the title.
NUMBER_WEIGHT = 0.05
# Below this a pair is not assigned and the file stays unmatched. A file
# without a title reaches it with its length within 2 s; unrelated titles
# score about 0.1 to 0.25, so they also need a close length to pass.
MIN_MATCH_SCORE = 0.4
# A pair is sure only above this title similarity. The closest wrong language
# version in the fixtures scores 0.902, so 0.95 keeps a wrong version unsure
# even when its own version is missing from the album.
SURE_TITLE_SIMILARITY = 0.95
# And only when the lengths agree this closely; a different edit or master of
# the same title is usually several seconds off.
SURE_LENGTH_TOLERANCE_SECONDS = 2.0

_APOSTROPHE_REGEX = re.compile(r"['’`]")
_NON_WORD_REGEX = re.compile(r"[\W_]+")
_FEATURING_REGEX = re.compile(r"\b(?:ft|featuring)\b")


class MatchConfidence(Enum):
    SURE = "sure"
    UNSURE = "unsure"
    UNMATCHED = "unmatched"


@dataclass(frozen=True)
class FileMatch:
    """One file's result in the album match; `track` is None when unmatched."""

    file: SourceFile
    track: Optional[Track]
    confidence: MatchConfidence
    score: float


def normalise_title(title: str) -> str:
    """Reduce a title to lower-case words so shop and Spotify styles compare.

    Genie writes "Title (English Ver.)" and "(Feat. X)" where Spotify writes
    "Title - English Ver." and "[feat. X]". Turning every bracket, dash and
    punctuation mark into a space makes all three qualifier styles the same
    text; apostrophes are dropped instead so "Don't" stays one word.
    """
    text = _APOSTROPHE_REGEX.sub("", title.casefold())
    text = _NON_WORD_REGEX.sub(" ", text)
    return _FEATURING_REGEX.sub("feat", text).strip()


def title_similarity(a: str, b: str) -> float:
    """0.0 to 1.0, comparing normalised titles character by character."""
    return SequenceMatcher(None, normalise_title(a), normalise_title(b)).ratio()


def match_album(files: Sequence[SourceFile], tracks: Sequence[Track]) -> list[FileMatch]:
    """Pair each file with at most one track; one result per file, in file order."""
    pairs = []
    for file_index, file in enumerate(files):
        for track_index, track in enumerate(tracks):
            score = _pair_score(file, track)
            if score >= MIN_MATCH_SCORE:
                pairs.append((score, file_index, track_index))
    # Sorting on the indices too keeps ties in file and track order.
    pairs.sort(key=lambda pair: (-pair[0], pair[1], pair[2]))

    assigned: dict[int, tuple[int, float]] = {}
    used_tracks: set[int] = set()
    for score, file_index, track_index in pairs:
        if file_index in assigned or track_index in used_tracks:
            continue
        assigned[file_index] = (track_index, score)
        used_tracks.add(track_index)

    results = []
    for file_index, file in enumerate(files):
        if file_index not in assigned:
            results.append(FileMatch(file, None, MatchConfidence.UNMATCHED, 0.0))
            continue
        track_index, score = assigned[file_index]
        track = tracks[track_index]
        confidence = MatchConfidence.SURE if _is_sure(file, track) else MatchConfidence.UNSURE
        results.append(FileMatch(file, track, confidence, score))
    return results


def _pair_score(file: SourceFile, track: Track) -> float:
    title = title_similarity(file.title, track.name) if file.title is not None else 0.0
    return (
        TITLE_WEIGHT * title
        + LENGTH_WEIGHT * _length_score(file, track)
        + NUMBER_WEIGHT * _numbers_agree(file, track)
    )


def _length_score(file: SourceFile, track: Track) -> float:
    return max(0.0, 1.0 - abs(file.length - track.length) / LENGTH_SCALE_SECONDS)


def _numbers_agree(file: SourceFile, track: Track) -> bool:
    # Most single-disc downloads carry no DISCNUMBER, so a missing one agrees.
    return file.track_number == track.track_number and (
        file.disc_number is None or file.disc_number == track.disc_number
    )


def _is_sure(file: SourceFile, track: Track) -> bool:
    # A file without a title can never be sure: length and number alone cannot
    # tell language versions apart.
    return (
        file.title is not None
        and title_similarity(file.title, track.name) >= SURE_TITLE_SIMILARITY
        and abs(file.length - track.length) <= SURE_LENGTH_TOLERANCE_SECONDS
    )
