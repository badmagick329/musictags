# Album-first tagging

- Date: 2026-10-19
- Status: Proposed; the restructure in *Layout* awaits the owner's approval.

## Problem

Tagging works one file at a time: for a 14-track album the user confirms 14 track names, runs 14 searches and picks the same album from 14 result lists, and tags are written the moment a track is picked. Shop downloads already carry usable source tags (track number, title, album, artist, track total), so most of that input is redundant.

## Target flow

1. Read the source tags of every file in the album folder: album, artist, year, track count, and per file its track number, title and length. Command-line `-a`/`-y` override them; the tool prompts only for what is missing.
2. Search Spotify for albums and rank candidates by track count, total length and name similarity. The user picks one, or pastes a Spotify album URL instead.
3. Album match: pair each file with a track of the chosen album by track number, title similarity and length. Length alone cannot separate language versions (`MIDNIGHT SIGNAL (English Ver.)` and `(Chinese Ver.)` are both 173.4 s), so title similarity breaks ties. Each pair is marked sure or unsure.
4. Preview: one table of old → new tags and old → new filename per file. The user applies, edits a row (falling back to today's per-track search for that file), picks another album, or chooses tidy.
5. Apply: write the tags, remove stray tags, rename. Nothing touches a file before this step.

Every name written follows [the Spotify-naming decision](../../decisions/2026-10-19-copy-spotify-naming.md).

## Tidy (lowest priority)

For releases not on Spotify: keep the source tags but normalise them: dates to `YYYY-MM-DD`, artist names to Spotify's spelling of the first artist where Spotify has the artist, stray tags removed, file renamed. A MusicBrainz source is deferred to YouTrack `MTG-3`.

## Layout

The project now crosses the threshold for vertical slices (several features plus Spotify, filesystem and CLI I/O). Proposed, pending approval:

```text
src/musictags/
  domain/            # Track, Album, Artist, tag mapping, match scoring: pure, no I/O
  features/
    tag_album/       # album-first flow use case
    tidy_tags/       # source-tag normalisation use case
  infrastructure/    # Spotify client, FLAC read/write, file renaming
  presentation/      # CLI prompts and the preview table
tests/
```

Spotify calls move to spotipy's own methods (`search`, `album_tracks`), which refresh the token, replacing the hand-built `requests` call and its one-hour limit.

## Acceptance criteria

- On `D:\Music\Nova\250314 MIDNIGHT SIGNAL` (on a copy), the flow needs one album pick and one confirmation when Spotify has the release, and every file is matched to its own language version.
- No file is modified before the user applies the preview.
- Tests cover match scoring against a recorded Spotify album response, including same-length language versions and a file missing from the Spotify release.
- `MTG-1` (inconsistent quotes) is resolved by the new result display; `MTG-2` (README usage) is done once the CLI settles.
