# Document index

These documents live under `docs/` and are tracked in Git: commit document changes with the work they describe, and keep credentials and unneeded personal data out of them. Read only what the task needs. Current user decisions, code, configuration and maintained public docs outrank these documents: when one disagrees with a document, correct the document; when two of them disagree with each other, ask the user.

## Project in one paragraph

musictags is the owner's personal command-line tool that fixes the tags on FLAC files so Last.fm scrobbles them correctly, using track data from the Spotify Web API. The user passes an album folder, plus an optional artist and release year (prompted for when missing). For each file the tool offers a suggestion for the track name, searches Spotify, and lists the matching tracks; the user selects one, starts a new search or skips the file. The selected track's tags are written to the file, which is then renamed to `NN Track name.flac` unless `--skip-renaming` is given. It runs locally from a Python virtual environment and is not deployed.

## Working rules for agents

- Run it from the repository root as `python src/musictags.py <album folder>`. Modules import their siblings by bare name, so `src/` must be the script's directory.
- Spotify credentials come from `CLIENT_ID` and `CLIENT_SECRET` in `.env` (see `.env.sample`).
- There is no test suite. Tagging and renaming change files in place, so try changes on a copy of an album folder.
- `SpotifyClient` reads the bearer token once, at construction, from spotipy's private `_auth_headers()`, then calls the search endpoint with `requests`. The token is never refreshed, so a run lasting over an hour fails its searches.

## Where to look

| Location | Purpose and retention |
| --- | --- |
| [context/glossary.md](context/glossary.md) | The project's ubiquitous language. Update when a concept is added or renamed. |
| YouTrack project `MTG` ("musictags") | Issues, bugs and feature requests, read and updated through the `youtrack` MCP tools; open work is `project: MTG #Unresolved`. |
| [decisions/2026-10-19-copy-spotify-naming.md](decisions/2026-10-19-copy-spotify-naming.md) | Why every tag copies Spotify's naming (scrobbles must merge with Spotify plays). Supersede when the scrobbling goal changes. |
| [plans/active/album-first-tagging.md](plans/active/album-first-tagging.md) | Album-first flow, preview, tidy and the vertical-slice restructure. Update as phases land; retire per *Where new documents go* when done. |
| [../README.md](../README.md) | Public setup and usage, including the CLI's arguments. Update when the arguments, setup or requirements change. |

## Language

[context/glossary.md](context/glossary.md) is the project's ubiquitous language. Name things with its terms in conversation, code, UI copy, docs and commits. A new concept gets its row in the same change that introduces it. When two names compete or a term stops fitting, ask the user, then rename everywhere or move the old name under *Avoid*.

## Where new documents go

Before writing, search the index and documents for the topic; extend the owning document when one exists. Load the `writing-for-agents` skill before creating or editing any document here.

- `context/`: current architecture, conventions, operations and gotchas. One home per topic; point to code and configuration rather than copying them.
- `decisions/YYYY-MM-DD-topic.md`: ADRs with status (`Proposed`, `Accepted`, `Superseded`), context, decision and consequences. They record rationale, not live state. Mark a superseded ADR and link its replacement.
- `plans/active/`: substantial unfinished work, with date, status, scope and acceptance criteria. On completion, move lasting rationale to `decisions/` and current guidance to `context/`, then delete the plan, or move it to `plans/completed/` while its evidence still matters.
- `research/` and `audits/`: dated findings with sources and status. An audit finding closes only on execution evidence.
- `artifacts/<task>/`: temporary outputs and helpers. Delete them once the task, and any deployment, is verified.

When this index names a YouTrack project, a bug, idea or backlog item the user decides to defer becomes an issue there, not a document. Raise findings, proposals and questions in chat as usual; open an issue only for work the user has chosen to defer.

Create a folder only when it receives a document. This index is the only file at the docs root.

## Keeping it current

A change is finished only when these documents describe it. Before reporting or committing:

1. **Find.** Search this collection for the names, paths, commands and terms the change touched. Documents you never opened go stale too. Done when every hit is updated or confirmed still true.
2. **Replace.** Rewrite changed guidance where it lives, following `writing-for-agents`, so each section reads as current truth on its own.
3. **One home.** Each fact lives in the document the index names for its topic; everywhere else links to it. Merge any copies the change created or exposed.
4. **Lifecycle.** Plans show actual progress, and finished plans leave `plans/active/`. Delete consumed handovers, status snapshots and verified artifacts once their unique facts have moved. Ask before deleting user-authored or uncertain material.
5. **Language.** Every concept the change introduced or renamed has its glossary row, and no avoided name came back.
6. **Index.** Rows and inbound links match every added, moved or deleted path.
7. **Issues.** When this index names a YouTrack project, every issue the change resolved or advanced gets a comment saying what changed and in which commit; resolve an issue once its change is verified.
