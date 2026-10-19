import pytest

from musictags.domain.album_link import parse_album_id

ID = "2Kbn6hMdh6bD50FmLB0eHb"


@pytest.mark.parametrize(
    "text",
    [
        ID,
        f"  {ID}\n",
        f"spotify:album:{ID}",
        f"https://open.spotify.com/album/{ID}",
        f"https://open.spotify.com/album/{ID}?si=Xr4b2aQ9TzK1",
        f"https://open.spotify.com/intl-ja/album/{ID}",
        f"https://open.spotify.com/intl-pt-BR/album/{ID}?si=abc&utm_source=copy-link",
        f"open.spotify.com/album/{ID}/",
    ],
)
def test_accepts_album_links_uris_and_ids(text):
    assert parse_album_id(text) == ID


@pytest.mark.parametrize(
    "text",
    [
        "",
        "MIDNIGHT SIGNAL",
        ID[:-1],
        ID + "x",
        f"{ID}!",
        f"spotify:track:{ID}",
        f"spotify:album:{ID[:-1]}",
        f"https://open.spotify.com/track/{ID}",
        f"https://open.spotify.com/artist/{ID}",
        f"https://example.com/album/{ID}",
        f"https://open.spotify.com.evil.com/album/{ID}",
        f"https://open.spotify.com/album/{ID}extra",
    ],
)
def test_rejects_anything_else(text):
    with pytest.raises(ValueError, match="Not a Spotify album link, URI or ID"):
        parse_album_id(text)
