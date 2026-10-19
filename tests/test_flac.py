import pytest
from mutagen.flac import FLAC

from musictags.infrastructure.flac import (
    FileRenamer,
    list_flac_files,
    read_source_files,
)


def write_flac(file, seconds: int, tags: dict[str, list[str]]) -> None:
    """Write a FLAC with a STREAMINFO block and no audio frames.

    mutagen reads only metadata, so this stands in for real audio without
    committing any; the length comes from STREAMINFO's sample count.
    """
    sample_rate, channels, bits = 44100, 2, 16
    packed = (
        (sample_rate << 44)
        | ((channels - 1) << 41)
        | ((bits - 1) << 36)
        | (seconds * sample_rate)
    )
    streaminfo = (
        (4096).to_bytes(2, "big") * 2
        + bytes(6)
        + packed.to_bytes(8, "big")
        + bytes(16)
    )
    # Header byte 0x80: last metadata block, type 0 (STREAMINFO).
    file.write_bytes(b"fLaC" + bytes([0x80]) + len(streaminfo).to_bytes(3, "big") + streaminfo)
    audio = FLAC(str(file))
    for key, values in tags.items():
        audio[key] = values
    audio.save()


def test_reads_source_tags_and_length(tmp_path):
    write_flac(
        tmp_path / "02. Song.flac",
        seconds=10,
        tags={
            "TITLE": ["Song (English Ver.)"],
            "TRACKNUMBER": ["2"],
            "DISCNUMBER": ["1/1"],
            "ALBUM": ["MIDNIGHT SIGNAL"],
            "AlbumArtist": ["NOVA & ORBIT"],
            "ARTIST": ["NOVA & ORBIT"],
            "DATE": ["2025.03.14"],
            "TRCK": ["8/25"],
            "WWW": ["https://a", "https://b"],
        },
    )
    (tmp_path / "cover.jpg").write_bytes(b"")

    [file] = read_source_files(tmp_path)

    assert file.path == tmp_path / "02. Song.flac"
    assert file.length == pytest.approx(10.0)
    assert (file.track_number, file.disc_number) == (2, 1)
    assert file.title == "Song (English Ver.)"
    assert file.album == "MIDNIGHT SIGNAL"
    assert file.album_artist == "NOVA & ORBIT"
    assert file.year == 2025
    assert file.tags["ALBUMARTIST"] == ("NOVA & ORBIT",)
    assert file.tags["WWW"] == ("https://a", "https://b")


def test_untagged_file_takes_track_number_from_filename(tmp_path):
    write_flac(tmp_path / "07 Song.flac", seconds=3, tags={})

    [file] = read_source_files(tmp_path)

    assert (file.track_number, file.title, file.tags) == (7, None, {})


def test_unreadable_file_names_the_file(tmp_path):
    (tmp_path / "01 Broken.flac").write_bytes(b"not a flac")

    with pytest.raises(RuntimeError, match="01 Broken.flac"):
        read_source_files(tmp_path)


def test_lists_flac_files_sorted_by_name(tmp_path):
    for name in ["10 b.flac", "02 a.flac", "cover.jpg", "upper.FLAC"]:
        (tmp_path / name).write_bytes(b"")
    (tmp_path / "disc 2.flac").mkdir()
    (tmp_path / "disc 2.flac" / "01 nested.flac").write_bytes(b"")

    assert [f.name for f in list_flac_files(tmp_path)] == ["02 a.flac", "10 b.flac"]


def test_rename_keeps_file_in_its_folder(tmp_path):
    file = tmp_path / "old.flac"
    file.write_bytes(b"audio")

    FileRenamer().rename(file, "01 New.flac")

    assert [f.name for f in tmp_path.iterdir()] == ["01 New.flac"]
    assert (tmp_path / "01 New.flac").read_bytes() == b"audio"
