import datetime
from datetime import datetime as dt
from typing import Optional

from ansii_colors import AnsiiColors


class Artist:
    data_dict: dict
    name: str
    type_: str
    uri: str
    external_url: str

    def __init__(self, data):
        self.data_dict = data
        self.name = data.get("name", "")
        self.type_ = data.get("type", "")
        self.uri = data.get("uri", "")
        try:
            self.external_url = data["external_urls"]["spotify"]
        except KeyError:
            self.external_url = ""

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return (
            f"Artist(name={self.name}, type_={self.type_}, uri={self.uri}, "
            f"external_url={self.external_url})"
        )


class Album:
    data_dict: dict
    name: str
    album_type: str
    type_: str
    release_date_str: str
    release_date_precision: str
    release_date: Optional[datetime.date]
    total_tracks: int
    external_url: str

    def __init__(self, data):
        self.data_dict = data
        self.name = data.get("name", "")
        self.album_type = data.get("album_type", "")
        self.type_ = data.get("type", "")
        self.release_date_str = data.get("release_date", "")
        self.release_date_precision = data.get("release_date_precision", "")
        date_str = self.release_date_str
        if self.release_date_precision == "month":
            date_str += "-01"
        elif self.release_date_precision == "year":
            date_str += "-01-01"
        try:
            self.release_date = dt.strptime(date_str, "%Y-%m-%d").date()
        except Exception:
            self.release_date = None
        self.total_tracks = int(data.get("total_tracks", 0))
        try:
            self.external_url = data["external_urls"]["spotify"]
        except KeyError:
            self.external_url = ""

    def __str__(self) -> str:
        return f'"{self.name}" ("{self.release_date}") [{self.album_type}]'

    def colored_string(self) -> str:
        name = AnsiiColors.colorize("GREEN", self.name)
        date = AnsiiColors.colorize("RED", f'"{self.release_date}"')
        return f"{name} ({date}) [{self.album_type}]"

    def __repr__(self) -> str:
        return (
            f"Album(name={self.name}, album_type={self.album_type}, "
            f"type_={self.type_}, release_date_str={self.release_date_str}, "
            f"release_date_precision={self.release_date_precision}, "
            f"release_date={self.release_date}, total_tracks={self.total_tracks}, "
            f"external_url={self.external_url})"
        )


class Track:
    data_dict: dict
    album: Album
    artists: list[Artist]
    track_id: str
    name: str
    track_number: int
    external_url: str
    popularity: int
    preview_url: str
    type_: str
    uri: str

    def __init__(self, data):
        self.data_dict = data
        self.album = Album(data["album"])
        self.artists = [Artist(a) for a in data["artists"]]
        self.track_id = data.get("id", "")
        self.name = data.get("name", "")
        self.track_number = int(data.get("track_number", 0))
        try:
            self.external_url = data["external_urls"]["spotify"]
        except KeyError:
            self.external_url = ""
        self.popularity = int(data.get("popularity", 0))
        self.preview_url = data.get("preview_url", "")
        self.type_ = data.get("type", "")
        self.uri = data.get("uri", "")

    def as_tags(self) -> dict[str, str]:
        date_value = (
            self.album.release_date.strftime("%Y-%m-%d")
            if self.album.release_date
            else ""
        )
        return {
            "ALBUM": self.album.name,
            "ARTIST": self.artists[0].name,
            "ARTISTS": self.artists[0].name,
            "DATE": date_value,
            "TITLE": self.name,
            "TRACKNUMBER": str(self.data_dict.get("track_number", 0)),
            "TRACKTOTAL": str(self.album.total_tracks),
        }

    def __str__(self) -> str:
        return f"{self.artists[0]} - {self.name} - {self.album} #{self.track_number}"

    def colored_string(self) -> str:
        artist = AnsiiColors.colorize("YELLOW", str(self.artists[0]))
        name = AnsiiColors.colorize("BLUE", self.name)
        return f"{artist} - {name} - {self.album.colored_string()} #{self.track_number}"

    def __repr__(self) -> str:
        return (
            f"Track(album={self.album}, artists={self.artists}, "
            f"track_id={self.track_id}, name={self.name}, "
            f"track_number={self.track_number}, "
            f"external_url={self.external_url}, popularity={self.popularity}, "
            f"preview_url={self.preview_url}, type_={self.type_}, uri={self.uri})"
        )
