
import asyncio
import logging
import shutil
from collections import deque

import discord
from yt_dlp import YoutubeDL

logger = logging.getLogger("music.player")
yt_logger = logging.getLogger("yt_dlp")

YDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": False,
    "no_warnings": False,
    "js_runtimes": {"deno": {}},
    "logger": yt_logger,
    "extractor_retries": 2,
}


def search_youtube(query: str):
    """Search YouTube or resolve a URL. Called from a worker thread."""
    logger.info("Starting YouTube search/resolution: %s", query)

    try:
        with YoutubeDL(YDL_OPTIONS) as ydl:
            if query.startswith(("https://", "http://")):
                info = ydl.extract_info(query, download=False)
            else:
                info = ydl.extract_info(
                    f"ytsearch1:{query}",
                    download=False,
                )
                entries = (info or {}).get("entries") or []
                info = entries[0] if entries else None

            if not info:
                logger.warning("YouTube returned no result for: %s", query)
                return None

            result = {
                "title": info.get("title", "Unknown title"),
                "url": info.get("webpage_url") or query,
                "source": info.get("url"),
            }

            logger.info(
                "YouTube result resolved: title=%s format=%s stream_url=%s",
                result["title"],
                info.get("format", "unknown"),
                bool(result["source"]),
            )

            if not result["source"]:
                logger.warning(
                    "YouTube result has no direct stream URL: %s",
                    result["title"],
                )
                return None

            return result

    except Exception:
        logger.exception("YouTube search or resolution failed for: %s", query)
        return None


