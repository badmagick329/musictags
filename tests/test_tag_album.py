import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
from factories import make_album, make_track

from musictags.domain.models import Album, Artist, Track
from musictags.domain.source import SourceFile
from musictags.domain.tags import track_tags
from musictags.features.tag_album.preview import (
    Clash,
    Mark,
    StrayTagCount,
    TagChange,
    rename_steps,
)
from musictags.features.tag_album.use_case import (
    AlbumChoice,
    AlbumLink,
    EditRow,
    PreviewCommand,
    RowEdit,
    TagAlbum,
)
from musictags.features.tag_tracks.use_case import TagTracks
from musictags.infrastructure.spotify import albums_from_search, tracks_from_album_page

FIXTURES = Path(__file__).parent / "fixtures" / "spotify"
FOLDER = Path("music/250314 MIDNIGHT SIGNAL")

# Genie's titles and file lengths for 250314 MIDNIGHT SIGNAL, in track order.
GENIE_MIDNIGHT = [
    ("MIDNIGHT SIGNAL (English Ver.)", 173.41),
    ("K.L.M (Kinder Louder Mood) (Feat. ORBIT GEM) (English Ver.)", 216.05),
    ("ENGINE (English Ver.)", 175.75),
    ("Over The Wall (ORBIT) (English Ver.)", 214.72),
    ("MIDNIGHT SIGNAL (Chinese Ver.)", 173.41),
    ("K.L.M (Kinder Louder Mood) (Feat. ORBIT GEM) (Chinese Ver.)", 216.05),
    ("ENGINE (Chinese Ver.)", 175.76),
    ("Over The Wall (ORBIT) (Chinese Ver.)", 214.71),
    ("FEVER (LEO & MIA) (English Edit)", 170.65),
    ("FEVER (LEO & MIA) (Spanish Edit)", 170.65),
    ("ECHO (RIN & SOL & KAI)", 255.15),
    ("Some Old Friend", 184.23),
    ("Gray Goose", 186.69),
    ("Drift", 195.95),
]


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def midnight() -> Album:
    return albums_from_search(fixture("search_albums_nova_midnight_signal.json"))[0]


@pytest.fixture
def midnight_tracks(midnight) -> list[Track]:
    return tracks_from_album_page(fixture("album_tracks_midnight_signal.json"), midnight)


def genie_file(number: int, title: str, length: float) -> SourceFile:
    """A file as Genie ships it, with the shop residue seen on the real album."""
    tags = {
        "TITLE": (title,),
        "ALBUM": ("MIDNIGHT SIGNAL",),
        "ALBUMARTIST": ("NOVA & ORBIT",),
        "ARTIST": ("NOVA & ORBIT",),
        "DATE": ("2025.03.14",),
        "YEAR": ("2025",),
        "TRACKNUMBER": (str(number),),
        "TRCK": (f"{number}/14",),
        "TRACKTOTAL": ("14",),
        "ALBUMTITLE": ("MIDNIGHT SIGNAL",),
        "COMMENT": ("지니뮤직",),
        "COPYRIGHT": ("해당곡의 저작권자",),
        "WWW": ("https://www.genie.co.kr",),
        "LYRICS": ("",),
    }
    return SourceFile.from_tags(FOLDER / f"{number:02}. {title}.flac", length, tags)


@pytest.fixture
def genie_files() -> list[SourceFile]:
    return [genie_file(n, t, l) for n, (t, l) in enumerate(GENIE_MIDNIGHT, 1)]


def bare_file(name: str, length: float = 180.0, **tags) -> SourceFile:
    return SourceFile.from_tags(
        FOLDER / name, length, {k.upper(): (v,) for k, v in tags.items()}
    )


