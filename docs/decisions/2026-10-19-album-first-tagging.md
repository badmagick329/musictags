# Tag a whole album from one Spotify album pick

- Date: 2026-10-19
- Status: Accepted

## Context

The per-file flow made the user confirm a track name, run a search and pick the same album once per file, and wrote tags the moment a track was picked. Shop downloads (Genie, QQ Music) already carry usable source tags, so most of that input was redundant. Built under YouTrack epic `MTG-4`.

## Decision

- **Album-first is the default.** `musictags <album folder>` reads every file's source tags, searches Spotify for albums, and needs one album pick and one `a`. `--per-track` keeps the per-file flow, which also serves `e N` then `/` in the preview.
- **Nothing is written before the preview is applied.** `q` and `--dry-run` leave files byte-identical; a rename clash (case-insensitive, Windows) blocks `a`.
- **Only a year the user gives (`-y`) filters the album search.** A year from the tags or folder name can be wrong and would hide the real album, so it only feeds the ranking.
- **In the album match, title similarity outweighs length, and a track number only supports a pair.** Language versions share a length to within 0.014 s (`MIDNIGHT SIGNAL - English Ver.` and `- Chinese Ver.`), and shops and deluxe editions renumber tracks. The weights and thresholds, with their reasons, are the constants in `domain/album_match.py` and `domain/ranking.py`.
- **Unsure rows are applied with sure ones; unmatched files are skipped.** The preview marks unsure rows `?` so the user can `e N` them before `a`.
- **Stray tags are removed on every write, in both flows.** The list (owner-confirmed) is the glossary's *Stray tags* row and `domain/tags.py`.
- **Filenames keep Spotify's trailing dot** (`01 MIDNIGHT SIGNAL - English Ver..flac`): owner's choice, so names stay a mechanical copy of Spotify's.

## Consequences

- Releases not on Spotify still need another route: tidy (`MTG-11`) or MusicBrainz (`MTG-3`).
- A file with no `TITLE` tag can be matched by length and track number but never as sure.
- Renames are ordered so none overwrites another file; a cycle goes through a temporary name.
