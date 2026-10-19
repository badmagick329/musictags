# Copy Spotify's naming in every tag

- Date: 2026-10-19
- Status: Accepted

## Context

The owner listens both on Spotify and on local FLAC files, and both are scrobbled to Last.fm. Last.fm keys a scrobble on the artist, track and album names it receives, so a local play tagged `NOVA & ORBIT` lands on a different Last.fm entry from the same song played on Spotify as `NOVA`. Shop downloads (Genie, QQ Music) carry their own spellings, artist joins (`&`, `/`) and date formats.

## Decision

Tags written by musictags reproduce Spotify's naming exactly: the track title, the album name and the first artist as Spotify lists them. `ARTIST` and `ARTISTS` hold only that first artist, because a Spotify scrobble sends only the first artist. `ALBUMARTIST` gets the album's first artist on the same reasoning (unverified against what Spotify sends). When a release is not on Spotify, artist names still come from Spotify where the artist exists there.

## Consequences

- Featured and secondary artists are dropped from the tags, even when the source tags list them correctly.
- Any new tag source (tidying source tags, MusicBrainz) maps its names onto Spotify's before writing, rather than keeping its own.
- Spotify's naming wins over a more accurate source; a release Spotify names oddly is tagged oddly.