class FakeCatalog:
    def __init__(self, searches=(), albums=None, tracks=None):
        self.searches = list(searches)
        self.albums = albums or {}
        self.tracks = tracks or {}
        self.search_calls = []
        self.album_calls = []
        self.tracks_calls = []

    def search_albums(self, artist, album, year=None):
        self.search_calls.append((artist, album, year))
        result = self.searches.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    def album(self, album_id):
        self.album_calls.append(album_id)
        result = self.albums[album_id]
        if isinstance(result, Exception):
            raise result
        return result

    def album_tracks(self, album):
        self.tracks_calls.append(album.id)
        return self.tracks[album.id]


class FakeTagWriter:
    def __init__(self):
        self.written = []

    def write_tags(self, file, tags):
        self.written.append((file, tags))


class FakeRenamer:
    def __init__(self):
        self.renamed = []

    def rename(self, file, new_name):
        self.renamed.append((file, new_name))


class FakeFinder:
    def __init__(self, *results):
        self.results = list(results)
        self.calls = []

    def find_track(self, file, artist, year):
        self.calls.append((file, artist, year))
        return self.results.pop(0)


class ScriptedUI:
    """Answers each prompt from its own script and records what it was shown.

    An album pick given as an int picks from the list as shown; a script that
    runs out raises IndexError, so an unexpected prompt fails the test.
    """

    def __init__(
        self,
        albums=(),
        commands=(),
        edits=(),
        artists=(),
        album_names=(),
        searches=(),
    ):
        self.albums = list(albums)
        self.commands = list(commands)
        self.edits = list(edits)
        self.artists = list(artists)
        self.album_names = list(album_names)
        self.searches = list(searches)
        self.offered = []
        self.previews = []
        self.edit_prompts = []
        self.errors = []
        self.refused = []
        self.applied = []
        self.no_files = []

    def show_no_files(self, folder):
        self.no_files.append(folder)

    def ask_artist(self):
        return self.artists.pop(0)

    def ask_album_name(self):
        return self.album_names.pop(0)

    def choose_album(self, ranked, artist, album_name):
        self.offered.append(([r.album for r in ranked], artist, album_name))
        choice = self.albums.pop(0)
        return ranked[choice].album if isinstance(choice, int) else choice

    def edit_search(self, artist, album_name):
        return self.searches.pop(0)

    def show_error(self, message):
        self.errors.append(message)

    def show_preview(self, preview):
        self.previews.append(preview)

    def ask_preview_command(self, row_count):
        return self.commands.pop(0)

    def ask_row_edit(self, row, tracks):
        self.edit_prompts.append(row.number)
        edit = self.edits.pop(0)
        return tracks[edit] if isinstance(edit, int) else edit

    def refuse_apply(self, clashes):
        self.refused.append(clashes)

    def announce_applied(self, written, renamed):
        self.applied.append((written, renamed))


class Harness:
    def __init__(self, files, catalog, ui, finder=None):
        self.files = files
        self.catalog = catalog
        self.ui = ui
        self.finder = finder or FakeFinder()
        self.writer = FakeTagWriter()
        self.renamer = FakeRenamer()
        self.read_folders = []

    def read(self, folder):
        self.read_folders.append(folder)
        return self.files

    def run(self, folder=FOLDER, artist=None, year=None, album_id=None, rename=True, dry_run=False):
        TagAlbum(self.read, self.catalog, self.writer, self.renamer, self.finder, self.ui).run(
            folder, artist, year, album_id, rename, dry_run
        )
        return self


@pytest.fixture
def catalog(midnight, midnight_tracks):
    return FakeCatalog(
        searches=[[midnight]],
        albums={midnight.id: midnight},
        tracks={midnight.id: midnight_tracks},
    )


