import re
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Optional

from spotify_client import SpotifyClient
from track import Track

NAME_REGEX = re.compile(r"\d*\.?(?: -)?\s?(.+)")


class SelectionResultType(Enum):
    SKIP = auto()
    SEARCH = auto()
    SELECTED = auto()


@dataclass
class TrackSelectionResult:
    result_type: SelectionResultType
    track: Optional[Track]


@dataclass
class TrackNameResult:
    result_type: SelectionResultType
    track_name: Optional[str]


class Cli:
    date_from_previous_choice: Optional[str] = None

    def get_track(
        self, client: SpotifyClient, artist: str, file: Path
    ) -> Optional[Track]:
        while True:
            selected = Cli._get_track_name(file)
            if selected.result_type == SelectionResultType.SKIP:
                return None
            name = selected.track_name
            assert name, "Track name should not be None"

            print(f"Searching for track: {name}")
            tracks = client.search_tracks(artist, name)
            if len(tracks) == 0:
                result_type = Cli._process_no_tracks(artist, name)
                if result_type == SelectionResultType.SKIP:
                    return None
                continue
            if self.date_from_previous_choice:
                tracks = Cli._resort_tracks(tracks, self.date_from_previous_choice)

            selected = Cli._select_track(tracks)
            if selected.result_type == SelectionResultType.SKIP:
                return None
            elif selected.result_type == SelectionResultType.SEARCH:
                continue
            if selected.track:
                self.date_from_previous_choice = (
                    selected.track.album.release_date.isoformat()
                    if selected.track.album.release_date
                    else None
                )

            return selected.track

    @classmethod
    def _get_track_name(cls, file: Path) -> TrackNameResult:
        suggestion = file.stem
        match = re.match(NAME_REGEX, file.stem)
        if match:
            suggestion = match.group(1)
        input_str = (
            f"\nFilename: {file.stem}\n"
            f"Suggestion: {suggestion}\n"
            f"Enter track name, use suggestion (u), or skip (s): "
        )
        name = input(input_str).strip()
        if name == "u":
            name = suggestion
        elif name == "s":
            return TrackNameResult(SelectionResultType.SKIP, None)
        return TrackNameResult(SelectionResultType.SELECTED, name)

    @staticmethod
    def get_artist_name() -> str:
        name = ""
        while name == "":
            name = input("Enter artist name: ").strip()
        return name

    @staticmethod
    def get_folder_name(folder: str) -> Optional[Path]:
        folder_path = Path(folder)
        if not folder_path.exists():
            print("Folder does not exist")
            return
        if not folder_path.is_dir():
            print("Path is not a folder")
            return
        return folder_path

    @classmethod
    def _resort_tracks(cls, tracks: list[Track], date: str) -> list[Track]:
        return sorted(
            tracks,
            key=lambda t: (
                -1
                if t.album.release_date and t.album.release_date.isoformat() == date
                else 1
            ),
        )

    @classmethod
    def _select_track(cls, tracks: list[Track]) -> TrackSelectionResult:
        while True:
            print()
            for i, track in enumerate(tracks):
                print(f"{i + 1}: {track.colored_string()}")
            input_str = "\nSelect track by index, search with a different name (n) or skip (s): "
            choice = input(input_str).strip().lower()
            if choice == "n":
                return TrackSelectionResult(SelectionResultType.SEARCH, None)
            elif choice == "s":
                return TrackSelectionResult(SelectionResultType.SKIP, None)
            try:
                choice = int(choice)
            except ValueError:
                print("Invalid input")
                continue
            if choice < 1 or choice > len(tracks):
                print("Index out of range")
                continue
            return TrackSelectionResult(
                SelectionResultType.SELECTED, tracks[choice - 1]
            )

    @classmethod
    def _process_no_tracks(cls, artist: str, name) -> SelectionResultType:
        input_str = (
            f"\nCould not find track information for: "
            f"artist:{artist} track:{name}\n"
            "Press enter to search again or skip (s): "
        )
        if input(input_str).strip().lower() == "s":
            return SelectionResultType.SKIP
        return SelectionResultType.SEARCH
