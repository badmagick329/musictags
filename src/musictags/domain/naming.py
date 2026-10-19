import re

# Strips a leading track number and separator: "01. Title", "01 - Title".
SUGGESTION_REGEX = re.compile(r"\d*\.?(?: -)?\s?(.+)")

# Characters Windows forbids in file names.
_UNSAFE_CHARS = '<>:"/\\|?*'


def suggest_track_name(stem: str) -> str:
    match = SUGGESTION_REGEX.match(stem)
    return match.group(1) if match else stem


def clean_name(name: str) -> str:
    for char in _UNSAFE_CHARS:
        name = name.replace(char, "_")
    return name


def track_filename(track_number: int, name: str, suffix: str) -> str:
    return f"{track_number:02} {clean_name(name)}{suffix}"
