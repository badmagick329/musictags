import os

from dotenv import load_dotenv

from cli import get_artist_name, get_folder_name, get_track
from file_metadata import FlacMetadata
from spotify_client import SpotifyClient
from utils import clean_name

load_dotenv()
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")


def main():
    folder = get_folder_name()
    if folder is None:
        return
    files = [f for f in folder.iterdir() if f.is_file() and f.suffix == ".flac"]
    if len(files) == 0:
        print(f"No flac files found at {folder}")
        return
    artist = get_artist_name()
    client = SpotifyClient(CLIENT_ID, CLIENT_SECRET)
    for file in files:
        track = get_track(client, artist, file)
        if track is None:
            continue
        mdata = FlacMetadata(file)
        mdata.set_tags(track.as_tags())
        new_name = f"{track.track_number:02} {clean_name(track.name)}"
        new_path = file.parent / f"{new_name}{file.suffix}"
        file.rename(new_path)


if __name__ == "__main__":
    main()
