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


def get_track(
    client: SpotifyClient, artist: str, file: Path
) -> Optional[Track]:
    while True:
        selected = _get_track_name(file)
        if selected.result_type == SelectionResultType.SKIP:
            return None
        name = selected.track_name
        print(f"Searching for track: {name}")
        tracks = client.search_tracks(artist, name)
        if len(tracks) == 0:
            result_type = _process_no_tracks(artist, name)
            if result_type == SelectionResultType.SKIP:
                return None
            continue
        selected = _select_track(tracks)
        if selected.result_type == SelectionResultType.SKIP:
            return None
        elif selected.result_type == SelectionResultType.SEARCH:
            continue
        return selected.track


def get_artist_name() -> str:
    name = ""
    while name == "":
        name = input(
            "Enter artist name (Case insensitive exact match): "
        ).strip()
    return name


def get_album_name() -> str:
    name = ""
    while name == "":
        name = input("Album name: ").strip()
    return name


def get_folder_name() -> Optional[Path]:
    folder_path = Path(input("Folder path: ").strip())
    if not folder_path.exists():
        print("Folder does not exist")
        return
    if not folder_path.is_dir():
        print("Path is not a folder")
        return
    return folder_path


def _get_track_name(file: Path) -> TrackNameResult:
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
    if name == "s":
        return TrackNameResult(SelectionResultType.SKIP, None)
    return TrackNameResult(SelectionResultType.SELECTED, name)


def _select_track(tracks) -> TrackSelectionResult:
    while True:
        print()
        for i, track in enumerate(tracks):
            print(f"{i+1}: {track}")
        input_str = (
            "\nSelect track by index, "
            "search with a different name (n) or skip (s): "
        )
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


def _process_no_tracks(artist: str, name) -> SelectionResultType:
    input_str = (
        f"\nCould not find track information for: "
        f"artist:{artist} track:{name}\n"
        "Press enter to search again or skip (s): "
    )
    if input(input_str).strip().lower() == "s":
        return SelectionResultType.SKIP
    return SelectionResultType.SEARCH