def test_midnight_signal_preview_pairs_every_file_with_its_own_version(
    genie_files, catalog, midnight, midnight_tracks
):
    ui = ScriptedUI(albums=[0], commands=[PreviewCommand.QUIT])

    Harness(genie_files, catalog, ui).run()

    assert catalog.search_calls == [("NOVA", "MIDNIGHT SIGNAL", None)]
    [preview] = ui.previews
    assert preview.album == midnight
    assert [(r.number, r.track, r.mark) for r in preview.rows] == [
        (n, track, Mark.SURE) for n, track in enumerate(midnight_tracks, 1)
    ]
    assert [r.new_name for r in preview.rows[:2]] == [
        # The trailing dot stays: Spotify's name ends in "Ver.".
        "01 MIDNIGHT SIGNAL - English Ver..flac",
        "02 K.L.M (Kinder Louder Mood) [feat. ORBIT GEM] - English Ver..flac",
    ]
    assert preview.rows[13].old_name == "14. Drift.flac"
    assert preview.rows[13].new_name == "14 Drift.flac"
    assert preview.album_changes == (
        TagChange("ALBUMARTIST", "NOVA & ORBIT", "NOVA"),
        TagChange("DATE", "2025.03.14", "2025-03-14"),
    )
    assert preview.stray == tuple(
        StrayTagCount(key, 14)
        for key in ("YEAR", "TRCK", "ALBUMTITLE", "COMMENT", "COPYRIGHT", "WWW", "LYRICS")
    )
    assert preview.clashes == ()


def test_apply_writes_and_renames_matched_files_only(genie_files, catalog, midnight_tracks):
    bonus = genie_file(15, "Bonus Track", 240.5)
    files = genie_files[:13] + [bonus]
    ui = ScriptedUI(albums=[0], commands=[PreviewCommand.APPLY])

    h = Harness(files, catalog, ui).run()

    assert ui.previews[0].rows[13].mark is Mark.SKIP
    assert h.writer.written == [
        (f.path, track_tags(t)) for f, t in zip(files[:13], midnight_tracks)
    ]
    assert [path for path, _ in h.renamer.renamed] == [f.path for f in files[:13]]
    assert h.renamer.renamed[0][1] == "01 MIDNIGHT SIGNAL - English Ver..flac"
    assert bonus.path not in [p for p, _ in h.writer.written + h.renamer.renamed]
    assert ui.applied == [(13, 13)]


def test_unsure_rows_are_written_too():
    file = bare_file("01 Song.flac", length=185.0, title="Song")
    album = make_album(total_tracks=1)
    track = replace(make_track(name="Song", length=180.0), album=album)
    catalog = FakeCatalog(searches=[[album]], tracks={album.id: [track]})
    ui = ScriptedUI(albums=[0], commands=[PreviewCommand.APPLY])

    h = Harness([file], catalog, ui).run(artist="Artist")

    assert ui.previews[0].rows[0].mark is Mark.UNSURE
    assert h.writer.written == [(file.path, track_tags(track))]


def test_quit_at_preview_writes_nothing(genie_files, catalog):
    ui = ScriptedUI(albums=[0], commands=[PreviewCommand.QUIT])

    h = Harness(genie_files, catalog, ui).run()

    assert h.writer.written == [] and h.renamer.renamed == []
    assert ui.applied == []


def test_quit_at_album_list_fetches_no_tracks(genie_files, catalog):
    ui = ScriptedUI(albums=[AlbumChoice.QUIT])

    h = Harness(genie_files, catalog, ui).run()

    assert catalog.tracks_calls == [] and ui.previews == []
    assert h.writer.written == []


def test_dry_run_shows_the_preview_without_asking_or_writing(genie_files, catalog):
    # No preview commands are scripted, so asking for one would fail.
    ui = ScriptedUI(albums=[0])

    h = Harness(genie_files, catalog, ui).run(dry_run=True)

    assert len(ui.previews) == 1
    assert h.writer.written == [] and h.renamer.renamed == []


