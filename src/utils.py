def clean_name(name) -> str:
    chars = [
        "<",
        ">",
        ":",
        '"',
        "/",
        "\\",
        "|",
        "?",
        "*",
    ]
    for char in chars:
        name = name.replace(char, "_")
    return name
