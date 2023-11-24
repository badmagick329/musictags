from urllib.parse import quote

import requests
import spotipy
from spotipy import SpotifyClientCredentials

from track import Track


class SpotifyClient:
    def __init__(self, client_id, client_secret):
        self.client = spotipy.Spotify(
            client_credentials_manager=SpotifyClientCredentials(
                client_id=client_id, client_secret=client_secret
            )
        )
        self.bearer = self.client._auth_headers()["Authorization"]

    def search_tracks(self, artist: str, track: str) -> list[Track]:
        headers = {"Authorization": self.bearer}
        query = quote(f"artist:{artist} track:{track}")
        url = f"https://api.spotify.com/v1/search?q={query}&type=track"
        response = requests.get(url, headers=headers)
        results = response.json()
        tracks = [Track(item) for item in results["tracks"]["items"]]
        return tracks

    # Note: Spotipy search sucks
    def __search_tracks(
        self, artist: str, track: str, album: str = "", max: int = 15
    ) -> list[Track]:
        query_str = f"{track}"
        if album:
            query_str += f" album:{album}"
        if artist:
            query_str += f" artist:{artist}"
        query = quote(query_str)
        results = self.client.search(q=query, type="track", limit=max)
        tracks = [Track(item) for item in results["tracks"]["items"]]
        tracks = self.filter_tracks(tracks, artist)
        prev_len = len(tracks)
        while len(tracks) < max and results["tracks"].get("next", None):
            results = self.client.next(results["tracks"])
            tracks.extend([Track(item) for item in results["tracks"]["items"]])
            tracks = self.filter_tracks(tracks, artist)
            if len(tracks) == prev_len:
                break
            prev_len = len(tracks)
        return tracks

    @staticmethod
    def __filter_tracks(tracks: list[Track], artist: str) -> list[Track]:
        return [
            t
            for t in tracks
            if t.artists[0].name.lower() == artist.strip().lower()
        ]


if __name__ == "__main__":
    import os

    from dotenv import load_dotenv

    load_dotenv()
    CLIENT_ID = os.getenv("CLIENT_ID")
    CLIENT_SECRET = os.getenv("CLIENT_SECRET")
    client = SpotifyClient(CLIENT_ID, CLIENT_SECRET)
    artist = input("Artist: ")
    album = input("Album: ")
    track = input("Track: ")
    tracks = client.search_tracks(artist, album, track, 15)
    for t in tracks:
        print(t)