def test_skip_renaming_keeps_names_and_still_writes(genie_files, catalog):
    ui = ScriptedUI(albums=[0], commands=[PreviewCommand.APPLY])

    h = Harness(genie_files, catalog, ui).run(rename=False)

    assert all(r.new_name == r.old_name for r in ui.previews[0].rows)
    assert len(h.writer.written) == 14
    assert h.renamer.renamed == []
    assert ui.applied == [(14, 0)]


def test_edit_assigns_an_album_track_and_redraws(genie_files, catalog, midnight_tracks):
    ui = ScriptedUI(
        albums=[0], commands=[EditRow(1), PreviewCommand.APPLY], edits=[4]
    )

    h = Harness(genie_files[:1], catalog, ui).run()

    assert ui.edit_prompts == [1]
    assert len(ui.previews) == 2
    row = ui.previews[1].rows[0]
    assert (row.track, row.mark) == (midnight_tracks[4], Mark.CHOSEN)
    assert h.writer.written == [(genie_files[0].path, track_tags(midnight_tracks[4]))]
    assert h.renamer.renamed == [(genie_files[0].path, "05 MIDNIGHT SIGNAL - Chinese Ver..flac")]


def test_edit_skip_leaves_the_file_untouched(genie_files, catalog):
    ui = ScriptedUI(
        albums=[0], commands=[EditRow(2), PreviewCommand.APPLY], edits=[RowEdit.SKIP]
    )

    h = Harness(genie_files[:3], catalog, ui).run()

    row = ui.previews[1].rows[1]
    assert (row.track, row.mark, row.new_name) == (None, Mark.SKIP, row.old_name)
    assert [p for p, _ in h.writer.written] == [genie_files[0].path, genie_files[2].path]
    assert genie_files[1].path not in [p for p, _ in h.renamer.renamed]


def test_edit_keep_leaves_the_row_as_it_was(genie_files, catalog):
    ui = ScriptedUI(
        albums=[0], commands=[EditRow(1), PreviewCommand.QUIT], edits=[RowEdit.KEEP]
    )

    Harness(genie_files[:1], catalog, ui).run()

    assert ui.previews[1].rows == ui.previews[0].rows


def test_edit_search_runs_the_per_file_search(genie_files, catalog):
    single = make_track(name="MIDNIGHT SIGNAL", track_number=1, artist="NOVA")
    finder = FakeFinder(single)
    ui = ScriptedUI(
        albums=[0], commands=[EditRow(1), PreviewCommand.APPLY], edits=[RowEdit.SEARCH]
    )

    h = Harness(genie_files[:1], catalog, ui, finder).run(year=2025)

    assert finder.calls == [(genie_files[0].path, "NOVA", 2025)]
    assert ui.previews[1].rows[0].mark is Mark.CHOSEN
    assert h.writer.written == [(genie_files[0].path, track_tags(single))]


def test_edit_search_drives_tag_tracks_find_track(genie_files, catalog):
    """The real per-file search, with its own fakes: the user types a name and
    picks the first result."""
    found = make_track(name="MIDNIGHT SIGNAL", artist="NOVA")

    class TrackSearch:
        calls = []

        def search_tracks(self, artist, name, year):
            self.calls.append((artist, name, year))
            return [found]

    class TrackUI:
        def ask_track_name(self, filename, suggestion):
            return "MIDNIGHT SIGNAL"

        def announce_search(self, name):
            pass

        def ask_after_no_results(self, artist, name):
            raise AssertionError("unexpected")

        def choose_track(self, tracks):
            return tracks[0]

    search = TrackSearch()
    finder = TagTracks(search, FakeTagWriter(), FakeRenamer(), TrackUI())
    ui = ScriptedUI(
        albums=[0], commands=[EditRow(1), PreviewCommand.QUIT], edits=[RowEdit.SEARCH]
    )

    Harness(genie_files[:1], catalog, ui, finder).run()

    assert search.calls == [("NOVA", "MIDNIGHT SIGNAL", None)]
    assert ui.previews[1].rows[0].track is found


