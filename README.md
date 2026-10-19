# musictags

Rewrites the tags on FLAC files with Spotify's names, so Last.fm scrobbles from local plays land on the same tracks, albums and artists as your Spotify plays.

![musictags4](https://github.com/badmagick329/musictags/assets/63713349/a975d6b2-bb6f-47e9-a807-cd74e26f4b5f)

## How it works

```
uv run musictags "path\to\250101 Album Name"
```

1. It reads the tags already on the files and the folder name (`YYMMDD Album name`) to work out the artist, album and year. It asks only for what it can't find.
2. It searches Spotify and lists matching albums. Type a number to pick one, paste a Spotify album link, `n` to change the search, or `q` to quit.
3. It pairs every file with a track on that album and shows a preview. Nothing has been written yet.
4. Press `a` and it writes the tags, removes shop leftovers and renames the files to `NN Track name.flac`.

The preview looks like this:

```
Album: Artist - Album Name (2025-01-01) [album] 10 tracks

Album tags:
  ALBUMARTIST: Artist & Guest → Artist
  DATE: 2025.01.01 → 2025-01-01

Files:
  1 ✓    01. Song One.flac → 01 Song One.flac
         #1 Song One
  2 ?    02. Song Two (Remix).flac → 02 Song Two - Remix.flac
         #2 Song Two - Remix
  ...

Stray tags to remove: YEAR ×10, TRCK ×10, COMMENT ×10, WWW ×10
```

`✓` is a confident match, `?` is a guess worth checking, and `skip` rows are left alone. At the preview prompt:

| Key | What it does |
| --- | --- |
| `a` | Apply. Refused while two files would get the same name. |
| `e N` | Change row N: an album track number, `s` to skip the file, or `/` to search Spotify for that file alone. |
| `p` | Back to the album list. |
| `q` | Quit without writing anything. |

## What gets written

| Tag | Value |
| --- | --- |
| `TITLE`, `ALBUM` | Spotify's names, exactly |
| `ARTIST`, `ARTISTS` | The track's first Spotify artist, since Spotify scrobbles send only that one |
| `ALBUMARTIST` | The album's first Spotify artist |
| `DATE` | Release date as `YYYY-MM-DD` |
| `TRACKNUMBER`, `TRACKTOTAL` | From the Spotify album |

It also removes `COMMENT`, `WWW`, `TRCK`, `ALBUMTITLE`, `YEAR`, empty tags and Genie's placeholder `COPYRIGHT`. Other tags, such as `GENRE`, `LABEL` and lyrics, stay.

## Options

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

`--per-track` is the older flow for albums that don't match well: you search Spotify one file at a time, and each file is tagged as soon as you pick its track.

## Setup

1. Create an app in the [Spotify developer dashboard](https://developer.spotify.com/dashboard) to get a Client ID and Client Secret.
2. Copy [.env.sample](.env.sample) to `.env` and fill in `CLIENT_ID` and `CLIENT_SECRET`.
3. Run `uv run musictags --help`. uv installs everything on the first run.

Files are changed in place, so try `--dry-run` or a copy of the folder first.
