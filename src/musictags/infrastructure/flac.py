from pathlib import Path

from mutagen import MutagenError
from mutagen.flac import FLAC

from musictags.domain.source import SourceFile, SourceTags
from musictags.domain.tags import stray_tags


def list_flac_files(folder: Path) -> list[Path]:
    return sorted(f for f in folder.iterdir() if f.is_file() and f.suffix == ".flac")


def read_source_files(folder: Path) -> list[SourceFile]:
    """Read every file's source tags and length; never writes to the files."""
    return [_read_source_file(file) for file in list_flac_files(folder)]


def _read_source_file(file: Path) -> SourceFile:
    try:
        audio = FLAC(str(file))
    except MutagenError as error:
        raise RuntimeError(f"Could not read {file.name}: {error}") from error
    return SourceFile.from_tags(file, audio.info.length, _source_tags(audio))


def _source_tags(audio: FLAC) -> SourceTags:
    # Vorbis keys are case-insensitive, so "Artist" and "ARTIST" are one tag.
    tags: dict[str, list[str]] = {}
    for key, value in audio.tags or []:
        tags.setdefault(key.upper(), []).append(value)
    return {key: tuple(values) for key, values in tags.items()}


class FlacTagWriter:
    def write_tags(self, file: Path, tags: dict[str, str]) -> None:
        """Set `tags` and remove the file's stray tags in a single save.

        Stray tags are judged against the file's tags as they are now, so the
        file is read here rather than trusting an earlier `SourceFile`.
        """
        audio = FLAC(str(file))
        for key in stray_tags(_source_tags(audio), tags):
            # mutagen matches Vorbis keys case-insensitively, so this drops
            # "Comment" and "COMMENT" alike.
            del audio[key]
        for key, value in tags.items():
            # Empty means Spotify had nothing; keep whatever the file already has.
            if not value:
                continue
            audio[key] = value
        audio.save()


class FileRenamer:
    def rename(self, file: Path, new_name: str) -> None:
        file.rename(file.parent / new_name)