def test_edit_search_skipped_skips_the_row(genie_files, catalog):
    ui = ScriptedUI(
        albums=[0], commands=[EditRow(1), PreviewCommand.APPLY], edits=[RowEdit.SEARCH]
    )

    h = Harness(genie_files[:1], catalog, ui, FakeFinder(None)).run()

    assert ui.previews[1].rows[0].mark is Mark.SKIP
    assert h.writer.written == []


def test_back_returns_to_the_album_list_without_searching_again(
    genie_files, midnight, midnight_tracks
):
    cover = make_album(name="Midnight Signal (Cover)", artist="Cover Duo", total_tracks=1, album_id="c" * 22)
    cover_track = replace(make_track(name="Midnight Signal", length=173.0), album=cover)
    catalog = FakeCatalog(
        searches=[[cover, midnight]],
        tracks={midnight.id: midnight_tracks, cover.id: [cover_track]},
    )
    # The ranking puts the real album first; the user picks the cover, backs out
    # and picks the album.
    ui = ScriptedUI(
        albums=[1, 0], commands=[PreviewCommand.BACK_TO_ALBUMS, PreviewCommand.APPLY]
    )

    h = Harness(genie_files, catalog, ui).run()

    assert len(catalog.search_calls) == 1
    assert ui.offered[0] == ui.offered[1]
    assert [p.album for p in ui.previews] == [cover, midnight]
    assert len(h.writer.written) == 14


def test_pasted_link_bypasses_the_list(genie_files, catalog, midnight):
    ui = ScriptedUI(albums=[AlbumLink(midnight.id)], commands=[PreviewCommand.QUIT])

    Harness(genie_files, catalog, ui).run()

    assert catalog.album_calls == [midnight.id]
    assert ui.previews[0].album == midnight


def test_a_failed_link_lookup_is_shown_and_the_list_offered_again(genie_files, catalog, midnight):
    catalog.albums["x" * 22] = RuntimeError("Spotify search failed (404): Resource not found")
    ui = ScriptedUI(albums=[AlbumLink("x" * 22), 0], commands=[PreviewCommand.QUIT])

    Harness(genie_files, catalog, ui).run()

    assert ui.errors == ["Spotify search failed (404): Resource not found"]
    assert len(ui.offered) == 2 and len(catalog.search_calls) == 1
    assert ui.previews[0].album == midnight


def test_album_id_skips_the_search_and_every_prompt(midnight, midnight_tracks):
    # No tags and a folder name without hints: the search would need both
    # prompts, which are not scripted.
    files = [bare_file(f"{n:02}.flac", length) for n, (_, length) in enumerate(GENIE_MIDNIGHT, 1)]
    catalog = FakeCatalog(albums={midnight.id: midnight}, tracks={midnight.id: midnight_tracks})
    ui = ScriptedUI(commands=[PreviewCommand.QUIT])

    Harness(files, catalog, ui).run(folder=Path(""), album_id=midnight.id)

    assert catalog.search_calls == [] and ui.offered == []
    assert catalog.album_calls == [midnight.id]
    assert ui.previews[0].album == midnight


def test_album_id_then_back_searches_with_prompts(midnight, midnight_tracks):
    files = [bare_file("01.flac")]
    catalog = FakeCatalog(
        searches=[[midnight]],
        albums={midnight.id: midnight},
        tracks={midnight.id: midnight_tracks},
    )
    ui = ScriptedUI(
        commands=[PreviewCommand.BACK_TO_ALBUMS],
        albums=[AlbumChoice.QUIT],
        artists=["NOVA"],
        album_names=["MIDNIGHT SIGNAL"],
    )

    Harness(files, catalog, ui).run(folder=Path(""), album_id=midnight.id)

    assert catalog.search_calls == [("NOVA", "MIDNIGHT SIGNAL", None)]


