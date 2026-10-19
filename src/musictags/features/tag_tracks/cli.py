from pathlib import Path
from typing import Optional, Union

from musictags.domain.models import Album, Track
from musictags.features.tag_tracks.use_case import Choice
from musictags.presentation.colors import colorize


def format_album(album: Album) -> str:
    name = colorize("GREEN", album.name)
    date = colorize("RED", f'"{album.release_date}"')
    return f"{name} ({date}) [{album.album_type}]"


def format_track(track: Track) -> str:
    artist = colorize("YELLOW", track.main_artist.name)
    name = colorize("BLUE", track.name)
    return f"{artist} - {name} - {format_album(track.album)} #{track.track_number}"


def get_folder(folder: str) -> Optional[Path]:
    folder_path = Path(folder)
    if not folder_path.exists():
        print("Folder does not exist")
        return None
    if not folder_path.is_dir():
        print("Path is not a folder")
        return None
    return folder_path


def get_artist_name() -> str:
    name = ""
    while name == "":
        name = input("Enter artist name: ").strip()
    return name


def get_year() -> Optional[int]:
    year = input("Enter release year (or leave blank): ").strip()
    if not year:
        return None
    try:
        return int(year)
    except ValueError:
        print(f"Invalid year: {year}")
        return None


class ConsoleInteraction:
    def ask_track_name(self, filename: str, suggestion: str) -> Union[str, Choice]:
        prompt = (
            f"\nFilename: {filename}\n"
            f"Suggestion: {suggestion}\n"
            f"Enter track name, use suggestion (u), or skip (s): "
        )
        name = input(prompt).strip()
        if name == "u" or name == "":
            return Choice.USE_SUGGESTION
        if name == "s":
            return Choice.SKIP
        return name

    def announce_search(self, name: str) -> None:
        print(f"Searching for track: {name}")

    def ask_after_no_results(self, artist: str, name: str) -> Choice:
        prompt = (
            f"\nCould not find track information for: "
            f"artist:{artist} track:{name}\n"
            "Press enter to search again or skip (s): "
        )
        if input(prompt).strip().lower() == "s":
            return Choice.SKIP
        return Choice.SEARCH_AGAIN

    def choose_track(self, tracks: list[Track]) -> Union[Track, Choice]:
        while True:
            print()
            for i, track in enumerate(tracks):
                print(f"{i + 1}: {format_track(track)}")
            prompt = "\nSelect track by index, search with a different name (n) or skip (s): "
            choice = input(prompt).strip().lower()
            if choice == "n":
                return Choice.SEARCH_AGAIN
            if choice == "s":
                return Choice.SKIP
            try:
                index = int(choice)
            except ValueError:
                print("Invalid input")
                continue
            if index < 1 or index > len(tracks):
                print("Index out of range")
                continue
            return tracks[index - 1]
