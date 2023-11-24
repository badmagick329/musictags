from pathlib import Path
from typing import Optional

from spotify_client import SpotifyClient
from track import Track


def get_track(
    client: SpotifyClient, artist: str, file: Path
) -> Optional[Track]:
    MAX_RESULTS = 15
    while True:
        input_str = f"Enter track name (filename: {file.stem}): "
        name = input(input_str).strip()
        print(f"Searching for track: {name}\n")
        tracks = client.search_tracks(artist, name)
        if len(tracks) == 0:
            print(
                f"Could not find track information for: "
                f"artist:{artist} track:{name}"
            )
            input_str = "Skip? (s): "
            if input(input_str).strip().lower() == "y":
                return None
            else:
                continue
        for i, track in enumerate(tracks):
            print(f"{i+1}: {track}")
        input_str = "Select track by index, search with a different name (n) or skip (s): "
        choice = input(input_str).strip().lower()
        if choice == "n":
            print()
            continue
        elif choice == "s":
            return None
        try:
            choice = int(choice)
        except ValueError:
            print("Invalid input")
            continue
        if choice < 1 or choice > MAX_RESULTS:
            print("Index out of range")
            continue
        return tracks[choice - 1]


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


def _get_track_name(file: Path) -> str:
    name = ""
    while name == "":
        name = input("Track name: ").strip()
    print(f"Using track name: {name}")
    return name
