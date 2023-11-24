# musictags

## Description

Fixes tags on flac audio files for scrobbling on last.fm. Uses track information from spotify

## Usage

You will need your Client ID and Client Secret from spotify. Make sure you add it in a .env file. [Sample file](.env.sample)

1. pip install -r requirements.txt
2. py src/main.py

```
positional arguments:
  album_folder          Folder to search for flac files

options:
  -h, --help            show this help message and exit
  -a ARTIST, --artist ARTIST
                        Artist name
  -sr, --skip-renaming  Files will also be renamed (format: track_number track_name). Provide this flag to skip renaming files
```

![musictags2](https://github.com/badmagick329/musictags/assets/63713349/edbfc9f9-42a7-48a9-8d8c-b622243af56a)
