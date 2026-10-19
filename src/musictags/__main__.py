import argparse
import os

from dotenv import load_dotenv

from musictags.features.tag_tracks import cli
from musictags.features.tag_tracks.use_case import TagTracks
from musictags.infrastructure.flac import FileRenamer, FlacTagWriter, list_flac_files
from musictags.infrastructure.spotify import SpotifyTrackSearch


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="musictags", description="Tag your flac files with Spotify metadata"
    )
    parser.add_argument("album_folder", help="Folder to search for flac files")
    parser.add_argument("-a", "--artist", help="Artist name")
    parser.add_argument("-y", "--year", type=int, help="Album release year")
    parser.add_argument(
        "-sr",
        "--skip-renaming",
        help="Files will also be renamed (format: track_number track_name). Provide this flag to skip renaming files",
        action="store_true",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    load_dotenv()

    folder = cli.get_folder(args.album_folder)
    if folder is None:
        return
    files = list_flac_files(folder)
    if not files:
        print(f"No flac files found at {folder}")
        return

    artist = args.artist if args.artist else cli.get_artist_name()
    year = args.year if args.year is not None else cli.get_year()
    search = SpotifyTrackSearch.from_credentials(
        os.getenv("CLIENT_ID"), os.getenv("CLIENT_SECRET")
    )
    TagTracks(
        search=search,
        tag_writer=FlacTagWriter(),
        renamer=FileRenamer(),
        interaction=cli.ConsoleInteraction(),
    ).run(files, artist, year, rename=not args.skip_renaming)


if __name__ == "__main__":
    main()
