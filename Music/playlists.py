
import json
import logging
import re
from pathlib import Path

logger = logging.getLogger("music.playlists")

BASE_DIR = Path(__file__).resolve().parent.parent
PLAYLIST_DIR = BASE_DIR / "data" / "playlists"
PLAYLIST_DIR.mkdir(parents=True, exist_ok=True)

YOUTUBE_PREFIXES = (
    "https://www.youtube.com/",
    "https://youtube.com/",
    "https://m.youtube.com/",
    "https://music.youtube.com/",
    "https://youtu.be/",
)


def validate_name(name: str):
    name = name.strip().lower()

    if not re.fullmatch(r"[a-z0-9_-]{1,40}", name):
        raise ValueError(
            "Names must be 1-40 characters: letters, numbers, _ or -."
        )

    return name


class PlaylistManager:
    def path_for(self, owner_id: int, name: str):
        name = validate_name(name)
        return PLAYLIST_DIR / f"{owner_id}_{name}.json"

    def save(self, owner_id: int, name: str, songs: list):
        name = validate_name(name)
        path = self.path_for(owner_id, name)

        entries = []
        for song in songs:
            url = song.get("url") or song.get("webpage_url")
            if not url or not url.startswith(YOUTUBE_PREFIXES):
                continue

            entries.append({
                "title": song.get("title", "Unknown title"),
                "url": url,
            })

        if not entries:
            raise ValueError("There are no valid songs to save.")

        data = {
            "owner_id": owner_id,
            "name": name,
            "songs": entries,
        }

        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info(
            "User %s saved playlist '%s' (%s songs)",
            owner_id,
            name,
            len(entries),
        )
        return path

    def load(self, owner_id: int, name: str):
        path = self.path_for(owner_id, name)

        if not path.exists():
            return None

        data = json.loads(path.read_text(encoding="utf-8"))

        if data.get("owner_id") != owner_id:
            raise PermissionError("You do not own this playlist.")

        return data

    def list_names(self, owner_id: int):
        prefix = f"{owner_id}_"
        return sorted(
            path.stem[len(prefix):]
            for path in PLAYLIST_DIR.glob(f"{prefix}*.json")
        )

    def export(self, owner_id: int, name: str):
        path = self.path_for(owner_id, name)

        if not path.exists():
            raise FileNotFoundError(name)

        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("owner_id") != owner_id:
            raise PermissionError("You do not own this playlist.")

        return path

    def import_data(self, owner_id: int, content: bytes):
        if len(content) > 1_000_000:
            raise ValueError("Playlist file must be under 1 MB.")

        data = json.loads(content.decode("utf-8"))
        name = validate_name(data.get("name", ""))
        songs = data.get("songs")

        if not isinstance(songs, list) or not 1 <= len(songs) <= 500:
            raise ValueError("Playlist must contain 1-500 songs.")

        clean_songs = []

        for song in songs:
            if not isinstance(song, dict):
                raise ValueError("Invalid song entry.")

            url = song.get("url")
            if not isinstance(url, str) or not url.startswith(
                YOUTUBE_PREFIXES
            ):
                raise ValueError("Invalid YouTube URL in playlist.")

            clean_songs.append({
                "title": str(song.get("title", "Unknown title"))[:200],
                "url": url,
            })

        return self.save(owner_id, name, clean_songs)
