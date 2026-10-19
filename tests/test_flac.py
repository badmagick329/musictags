from musictags.infrastructure.flac import FileRenamer, list_flac_files


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
