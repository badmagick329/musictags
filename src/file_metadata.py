from mutagen.flac import FLAC


class FlacMetadata:
    file: str
    audio: FLAC

    def __init__(self, file: str):
        self.file = file
        self.audio = FLAC(self.file)

    def set_tags(self, tags: dict[str, str]):
        for key, value in tags.items():
            if not value:
                continue
            self.audio[key] = value
        self.audio.save()

    def __str__(self):
        return self.audio.pprint()
