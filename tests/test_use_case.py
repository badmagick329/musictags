from datetime import date
from pathlib import Path

from factories import make_track

from musictags.features.tag_tracks.use_case import Choice, TagTracks


class FakeSearch:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def search_tracks(self, artist, name, year):
        self.calls.append((artist, name, year))
        return self.responses.pop(0)


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


class ScriptedInteraction:
    """Answers each prompt from a per-prompt script and records what it was shown."""

    def __init__(self, names=(), after_no_results=(), choices=()):
        self.names = list(names)
        self.after_no_results = list(after_no_results)
        self.choices = list(choices)
        self.name_prompts = []
        self.searched = []
        self.offered = []

    def ask_track_name(self, filename, suggestion):
        self.name_prompts.append((filename, suggestion))
        return self.names.pop(0)

    def announce_search(self, name):
        self.searched.append(name)

    def ask_after_no_results(self, artist, name):
        return self.after_no_results.pop(0)

    def choose_track(self, tracks):
        self.offered.append(list(tracks))
        choice = self.choices.pop(0)
        # An int picks from the list as shown, like the user typing an index.
        return tracks[choice] if isinstance(choice, int) else choice


def run(files, search, ui, rename=True, year=None):
    writer, renamer = FakeTagWriter(), FakeRenamer()
    TagTracks(search, writer, renamer, ui).run(
        [Path(f) for f in files], "Artist", year, rename=rename
    )
    return writer, renamer


def test_selected_track_is_tagged_and_renamed():
    track = make_track(name="Who: Me?", track_number=3)
    ui = ScriptedInteraction(names=["Who Me"], choices=[0])
    search = FakeSearch([track])

    writer, renamer = run(["music/03 - who me.flac"], search, ui, year=2020)

    assert search.calls == [("Artist", "Who Me", 2020)]
    assert ui.searched == ["Who Me"]
    assert writer.written == [(Path("music/03 - who me.flac"), {
        "ALBUM": "Album",
        "ARTIST": "Artist",
        "ARTISTS": "Artist",
        "DATE": "2020-08-28",
        "TITLE": "Who: Me?",
        "TRACKNUMBER": "3",
        "TRACKTOTAL": "10",
    })]
    assert renamer.renamed == [(Path("music/03 - who me.flac"), "03 Who_ Me_.flac")]


def test_skip_renaming_still_writes_tags():
    ui = ScriptedInteraction(names=["Song"], choices=[0])
    writer, renamer = run(["a.flac"], FakeSearch([make_track()]), ui, rename=False)

    assert len(writer.written) == 1
    assert renamer.renamed == []


def test_suggestion_is_offered_and_used():
    ui = ScriptedInteraction(names=[Choice.USE_SUGGESTION], choices=[0])
    search = FakeSearch([make_track()])

    run(["01. Ice Cream.flac"], search, ui)

    assert ui.name_prompts == [("01. Ice Cream", "Ice Cream")]
    assert search.calls == [("Artist", "Ice Cream", None)]


def test_skip_at_name_prompt_touches_nothing():
    ui = ScriptedInteraction(names=[Choice.SKIP])
    search = FakeSearch()

    writer, renamer = run(["a.flac"], search, ui)

    assert search.calls == []
    assert writer.written == [] and renamer.renamed == []


def test_skip_at_result_list_moves_to_next_file():
    ui = ScriptedInteraction(names=["One", "Two"], choices=[Choice.SKIP, 0])
    search = FakeSearch([make_track(name="One")], [make_track(name="Two")])

    writer, _ = run(["1.flac", "2.flac"], search, ui)

    assert [f for f, _ in writer.written] == [Path("2.flac")]


def test_new_search_asks_for_name_again():
    wanted = make_track(name="Right")
    ui = ScriptedInteraction(names=["Wrong", "Right"], choices=[Choice.SEARCH_AGAIN, 0])
    search = FakeSearch([make_track(name="Wrong")], [wanted])

    writer, _ = run(["a.flac"], search, ui)

    assert [c[1] for c in search.calls] == ["Wrong", "Right"]
    assert writer.written[0][1]["TITLE"] == "Right"


def test_no_results_then_search_again():
    ui = ScriptedInteraction(
        names=["Typo", "Fixed"], after_no_results=[Choice.SEARCH_AGAIN], choices=[0]
    )
    search = FakeSearch([], [make_track(name="Fixed")])

    writer, _ = run(["a.flac"], search, ui)

    assert [c[1] for c in search.calls] == ["Typo", "Fixed"]
    assert writer.written[0][1]["TITLE"] == "Fixed"


def test_no_results_then_skip():
    ui = ScriptedInteraction(names=["Typo"], after_no_results=[Choice.SKIP])

    writer, renamer = run(["a.flac"], FakeSearch([]), ui)

    assert ui.offered == []
    assert writer.written == [] and renamer.renamed == []


def test_results_from_previous_release_date_are_listed_first():
    album_day = date(2020, 10, 2)
    first = make_track(name="A", release_date=album_day)
    single = make_track(name="B single", release_date=date(2020, 8, 28))
    unknown = make_track(name="B unknown", release_date=None)
    other = make_track(name="B other", release_date=date(2019, 1, 1))
    album_cut = make_track(name="B album", release_date=album_day)
    ui = ScriptedInteraction(names=["A", "B"], choices=[0, 0])
    search = FakeSearch([first], [single, unknown, album_cut, other])

    run(["1.flac", "2.flac"], search, ui)

    assert ui.offered[1] == [album_cut, single, unknown, other]


def test_first_file_keeps_spotify_order():
    tracks = [
        make_track(name="X", release_date=date(2019, 1, 1)),
        make_track(name="Y", release_date=date(2020, 1, 1)),
    ]
    ui = ScriptedInteraction(names=["X"], choices=[1])

    run(["1.flac"], FakeSearch(tracks), ui)

    assert ui.offered == [tracks]


def test_picking_undated_track_stops_reordering():
    dated = make_track(name="Dated", release_date=date(2020, 1, 1))
    undated = make_track(name="Undated", release_date=None)
    later = [make_track(name="Other", release_date=date(1999, 1, 1)), dated]
    ui = ScriptedInteraction(names=["a", "b", "c"], choices=[0, 0, 0])
    search = FakeSearch([dated], [undated], list(later))

    run(["1.flac", "2.flac", "3.flac"], search, ui)

    assert ui.offered[2] == later
