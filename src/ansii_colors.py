from typing import Literal

ColorType = Literal[
    "BLACK", "RED", "GREEN", "YELLOW", "BLUE", "MAGENTA", "CYAN", "WHITE", "RESET"
]


class AnsiiColors:
    colors: dict[ColorType, str] = {
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

    @classmethod
    def colorize(cls, color: ColorType, text: str) -> str:
        return f"{cls.colors[color]}{text}{cls.colors['RESET']}"