def test_edit_search_with_album_id_falls_back_to_the_album_artist(midnight, midnight_tracks):
    files = [bare_file("01.flac")]
    catalog = FakeCatalog(albums={midnight.id: midnight}, tracks={midnight.id: midnight_tracks})
    finder = FakeFinder(None)
    ui = ScriptedUI(commands=[EditRow(1), PreviewCommand.QUIT], edits=[RowEdit.SEARCH])

    Harness(files, catalog, ui, finder).run(folder=Path("misc"), album_id=midnight.id)

    assert finder.calls == [(files[0].path, "NOVA", None)]


@pytest.mark.parametrize(
    ("folder", "tags", "artist", "asked_artist", "asked_album"),
    [
        # Nothing known: both are asked.
        ("", {}, None, ["Typed"], ["Typed album"]),
        # The album comes from the folder name, the artist from -a.
        ("250314 MIDNIGHT SIGNAL", {}, "NOVA", [], []),
        # Source tags give the artist; the album is asked.
        ("", {"albumartist": "NOVA & ORBIT"}, None, [], ["Typed album"]),
        # Source tags give the album; the artist is asked.
        ("", {"album": "MIDNIGHT SIGNAL"}, None, ["Typed"], []),
    ],
)
def test_prompts_only_for_a_missing_artist_or_album(
    midnight, folder, tags, artist, asked_artist, asked_album
):
    catalog = FakeCatalog(searches=[[]])
    ui = ScriptedUI(
        albums=[AlbumChoice.QUIT], artists=list(asked_artist), album_names=list(asked_album)
    )

    Harness([bare_file("01.flac", **tags)], catalog, ui).run(folder=Path(folder), artist=artist)

    # Every scripted answer was used, and no other prompt came up.
    assert ui.artists == [] and ui.album_names == []
    [(searched_artist, searched_album, _)] = catalog.search_calls
    assert searched_artist == (asked_artist[0] if asked_artist else artist or "NOVA")
    assert searched_album == (asked_album[0] if asked_album else "MIDNIGHT SIGNAL")


def test_artist_override_beats_the_source_tags(genie_files, catalog):
    ui = ScriptedUI(albums=[AlbumChoice.QUIT])

    Harness(genie_files, catalog, ui).run(artist="ORBIT")

    assert catalog.search_calls == [("ORBIT", "MIDNIGHT SIGNAL", None)]


def test_only_a_given_year_filters_the_search_but_the_hint_year_ranks():
    # Spotify lists the re-release first; the folder's year ranks the original
    # above it without being sent as a filter.
    original = make_album(name="Album", release_date=date(2020, 1, 1), album_id="o" * 22)
    rerelease = make_album(name="Album", release_date=date(2023, 1, 1), album_id="r" * 22)
    catalog = FakeCatalog(searches=[[rerelease, original]])
    ui = ScriptedUI(albums=[AlbumChoice.QUIT])

    Harness([bare_file("01.flac", artist="Artist")], catalog, ui).run(folder=Path("200101 Album"))

    assert catalog.search_calls == [("Artist", "Album", None)]
    assert ui.offered[0][0] == [original, rerelease]


def test_a_given_year_filters_the_search(genie_files, catalog):
    ui = ScriptedUI(albums=[AlbumChoice.QUIT])

    Harness(genie_files, catalog, ui).run(year=2024)

    assert catalog.search_calls == [("NOVA", "MIDNIGHT SIGNAL", 2024)]


def test_edit_search_searches_again_with_the_new_terms(genie_files, catalog, midnight):
    catalog.searches = [[], [midnight]]
    ui = ScriptedUI(
        albums=[AlbumChoice.EDIT_SEARCH, 0],
        searches=[("NOVA", "MIDNIGHT")],
        commands=[PreviewCommand.QUIT],
    )

    Harness(genie_files, catalog, ui).run()

    assert catalog.search_calls == [
        ("NOVA", "MIDNIGHT SIGNAL", None),
        ("NOVA", "MIDNIGHT", None),
    ]
    assert ui.offered[0] == ([], "NOVA", "MIDNIGHT SIGNAL")


