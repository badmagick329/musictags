from urllib.parse import quote

import requests
import spotipy
from spotipy import SpotifyClientCredentials
from typing import Optional

from track import Track


class SpotifyClient:
    def __init__(self, client_id, client_secret):
        self.client = spotipy.Spotify(
            client_credentials_manager=SpotifyClientCredentials(
                client_id=client_id, client_secret=client_secret
            )
        )
        self.bearer = self.client._auth_headers()["Authorization"]

    def search_tracks(
        self, artist: str, track: str, year: Optional[int] = None
    ) -> list[Track]:
        headers = {"Authorization": self.bearer}
        query = f"year:{year} " if year else ""
        query += f"artist:{artist} track:{track}"
        quoted = quote(query)
        url = f"https://api.spotify.com/v1/search?q={quoted}&type=track"
        response = requests.get(url, headers=headers)
        results = response.json()
        tracks = [Track(item) for item in results["tracks"]["items"]]
        return tracks


if __name__ == "__main__":
    import os

    from dotenv import load_dotenv

    load_dotenv()
    CLIENT_ID = os.getenv("CLIENT_ID")
    CLIENT_SECRET = os.getenv("CLIENT_SECRET")
    client = SpotifyClient(CLIENT_ID, CLIENT_SECRET)
    artist_ = input("Artist: ")
    track_ = input("Track: ")
    tracks_ = client.search_tracks(artist_, track_)
    for t in tracks_:
        print(t)
