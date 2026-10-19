import re

_ID = r"([0-9A-Za-z]{22})"
_FORMS = (
    re.compile(rf"{_ID}"),
    re.compile(rf"spotify:album:{_ID}"),
    # Spotify's API rejects localised links (open.spotify.com/intl-ja/album/...),
    # so the ID is pulled out here rather than the link passed through.
    re.compile(
        rf"(?:https?://)?open\.spotify\.com/(?:intl-[A-Za-z-]+/)?album/{_ID}/?(?:[?#].*)?"
    ),
)


def parse_album_id(text: str) -> str:
    """The Spotify album ID in a pasted album link, URI or bare ID.

    Raises ValueError, with a message fit to show the user, for anything else.
    """
    stripped = text.strip()
    for form in _FORMS:
        match = form.fullmatch(stripped)
        if match:
            return match.group(1)
    raise ValueError(f"Not a Spotify album link, URI or ID: {text!r}")
