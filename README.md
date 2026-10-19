# musictags

## Description

Fixes tags on flac audio files for scrobbling on last.fm. Uses track information from spotify

![musictags4](https://github.com/badmagick329/musictags/assets/63713349/a975d6b2-bb6f-47e9-a807-cd74e26f4b5f)

## Usage

### Setup

You need a Client ID and Client Secret from a Spotify app. Copy [.env.sample](.env.sample) to `.env` and fill in `CLIENT_ID` and `CLIENT_SECRET`.

Install into a virtual environment:

```
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

### Tagging an album

```
python -m musictags <album folder>
```

musictags reads the existing tags to work out the artist, album and year (falling back to a folder name like `250314 MIDNIGHT SIGNAL`), searches Spotify for the album and lists the best matches. If the files carry no artist or album, it asks for them. At the album list you can:

- type a number to pick that album
- paste a Spotify album link, URI or ID
- type `n` to edit the artist and album and search again
- type `q` to quit

It then matches each file to a track on the album and shows a preview: the album tags that will change, each file with its matched track and new name, and the stray tags it will remove (Genie leftovers such as `COMMENT`, `WWW`, `TRCK`, `ALBUMTITLE`, `YEAR`, the placeholder `COPYRIGHT`, and blank tags). `✓` marks a confident match, `?` a guess worth checking. Nothing is written until you apply.

- `a` writes the tags and renames the files to `NN Track name.flac`
- `e N` edits row N: type the album track number to use, `s` to skip the file, `/` to search Spotify for that one file, or Enter to keep the row
- `p` goes back to the album list
- `q` quits without writing

If two files would end up with the same name, `a` refuses until you fix the rows. Use `--dry-run` to print the preview and exit, or `--album LINK` to skip the search when you already know the album.

### Tagging file by file

```
python -m musictags --per-track -a "NOVA" <album folder>
```

This searches Spotify for each file in turn. For every file it suggests a track name from the filename; press Enter or `u` to search with it, type a different name, or `s` to skip. Pick a result by number, `n` to search with another name, or `s` to skip. Each file is tagged and renamed as soon as you pick. Without `-a` or `-y` it asks for the artist and release year first. `--album` and `--dry-run` don't work in this mode.

### Options

```
usage: musictags [-h] [-a ARTIST] [-y YEAR] [-sr] [--per-track] [--album LINK]
                 [--dry-run]
                 album_folder

Tag your flac files with Spotify metadata

positional arguments:
  album_folder          Folder to search for flac files

options:
  -h, --help            show this help message and exit
  -a ARTIST, --artist ARTIST
                        Artist name
  -y YEAR, --year YEAR  Album release year
  -sr, --skip-renaming  Files will also be renamed (format: track_number
                        track_name). Provide this flag to skip renaming files
  --per-track           Search and pick a Spotify track for each file in turn
                        instead of picking one album
  --album LINK          Spotify album URL, URI or ID to tag from, skipping the
                        album search
  --dry-run             Print the preview and exit without writing anything
```