def test_a_failed_search_is_shown_as_an_empty_list(genie_files, catalog):
    catalog.searches = [RuntimeError("Spotify search failed (503): No response body")]
    ui = ScriptedUI(albums=[AlbumChoice.QUIT])

    Harness(genie_files, catalog, ui).run()

    assert ui.errors == ["Spotify search failed (503): No response body"]
    assert ui.offered == [([], "NOVA", "MIDNIGHT SIGNAL")]


def test_an_empty_folder_says_so_and_searches_nothing():
    catalog = FakeCatalog()
    ui = ScriptedUI()

    Harness([], catalog, ui).run()

    assert ui.no_files == [FOLDER] and catalog.search_calls == []


def two_track_album():
    album = make_album(total_tracks=2)
    one = replace(make_track(name="One", track_number=1, length=180.0), album=album)
    two = replace(make_track(name="Two", track_number=2, length=200.0), album=album)
    return album, [one, two]


def test_a_rename_clash_blocks_apply_and_names_the_rows():
    album, tracks = two_track_album()
    files = [
        bare_file("a.flac", length=180.0, title="One"),
        bare_file("b.flac", length=200.0, title="Two"),
    ]
    catalog = FakeCatalog(searches=[[album]], tracks={album.id: tracks})
    # Row 2 gets track 1 too, so both files would be "01 One.flac".
    ui = ScriptedUI(
        albums=[0],
        commands=[EditRow(2), PreviewCommand.APPLY, PreviewCommand.QUIT],
        edits=[0],
    )

    h = Harness(files, catalog, ui).run(artist="Artist")

    assert ui.refused == [(Clash("01 One.flac", (1, 2)),)]
    assert h.writer.written == [] and h.renamer.renamed == []


def test_a_new_name_taken_by_a_file_that_stays_put_clashes_case_insensitively():
    album, tracks = two_track_album()
    files = [
        # Unmatched and so left alone, but it holds track 2's name.
        bare_file("02 two.flac", length=400.0, title="Zzzz"),
        bare_file("b.flac", length=200.0, title="Two"),
    ]
    catalog = FakeCatalog(searches=[[album]], tracks={album.id: tracks})
    ui = ScriptedUI(albums=[0], commands=[PreviewCommand.APPLY, PreviewCommand.QUIT])

    h = Harness(files, catalog, ui).run(artist="Artist")

    assert ui.previews[0].rows[0].mark is Mark.SKIP
    assert ui.refused == [(Clash("02 two.flac", (1, 2)),)]
    assert h.writer.written == []


def test_skip_renaming_cannot_clash():
    album, tracks = two_track_album()
    files = [
        bare_file("a.flac", length=180.0, title="One"),
        bare_file("b.flac", length=200.0, title="Two"),
    ]
    catalog = FakeCatalog(searches=[[album]], tracks={album.id: tracks})
    ui = ScriptedUI(albums=[0], commands=[EditRow(2), PreviewCommand.APPLY], edits=[0])

    h = Harness(files, catalog, ui).run(artist="Artist", rename=False)

    assert ui.refused == []
    assert len(h.writer.written) == 2


def test_swapped_names_are_renamed_through_a_temporary_name():
    album, tracks = two_track_album()
    # Each file carries the other's name, so either rename alone would overwrite.
    files = [
        bare_file("02 Two.flac", length=180.0, title="One"),
        bare_file("01 One.flac", length=200.0, title="Two"),
    ]
    catalog = FakeCatalog(searches=[[album]], tracks={album.id: tracks})
    ui = ScriptedUI(albums=[0], commands=[PreviewCommand.APPLY])

    h = Harness(files, catalog, ui).run(artist="Artist")

    temp = FOLDER / ".musictags-rename-1.flac"
    assert h.renamer.renamed == [
        (FOLDER / "02 Two.flac", temp.name),
        (FOLDER / "01 One.flac", "02 Two.flac"),
        (temp, "01 One.flac"),
    ]


