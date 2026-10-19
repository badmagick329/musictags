from typing import Literal

Color = Literal[
    "BLACK", "RED", "GREEN", "YELLOW", "BLUE", "MAGENTA", "CYAN", "WHITE", "RESET"
]

ANSI_CODES: dict[Color, str] = {
    "BLACK": "\033[30m",
    "RED": "\033[31m",
    "GREEN": "\033[32m",
    "YELLOW": "\033[33m",
    "BLUE": "\033[34m",
    "MAGENTA": "\033[35m",
    "CYAN": "\033[36m",
    "WHITE": "\033[37m",
    "RESET": "\033[0m",
}


def colorize(color: Color, text: str) -> str:
    return f"{ANSI_CODES[color]}{text}{ANSI_CODES['RESET']}"
