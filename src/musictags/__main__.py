import argparse
import os
import sys
from pathlib import Path
from typing import Optional, Sequence

from dotenv import load_dotenv

from musictags.domain.album_link import parse_album_id
from musictags.features.tag_album import cli as album_cli
from musictags.features.tag_album.use_case import TagAlbum
from musictags.features.tag_tracks import cli
from musictags.features.tag_tracks.use_case import TagTracks
from musictags.infrastructure.flac import (
    FileRenamer,
    FlacTagWriter,
    list_flac_files,
    read_source_files,
)
from musictags.infrastructure.spotify import SpotifyCatalog


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
    parser.add_argument(
        "--per-track",
        help="Search and pick a Spotify track for each file in turn instead of picking one album",
        action="store_true",
    )
    parser.add_argument(
        "--album",
        metavar="LINK",
        help="Spotify album URL, URI or ID to tag from, skipping the album search",
    )
    parser.add_argument(
        "--dry-run",
        help="Print the preview and exit without writing anything",
        action="store_true",
    )
    return parser


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)
    # The per-file flow has no album to name and writes as it goes, so there
    # is no preview to print.
    if args.per_track and (args.album is not None or args.dry_run):
        parser.error("--album and --dry-run cannot be used with --per-track")
    return args


def main(argv: Optional[Sequence[str]] = None) -> None:
    try:
        _main(argv)
    except (EOFError, KeyboardInterrupt):
        # End of input (Ctrl+Z, Ctrl+D) or Ctrl+C at any prompt means quit.
        # The album-first flow writes nothing before `a`; the per-file flow
        # keeps the files it has already tagged.
        print()
        sys.exit(1)


def _main(argv: Optional[Sequence[str]]) -> None:
    args = parse_args(argv)
    album_id = None
    if args.album is not None:
        try:
            album_id = parse_album_id(args.album)
        except ValueError as error:
            print(error)
            sys.exit(1)
    load_dotenv()

    folder = cli.get_folder(args.album_folder)
    if folder is None:
        return

    catalog = SpotifyCatalog.from_credentials(
        os.getenv("CLIENT_ID"), os.getenv("CLIENT_SECRET")
    )
    try:
        if args.per_track:
            _tag_tracks(args, folder, catalog)
        else:
            _tag_album(args, folder, catalog, album_id)
    except RuntimeError as error:
        # Spotify and file-read failures carry a message meant for the user.
        print(error)
        sys.exit(1)


def _per_file_flow(catalog: SpotifyCatalog) -> TagTracks:
    return TagTracks(
        search=catalog,
        tag_writer=FlacTagWriter(),
        renamer=FileRenamer(),
        interaction=cli.ConsoleInteraction(),
    )


def _tag_tracks(args: argparse.Namespace, folder: Path, catalog: SpotifyCatalog) -> None:
    files = list_flac_files(folder)
    if not files:
        print(f"No flac files found at {folder}")
        return
    artist = args.artist if args.artist else cli.get_artist_name()
    year = args.year if args.year is not None else cli.get_year()
    _per_file_flow(catalog).run(files, artist, year, rename=not args.skip_renaming)


def _tag_album(
    args: argparse.Namespace,
    folder: Path,
    catalog: SpotifyCatalog,
    album_id: Optional[str],
) -> None:
    TagAlbum(
        read_source_files=read_source_files,
        catalog=catalog,
        tag_writer=FlacTagWriter(),
        renamer=FileRenamer(),
        track_finder=_per_file_flow(catalog),
        interaction=album_cli.ConsoleInteraction(),
    ).run(
        folder,
        artist=args.artist,
        year=args.year,
        album_id=album_id,
        rename=not args.skip_renaming,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