class MusicPlayer:
    def __init__(self, bot, guild_id: int):
        self.bot = bot
        self.guild_id = guild_id
        self.queue = deque()
        self.voice = None
        self.current = None

        self.volume = 0.5
        self.repeat = False
        self._generation = 0
        self._lock = asyncio.Lock()

        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path is None:
            logger.critical(
                "FFmpeg was not found in PATH. Guild=%s",
                guild_id,
            )
            raise RuntimeError(
                "FFmpeg was not found. Install it and add it to PATH."
            )

        logger.info(
            "Music player initialized: guild=%s ffmpeg=%s",
            guild_id,
            ffmpeg_path,
        )

    @property
    def is_playing(self):
        return bool(self.voice and self.voice.is_playing())

    @property
    def is_paused(self):
        return bool(self.voice and self.voice.is_paused())

    async def connect(self, channel):
        logger.info(
            "Voice connection requested: guild=%s channel=%s channel_id=%s",
            self.guild_id,
            channel.name,
            channel.id,
        )

        try:
            if self.voice and self.voice.is_connected():
                if self.voice.channel != channel:
                    logger.info(
                        "Moving voice channel: guild=%s old=%s new=%s",
                        self.guild_id,
                        self.voice.channel,
                        channel,
                    )
                    await self.voice.move_to(channel)
                    logger.info(
                        "Voice channel move completed: guild=%s",
                        self.guild_id,
                    )
                else:
                    logger.debug(
                        "Already connected to requested voice channel: guild=%s",
                        self.guild_id,
                    )
            else:
                self.voice = await channel.connect()
                logger.info(
                    "Voice connection established: guild=%s channel=%s",
                    self.guild_id,
                    channel.name,
                )

        except Exception:
            logger.exception(
                "Voice connection failed: guild=%s channel=%s",
                self.guild_id,
                channel.name,
            )
            raise

    async def add(self, song):
        self.queue.append(song)

        logger.info(
            "Song added to queue: guild=%s title=%s queue_size=%s",
            self.guild_id,
            song.get("title", "Unknown title"),
            len(self.queue),
        )

        if self.current is None and not self.is_paused:
            await self.play_next()

    async def play_next(self):
        async with self._lock:
            if not self.voice or not self.voice.is_connected():
                logger.warning(
                    "Cannot start playback: voice is disconnected, guild=%s",
                    self.guild_id,
                )
                self.current = None
                return

            if not self.queue:
                self.current = None
                logger.info("Queue is empty: guild=%s", self.guild_id)
                return

            song = self.queue.popleft()
            self.current = song
            self._generation += 1
            token = self._generation

            logger.info(
                "Preparing next track: guild=%s title=%s remaining=%s",
                self.guild_id,
                song.get("title", "Unknown title"),
                len(self.queue),
            )

            # Direct YouTube stream URLs expire, so resolve the page URL again.
            try:
                resolved = await asyncio.to_thread(
                    search_youtube,
                    song["url"],
                )
            except Exception:
                logger.exception(
                    "Unexpected stream resolution error: guild=%s title=%s",
                    self.guild_id,
                    song.get("title"),
                )
                resolved = None

            if not resolved or not resolved.get("source"):
                logger.error(
                    "Could not resolve audio stream: guild=%s title=%s",
                    self.guild_id,
                    song.get("title"),
                )
                self.current = None
                self.bot.loop.call_soon(
                    lambda: asyncio.create_task(self.play_next())
                )
                return

            self.current = {
                **song,
                "title": resolved["title"],
                "url": resolved["url"],
            }

            source = None

            try:
                logger.info(
                    "Creating FFmpeg audio source: guild=%s title=%s volume=%s",
                    self.guild_id,
                    self.current["title"],
                    self.volume,
                )

                audio = discord.FFmpegPCMAudio(
                    resolved["source"],
                    before_options=(
                        "-reconnect 1 "
                        "-reconnect_streamed 1 "
                        "-reconnect_delay_max 5"
                    ),
                    options="-vn",
                )

                source = discord.PCMVolumeTransformer(
                    audio,
                    volume=self.volume,
                )

                def after(error):
                    if error:
                        logger.error(
                            "Audio playback callback reported an error: "
                            "guild=%s title=%s error=%s",
                            self.guild_id,
                            self.current.get("title")
                            if self.current else "Unknown",
                            error,
                        )
                    else:
                        logger.info(
                            "Audio source ended: guild=%s title=%s",
                            self.guild_id,
                            self.current.get("title")
                            if self.current else "Unknown",
                        )

                    try:
                        future = asyncio.run_coroutine_threadsafe(
                            self._after_track(token),
                            self.bot.loop,
                        )

                        def log_callback_result(completed):
                            try:
                                completed.result()
                            except Exception:
                                logger.exception(
                                    "Track completion handler failed: guild=%s",
                                    self.guild_id,
                                )

                        future.add_done_callback(log_callback_result)

                    except Exception:
                        logger.exception(
                            "Could not schedule track completion: guild=%s",
                            self.guild_id,
                        )

                self.voice.play(source, after=after)

                logger.info(
                    "Playback started: guild=%s title=%s",
                    self.guild_id,
                    self.current["title"],
                )

            except Exception:
                logger.exception(
                    "Failed to start FFmpeg/Discord playback: "
                    "guild=%s title=%s",
                    self.guild_id,
                    self.current.get("title", "Unknown title"),
                )

                if source is not None:
                    try:
                        source.cleanup()
                    except Exception:
                        logger.debug(
                            "Audio source cleanup failed.",
                            exc_info=True,
                        )

                self.current = None
                self.bot.loop.call_soon(
                    lambda: asyncio.create_task(self.play_next())
                )

    async def _after_track(self, token):
        # Ignore callbacks from tracks stopped or replaced by a command.
        if token != self._generation:
            logger.debug(
                "Ignoring stale track callback: guild=%s token=%s current=%s",
                self.guild_id,
                token,
                self._generation,
            )
            return

        finished = self.current

        logger.info(
            "Track completed: guild=%s title=%s",
            self.guild_id,
            finished.get("title") if finished else "Unknown",
        )

        if self.repeat and finished:
            self.queue.append(finished)
            logger.info(
                "Repeat enabled; track requeued: guild=%s title=%s",
                self.guild_id,
                finished["title"],
            )

        self.current = None
        await self.play_next()

    async def skip(self):
        if not self.voice or not (
            self.voice.is_playing() or self.voice.is_paused()
        ):
            logger.warning(
                "Skip requested but no track is playing: guild=%s",
                self.guild_id,
            )
            return None

        skipped = self.current

        # Invalidate the callback before stopping the old source.
        self._generation += 1
        self.current = None
        self.voice.stop()

        logger.info(
            "Track skipped: guild=%s title=%s",
            self.guild_id,
            skipped.get("title") if skipped else "Unknown title",
        )

        await self.play_next()
        return skipped

    async def set_volume(self, level: int):
        if not 0 <= level <= 100:
            raise ValueError("Volume must be between 0 and 100.")

        self.volume = level / 100

        if self.voice and self.voice.source:
            if isinstance(
                self.voice.source,
                discord.PCMVolumeTransformer,
            ):
                self.voice.source.volume = self.volume

        logger.info(
            "Volume changed: guild=%s volume=%s%%",
            self.guild_id,
            level,
        )

    async def clear(self):
        cleared_count = len(self.queue)
        self.queue.clear()

        if self.voice and (
            self.voice.is_playing() or self.voice.is_paused()
        ):
            self._generation += 1
            self.voice.stop()

        self.current = None

        logger.info(
            "Queue cleared: guild=%s queued_tracks_removed=%s",
            self.guild_id,
            cleared_count,
        )

    async def disconnect(self):
        logger.info("Disconnect requested: guild=%s", self.guild_id)

        self._generation += 1
        self.queue.clear()
        self.current = None

        if self.voice and self.voice.is_connected():
            await self.voice.disconnect()

        self.voice = None

        logger.info("Disconnected from voice: guild=%s", self.guild_id)
