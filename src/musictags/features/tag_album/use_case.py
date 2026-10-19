from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Optional, Protocol, Union

from musictags.domain.album_match import match_album
from musictags.domain.models import Album, Track
from musictags.domain.ranking import RankedAlbum, rank_albums
from musictags.domain.source import ReleaseHints, SourceFile, derive_release_hints
from musictags.domain.tags import track_tags
from musictags.features.tag_album.preview import (
    Assignment,
    Clash,
    Mark,
    Preview,
    PreviewRow,
    assignments_from_match,
    build_preview,
    rename_steps,
)
from musictags.features.tag_tracks.use_case import Renamer, TagWriter


class AlbumChoice(Enum):
    EDIT_SEARCH = auto()
    QUIT = auto()


@dataclass(frozen=True)
class AlbumLink:
    """An album the user pasted instead of picking from the list."""

    album_id: str


class PreviewCommand(Enum):
    APPLY = auto()
    BACK_TO_ALBUMS = auto()
    QUIT = auto()


@dataclass(frozen=True)
class EditRow:
    number: int


class RowEdit(Enum):
    SKIP = auto()
    SEARCH = auto()
    # Enter at the edit prompt: leave the row as it is.
    KEEP = auto()


class SourceReader(Protocol):
    def __call__(self, folder: Path) -> list[SourceFile]:
        """Every file's source tags and length, without writing to any."""
        ...


class AlbumCatalog(Protocol):
    def search_albums(
        self, artist: str, album: str, year: Optional[int] = None
    ) -> list[Album]: ...

    def album(self, album_id: str) -> Album: ...

    def album_tracks(self, album: Album) -> list[Track]: ...


class TrackFinder(Protocol):
    def find_track(
        self, file: Path, artist: str, year: Optional[int]
    ) -> Optional[Track]:
        """The per-file search for one file; None if the user skipped it."""
        ...


class Interaction(Protocol):
    def show_no_files(self, folder: Path) -> None: ...

    def ask_artist(self) -> str: ...

    def ask_album_name(self) -> str: ...

    def choose_album(
        self, ranked: list[RankedAlbum], artist: str, album_name: str
    ) -> Union[Album, AlbumLink, AlbumChoice]:
        """A listed album, a pasted album link, or a command. `ranked` may be
        empty, when nothing was found."""
        ...

    def edit_search(self, artist: str, album_name: str) -> tuple[str, str]:
        """New artist and album name, the current ones as defaults."""
        ...

    def show_error(self, message: str) -> None: ...

    def show_preview(self, preview: Preview) -> None: ...

    def ask_preview_command(self, row_count: int) -> Union[PreviewCommand, EditRow]:
        """A preview command; an EditRow's number is within 1..row_count."""
        ...

    def ask_row_edit(
        self, row: PreviewRow, tracks: list[Track]
    ) -> Union[Track, RowEdit]:
        """One of `tracks` for the row, or what to do instead."""
        ...

    def refuse_apply(self, clashes: tuple[Clash, ...]) -> None: ...

    def announce_applied(self, written: int, renamed: int) -> None: ...


@dataclass
class _Search:
    """The album search of one run. The last album list is kept so `p`
    returns to it without searching again; None means search next time."""

    artist: Optional[str]
    album_name: Optional[str]
    # Only a year the user gave filters the search: a wrong folder or tag year
    # would hide the real album. Any year still helps the ranking.
    filter_year: Optional[int]
    rank_year: Optional[int]
    track_count: int
    ranked: Optional[list[RankedAlbum]] = None


