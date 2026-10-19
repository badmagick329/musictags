# Album-first tagging

- Date: 2026-10-19
- Status: In progress. *Layout* is done. The target flow is tracked as YouTrack epic `MTG-4` and its subtasks; tidy is not started and is outside the epic.

## Problem

Tagging works one file at a time: for a 14-track album the user confirms 14 track names, runs 14 searches and picks the same album from 14 result lists, and tags are written the moment a track is picked. Shop downloads already carry usable source tags (track number, title, album, artist, track total), so most of that input is redundant.

## Target flow

1. Read the source tags of every file in the album folder: album, artist, year, track count, and per file its track number, title and length. The folder name (`YYMMDD Album name`, the owner's convention) is the fallback for album and year. Command-line `-a`/`-y` override them; the tool prompts only for what is still missing.
2. Search Spotify for albums and rank candidates by artist, album name, track count and year. The user picks one by number, pastes a Spotify album URL or ID, or edits the artist and album and searches again.
3. Album match: pair each file with a track of the chosen album by title similarity, length, and track and disc number. Length alone cannot separate language versions (`MIDNIGHT SIGNAL (English Ver.)` and `(Chinese Ver.)` are both 173.4 s), so title similarity breaks ties. Each file is sure, unsure or unmatched.
4. Preview: album-level tags (old → new) once, then one row per file: old → new filename, the Spotify title, and its sure/unsure/unmatched mark; stray tags to be removed are listed. Unmatched files are skipped unless edited.
5. Apply: write the tags, remove stray tags, rename. Nothing touches a file before this step.

Every name written follows [the Spotify-naming decision](../../decisions/2026-10-19-copy-spotify-naming.md), in both the album-first and per-file flows.

## CLI

- `musictags <album folder>` runs the album-first flow; `--per-track` runs the per-file flow as it is today.
- `--album <Spotify album URL or ID>` skips the album search.
- `--dry-run` prints the preview and exits without writing.
- `-a/--artist`, `-y/--year` and `-sr/--skip-renaming` keep their meaning in both flows.

Preview commands: `a` applies; `e N` edits row N (assign another track of the album by its number, `s` to skip the file, or `/` for the per-file search); `p` returns to the album list; `q` quits without writing.

## Tidy (lowest priority)

For releases not on Spotify: keep the source tags but normalise them: dates to `YYYY-MM-DD`, artist names to Spotify's spelling of the first artist where Spotify has the artist, stray tags removed, file renamed. A MusicBrainz source is deferred to YouTrack `MTG-3`.

## Layout

Done 2026-10-19: the code is in vertical slices (see the index's working rules), the per-file flow is the `tag_tracks` slice, and Spotify search goes through spotipy, which refreshes its token. The album-first flow becomes a `tag_album` slice reusing `tag_tracks` for edited rows, tidy becomes `tidy_tags`, and ranking and match scoring go in `domain/`.

## Acceptance criteria

- On a copy of `D:\Music\Nova\250314 MIDNIGHT SIGNAL`, the flow needs one album pick and one `a` when Spotify has the release, and every file is matched to its own language version.
- No file is modified before the user applies the preview; `q` and `--dry-run` leave files byte-identical.
- Tests cover ranking and match scoring against recorded Spotify responses, including same-length language versions and a file missing from the Spotify release.
- `MTG-2` (README usage) is done once the CLI settles.
