
import logging
import logging.handlers
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "bot.log"

LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | "
    "%(name)s | %(message)s"
)
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        handlers=[
            logging.StreamHandler(),
            logging.handlers.RotatingFileHandler(
                LOG_FILE,
                maxBytes=2 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            ),
        ],
        force=True,
    )

    # Detailed logs for music playback and YouTube extraction.
    logging.getLogger("music.player").setLevel(logging.DEBUG)
    logging.getLogger("music.cog").setLevel(logging.DEBUG)
    logging.getLogger("music.playlists").setLevel(logging.DEBUG)
    logging.getLogger("yt_dlp").setLevel(logging.DEBUG)

    # Voice connection diagnostics.
    logging.getLogger("discord.voice_state").setLevel(logging.DEBUG)
    logging.getLogger("discord.gateway").setLevel(logging.INFO)

    # Avoid excessive HTTP request noise.
    logging.getLogger("discord.http").setLevel(logging.WARNING)

    logging.getLogger("bot").info(
        "Logging initialized. Console and file: %s",
        LOG_FILE,
    )