class TagAlbum:
    """The album-first flow: pick one album, preview every file, then apply."""

    def __init__(
        self,
        read_source_files: SourceReader,
        catalog: AlbumCatalog,
        tag_writer: TagWriter,
        renamer: Renamer,
        track_finder: TrackFinder,
        interaction: Interaction,
    ):
        self._read = read_source_files
        self._catalog = catalog
        self._tag_writer = tag_writer
        self._renamer = renamer
        self._track_finder = track_finder
        self._ui = interaction

    def run(
        self,
        folder: Path,
        artist: Optional[str],
        year: Optional[int],
        album_id: Optional[str],
        rename: bool,
        dry_run: bool,
    ) -> None:
        """`artist` and `year` are the -a/-y overrides; `album_id` is --album's."""
        files = self._read(folder)
        if not files:
            self._ui.show_no_files(folder)
            return
        hints = derive_release_hints(files, folder.name)
        search = _Search(
            artist=artist or hints.artist,
            album_name=hints.album,
            filter_year=year,
            rank_year=year if year is not None else hints.year,
            track_count=len(files),
        )

        album = (
            self._catalog.album(album_id)
            if album_id is not None
            else self._choose_album(search)
        )
        while album is not None:
            tracks = self._catalog.album_tracks(album)
            assignments = assignments_from_match(match_album(files, tracks))
            if dry_run:
                self._ui.show_preview(build_preview(album, assignments, rename))
                return
            if self._review(search, album, tracks, assignments, rename) is not (
                PreviewCommand.BACK_TO_ALBUMS
            ):
                return
            album = self._choose_album(search)

    def _choose_album(self, search: _Search) -> Optional[Album]:
        """The album to tag from, or None when the user quits."""
        while True:
            if search.ranked is None:
                search.ranked = self._search_albums(search)
            assert search.artist and search.album_name
            choice = self._ui.choose_album(search.ranked, search.artist, search.album_name)
            if isinstance(choice, Album):
                return choice
            if isinstance(choice, AlbumLink):
                try:
                    return self._catalog.album(choice.album_id)
                except RuntimeError as error:
                    self._ui.show_error(str(error))
                    continue
            if choice is AlbumChoice.QUIT:
                return None
            search.artist, search.album_name = self._ui.edit_search(
                search.artist, search.album_name
            )
            search.ranked = None

    def _search_albums(self, search: _Search) -> list[RankedAlbum]:
        # Asked only here, so --album never prompts for them.
        if not search.artist:
            search.artist = self._ui.ask_artist()
        if not search.album_name:
            search.album_name = self._ui.ask_album_name()
        try:
            candidates = self._catalog.search_albums(
                search.artist, search.album_name, search.filter_year
            )
        except RuntimeError as error:
            # Treated as an empty result, so the user can edit the search or quit.
            self._ui.show_error(str(error))
            candidates = []
        hints = ReleaseHints(
            album=search.album_name,
            artist=search.artist,
            year=search.rank_year,
            track_count=search.track_count,
        )
        return rank_albums(hints, candidates)

    def _review(
        self,
        search: _Search,
        album: Album,
        tracks: list[Track],
        assignments: list[Assignment],
        rename: bool,
    ) -> PreviewCommand:
        """Show the preview and run its commands until apply, back or quit."""
        while True:
            preview = build_preview(album, assignments, rename)
            self._ui.show_preview(preview)
            command = self._ui.ask_preview_command(len(preview.rows))
            if isinstance(command, EditRow):
                index = command.number - 1
                assignments[index] = self._edit_row(
                    search, album, tracks, preview.rows[index]
                )
                continue
            if command is PreviewCommand.APPLY:
                if preview.clashes:
                    self._ui.refuse_apply(preview.clashes)
                    continue
                self._apply(preview, rename)
            return command

    def _edit_row(
        self, search: _Search, album: Album, tracks: list[Track], row: PreviewRow
    ) -> Assignment:
        edit = self._ui.ask_row_edit(row, tracks)
        if isinstance(edit, Track):
            return Assignment(row.file, edit, Mark.CHOSEN)
        if edit is RowEdit.KEEP:
            return Assignment(row.file, row.track, row.mark)
        if edit is RowEdit.SKIP:
            return Assignment(row.file, None, Mark.SKIP)
        # With --album and no -a there is no search artist; the album's first
        # artist is the best guess for a track on it.
        artist = search.artist or (album.artists[0].name if album.artists else "")
        track = self._track_finder.find_track(row.file.path, artist, search.filter_year)
        if track is None:
            return Assignment(row.file, None, Mark.SKIP)
        return Assignment(row.file, track, Mark.CHOSEN)

    def _apply(self, preview: Preview, rename: bool) -> None:
        written = [row for row in preview.rows if row.track is not None]
        for row in written:
            self._tag_writer.write_tags(row.file.path, track_tags(row.track))
        steps = rename_steps(preview.rows) if rename else []
        for path, new_name in steps:
            self._renamer.rename(path, new_name)
        renamed = sum(1 for row in written if row.new_name != row.old_name)
        self._ui.announce_applied(len(written), renamed)

