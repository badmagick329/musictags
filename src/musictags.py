#!/usr/bin/env python3
import argparse
import os

from dotenv import load_dotenv

from cli import Cli
from file_metadata import FlacMetadata
from spotify_client import SpotifyClient
from utils import clean_name

load_dotenv()
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Tag your flac files with Spotify metadata"
    )
    parser.add_argument("album_folder", help="Folder to search for flac files")
    parser.add_argument("-a", "--artist", help="Artist name")
    parser.add_argument(
        "-sr",
        "--skip-renaming",
        help="Files will also be renamed (format: track_number track_name). Provide this flag to skip renaming files",
        action="store_true",
    )
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    cli = Cli()
    folder = cli.get_folder_name(args.album_folder)
    if folder is None:
        return
    files = [f for f in folder.iterdir() if f.is_file() and f.suffix == ".flac"]
    if len(files) == 0:
        print(f"No flac files found at {folder}")
        return

    artist = args.artist if args.artist else cli.get_artist_name()
    client = SpotifyClient(CLIENT_ID, CLIENT_SECRET)
    for file in files:
        track = cli.get_track(client, artist, file)
        if track is None:
            continue
        mdata = FlacMetadata(str(file))
        mdata.set_tags(track.as_tags())
        if args.skip_renaming:
            continue
        new_name = f"{track.track_number:02} {clean_name(track.name)}"
        new_path = file.parent / f"{new_name}{file.suffix}"
        file.rename(new_path)


if __name__ == "__main__":
    main()
