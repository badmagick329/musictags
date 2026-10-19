from datetime import date
from enum import Enum, auto
from pathlib import Path
from typing import Optional, Protocol, Union

from musictags.domain.models import Track
from musictags.domain.naming import suggest_track_name, track_filename
from musictags.domain.tags import track_tags


class Choice(Enum):
    SKIP = auto()
    USE_SUGGESTION = auto()
    SEARCH_AGAIN = auto()


class TrackSearch(Protocol):
    def search_tracks(
        self, artist: str, name: str, year: Optional[int]
    ) -> list[Track]: ...


class TagWriter(Protocol):
    def write_tags(self, file: Path, tags: dict[str, str]) -> None: ...


class Renamer(Protocol):
    def rename(self, file: Path, new_name: str) -> None: ...


class Interaction(Protocol):
    def ask_track_name(self, filename: str, suggestion: str) -> Union[str, Choice]:
        """A track name to search for, Choice.USE_SUGGESTION or Choice.SKIP."""
        ...

    def announce_search(self, name: str) -> None: ...

    def ask_after_no_results(self, artist: str, name: str) -> Choice:
        """Choice.SEARCH_AGAIN or Choice.SKIP."""
        ...

    def choose_track(self, tracks: list[Track]) -> Union[Track, Choice]:
        """The chosen track, Choice.SEARCH_AGAIN or Choice.SKIP."""
        ...


class TagTracks:
    def __init__(
        self,
        search: TrackSearch,
        tag_writer: TagWriter,
        renamer: Renamer,
        interaction: Interaction,
    ):
        self._search = search
        self._tag_writer = tag_writer
        self._renamer = renamer
        self._ui = interaction
        # Files in one folder usually come from one release, so after the first
        # pick, results from the same release date are listed first.
        self._previous_release_date: Optional[date] = None

    def run(
        self, files: list[Path], artist: str, year: Optional[int], rename: bool
    ) -> None:
        for file in files:
            track = self._find_track(file, artist, year)
            if track is None:
                continue
            self._tag_writer.write_tags(file, track_tags(track))
            if rename:
                self._renamer.rename(
                    file, track_filename(track.track_number, track.name, file.suffix)
                )

    def _find_track(
        self, file: Path, artist: str, year: Optional[int]
    ) -> Optional[Track]:
        suggestion = suggest_track_name(file.stem)
        while True:
            name = self._ui.ask_track_name(file.stem, suggestion)
            if name is Choice.SKIP:
                return None
            if name is Choice.USE_SUGGESTION:
                name = suggestion
            assert isinstance(name, str)

            self._ui.announce_search(name)
            tracks = self._search.search_tracks(artist, name, year)
            if not tracks:
                if self._ui.ask_after_no_results(artist, name) is Choice.SKIP:
                    return None
                continue

            choice = self._ui.choose_track(self._same_release_first(tracks))
            if choice is Choice.SKIP:
                return None
            if choice is Choice.SEARCH_AGAIN:
                continue
            assert isinstance(choice, Track)
            self._previous_release_date = choice.album.release_date
            return choice

    def _same_release_first(self, tracks: list[Track]) -> list[Track]:
        previous = self._previous_release_date
        if previous is None:
            return tracks
        # sorted() is stable, so Spotify's relevance order holds within each group.
        return sorted(tracks, key=lambda t: t.album.release_date != previous)
