from pathlib import Path

from mutagen.flac import FLAC


def list_flac_files(folder: Path) -> list[Path]:
    return sorted(f for f in folder.iterdir() if f.is_file() and f.suffix == ".flac")


class FlacTagWriter:
    def write_tags(self, file: Path, tags: dict[str, str]) -> None:
        audio = FLAC(str(file))
        for key, value in tags.items():
            # Empty means Spotify had nothing; keep whatever the file already has.
            if not value:
                continue
            audio[key] = value
        audio.save()


class FileRenamer:
    def rename(self, file: Path, new_name: str) -> None:
        file.rename(file.parent / new_name)