def test_rename_steps_wait_for_a_target_to_be_freed():
    album, tracks = two_track_album()
    # x.flac comes first but must wait until 01 One.flac has moved.
    files = [
        bare_file("x.flac", length=180.0, title="One"),
        bare_file("01 One.flac", length=200.0, title="Two"),
    ]
    catalog = FakeCatalog(searches=[[album]], tracks={album.id: tracks})
    ui = ScriptedUI(albums=[0], commands=[PreviewCommand.QUIT])
    Harness(files, catalog, ui).run(artist="Artist")

    assert rename_steps(ui.previews[0].rows) == [
        (FOLDER / "01 One.flac", "02 Two.flac"),
        (FOLDER / "x.flac", "01 One.flac"),
    ]


def test_a_case_only_rename_is_kept():
    album, tracks = two_track_album()
    files = [bare_file("01 one.flac", length=180.0, title="One")]
    catalog = FakeCatalog(searches=[[album]], tracks={album.id: tracks})
    ui = ScriptedUI(albums=[0], commands=[PreviewCommand.APPLY])

    h = Harness(files, catalog, ui).run(artist="Artist")

    assert ui.previews[0].clashes == ()
    assert h.renamer.renamed == [(FOLDER / "01 one.flac", "01 One.flac")]


def test_an_unchanged_name_is_not_renamed():
    album, tracks = two_track_album()
    files = [bare_file("01 One.flac", length=180.0, title="One")]
    catalog = FakeCatalog(searches=[[album]], tracks={album.id: tracks})
    ui = ScriptedUI(albums=[0], commands=[PreviewCommand.APPLY])

    h = Harness(files, catalog, ui).run(artist="Artist")

    assert len(h.writer.written) == 1 and h.renamer.renamed == []
    assert ui.applied == [(1, 0)]


def test_album_changes_use_the_most_common_value_and_skip_unchanged_ones():
    album = Album(
        id="a" * 22,
        name="Album",
        artists=(Artist("Artist"),),
        album_type="album",
        release_date=None,
        total_tracks=3,
    )
    tracks = [
        replace(make_track(name=n, track_number=i, length=180.0 + 30 * i), album=album)
        for i, n in enumerate(["One", "Two", "Three"], 1)
    ]
    files = [
        bare_file("1.flac", 210.0, title="One", album="Album", tracktotal="3"),
        bare_file("2.flac", 240.0, title="Two", album="Album (Deluxe)", tracktotal="3"),
        bare_file("3.flac", 270.0, title="Three", album="Album", tracktotal="12"),
    ]
    catalog = FakeCatalog(searches=[[album]], tracks={album.id: tracks})
    ui = ScriptedUI(albums=[0], commands=[PreviewCommand.QUIT])

    Harness(files, catalog, ui).run(artist="Artist")

    # ALBUM and TRACKTOTAL agree with the majority, DATE is unknown on Spotify
    # (left as is), and no file has an ALBUMARTIST.
    assert ui.previews[0].album_changes == (TagChange("ALBUMARTIST", None, "Artist"),)


def test_stray_summary_counts_only_files_to_be_written():
    album, tracks = two_track_album()
    files = [
        bare_file("a.flac", length=180.0, title="One", comment="shop", www="url"),
        bare_file("b.flac", length=400.0, title="Zzzz", comment="shop"),
    ]
    catalog = FakeCatalog(searches=[[album]], tracks={album.id: tracks})
    ui = ScriptedUI(albums=[0], commands=[PreviewCommand.QUIT])

    Harness(files, catalog, ui).run(artist="Artist")

    assert ui.previews[0].stray == (StrayTagCount("COMMENT", 1), StrayTagCount("WWW", 1))
