# Glossary

The project's ubiquitous language, one row per concept; the index's *Language* section says how to use it. Sorted by term.

| Term | Meaning | Avoid | In code |
| --- | --- | --- | --- |
| Album | A Spotify release an album folder is tagged from. Its artists are kept apart from each track's, because the two lists can differ in order. | release (except in *release date* and *release hints*) | `Album`, `Album.artists`, `SpotifyCatalog.search_albums`, `SpotifyCatalog.album_tracks` |
| Album link | A Spotify album URL (localised `intl-xx/` ones included), `spotify:album:` URI or bare ID, pasted by the user or given to `--album`. | | `parse_album_id` |
| Album match | Pairing every file in the album folder with a track of one chosen Spotify album, by track number, title similarity and length; each pair is sure or unsure. Planned. | auto-match | |
| Album folder | The folder given on the command line; only `.flac` files directly inside it are processed. | directory | `album_folder`, `folder` |
| Artist | The performer searched for, entered once per run and used for every file. The tags take the selected track's first Spotify artist instead. | | `artist`; `Artist` is a Spotify artist, `Track.main_artist` the first |
| File | One FLAC file in the album folder, tagged and renamed in place. | track | `file`, `FlacTagWriter` |
| New search | Searching Spotify again for the same file with a different track name: `n` at the result prompt, or Enter after an empty result. | retry | `Choice.SEARCH_AGAIN` |
| Preview | The table of old → new tags and filenames shown before anything is written; nothing changes until the user applies it. Planned. | dry run (that is the flag that shows it and exits) | |
| Release date | The album's release date from Spotify, padded to a full date when Spotify gives only a year or month. Written as the `DATE` tag, and results sharing the previously selected track's release date are listed first. | | `Album.release_date`, `TagTracks._previous_release_date` |
| Release hints | Album, first album artist, year and track count derived from the source tags, falling back to the folder name `YYMMDD Album name`; they drive the album search and the prompt defaults. | | `ReleaseHints`, `derive_release_hints` |
| Release year | Optional filter limiting the Spotify search to one year, from `-y` or the prompt. | year filter | `year` |
| Renaming | Renaming a tagged file to `NN Track name.flac`, with characters illegal in Windows filenames replaced by `_`. `--skip-renaming` turns it off. | | `track_filename`, `clean_name` |
| Skip | Leaving a file untagged and unrenamed: `s` at any per-file prompt. | | `Choice.SKIP` |
| Source file | One file's source tags and length, read once before anything is written. `TRCK` is ignored: shops fill it with wrong values. | | `SourceFile`, `read_source_files` |
| Source tags | The tags a file carries before musictags touches it, usually written by the shop it came from (Genie, QQ Music). | existing tags, original tags | `SourceFile.tags` |
| Stray tags | Source tags removed whenever a file is tagged, because they are shop residue: `COMMENT`, `WWW`, `TRCK`, `ALBUMTITLE`, `YEAR`, any tag whose values are all blank, and placeholders such as Genie's `COPYRIGHT` `해당곡의 저작권자`. A tag being written is overwritten, never removed. | junk tags | `stray_tags`, `ALWAYS_STRAY_KEYS`, `PLACEHOLDER_VALUES` |
| Suggestion | The track name derived from the filename by stripping a leading track number and separator; used when the prompt gets `u` or is left blank. | suggested name | `suggest_track_name` |
| Tags | The Vorbis comments written to a file: `ALBUM`, `ALBUMARTIST` (the album's first artist), `ARTIST`, `ARTISTS`, `DATE`, `TITLE`, `TRACKNUMBER`, `TRACKTOTAL`. An empty value leaves the existing tag; the same save removes stray tags. | metadata | `track_tags`, `FlacTagWriter.write_tags` |
| Tidy | Tagging a release not on Spotify by normalising its source tags (date format, Spotify's artist spelling, stray tags removed) instead of replacing them. Planned. | | |
| Track | A Spotify track, from a track search or an album's track list; the one chosen for a file supplies its tags and new name. Its length is in seconds, comparable with a file's. | song, match | `Track`, `Track.length` |
| Track name | The text searched for a file: typed, or the suggestion. | title (that is the `TITLE` tag) | `name` |
