# musictags

## Description

Fixes tags on flac audio files for scrobbling on last.fm. Uses track information from spotify

![musictags4](https://github.com/badmagick329/musictags/assets/63713349/a975d6b2-bb6f-47e9-a807-cd74e26f4b5f)

## Usage

You will need your Client ID and Client Secret from spotify. Make sure you add it in a .env file. [Sample file](.env.sample)

1. pip install -r requirements.txt
2. py src/musictags.py

```
positional arguments:
  album_folder          Folder to search for flac files

options:
  -h, --help            show this help message and exit
  -a ARTIST, --artist ARTIST
                        Artist name
  -sr, --skip-renaming  Files will also be renamed (format: track_number track_name). Provide this flag to skip renaming files
```
