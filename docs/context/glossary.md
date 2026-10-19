# Glossary

The project's ubiquitous language, one row per concept; the index's *Language* section says how to use it. Sorted by term.

| Term | Meaning | Avoid | In code |
| --- | --- | --- | --- |
| Album match | Pairing every file in the album folder with a track of one chosen Spotify album, by track number, title similarity and length; each pair is sure or unsure. Planned. | auto-match | |
| Album folder | The folder given on the command line; only `.flac` files directly inside it are processed. | directory | `album_folder`, `folder` |
| Artist | The performer searched for, entered once per run and used for every file. The tags take the selected track's first Spotify artist instead. | | `artist`; `Artist` is a Spotify artist |
| File | One FLAC file in the album folder, tagged and renamed in place. | track | `file`, `FlacMetadata` |
| New search | Searching Spotify again for the same file with a different track name: `n` at the result prompt, or Enter after an empty result. | retry | `SelectionResultType.SEARCH` |
| Preview | The table of old → new tags and filenames shown before anything is written; nothing changes until the user applies it. Planned. | dry run (that is the flag that shows it and exits) | |
| Release date | The album's release date from Spotify, padded to a full date when Spotify gives only a year or month. Written as the `DATE` tag, and results sharing the previously selected track's release date are listed first. | | `Album.release_date`, `date_from_previous_choice` |
| Release year | Optional filter limiting the Spotify search to one year, from `-y` or the prompt. | year filter | `year` |
| Renaming | Renaming a tagged file to `NN Track name.flac`, with characters illegal in Windows filenames replaced by `_`. `--skip-renaming` turns it off. | | `clean_name`, `skip_renaming` |
| Skip | Leaving a file untagged and unrenamed: `s` at any per-file prompt. | | `SelectionResultType.SKIP` |
| Source tags | The tags a file carries before musictags touches it, usually written by the shop it came from (Genie, QQ Music). | existing tags, original tags | |
| Stray tags | Source tags musictags removes because they are shop residue: store comments, URLs, placeholder copyright, duplicate track fields such as `TRCK`. Planned. | junk tags | |
| Suggestion | The track name derived from the filename by stripping a leading track number and separator; used when the prompt gets `u` or is left blank. | suggested name | `NAME_REGEX`, `suggestion` |
| Tags | The Vorbis comments written to a file: `ALBUM`, `ARTIST`, `ARTISTS`, `DATE`, `TITLE`, `TRACKNUMBER`, `TRACKTOTAL`. An empty value leaves the existing tag. | metadata | `Track.as_tags`, `FlacMetadata.set_tags` |
| Tidy | Tagging a release not on Spotify by normalising its source tags (date format, Spotify's artist spelling, stray tags removed) instead of replacing them. Planned. | | |
| Track | A Spotify search result; the one the user selects for a file supplies its tags and new name. | song, match | `Track` |
| Track name | The text searched for a file: typed, or the suggestion. | title (that is the `TITLE` tag) | `name`, `track_name` |
