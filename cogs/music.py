
import asyncio
import logging

import discord
from discord.ext import commands

import GlobalDeclaration
from music.player import MusicPlayer, search_youtube
from music.playlists import PlaylistManager

logger = logging.getLogger("music.cog")


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.players = {}
        self.playlists = PlaylistManager()

    def get_player(self, guild_id: int):
        if guild_id not in self.players:
            self.players[guild_id] = MusicPlayer(self.bot, guild_id)
        return self.players[guild_id]

    async def ensure_voice(self, ctx):
        if ctx.guild is None:
            await ctx.send("This command can only be used in a server.")
            return None

        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("Join a voice channel first.")
            return None

        player = self.get_player(ctx.guild.id)

        try:
            await player.connect(ctx.author.voice.channel)
            return player
        except Exception:
            logger.exception("Could not connect to voice in guild %s", ctx.guild.id)
            await ctx.send("Couldn't connect to your voice channel.")
            return None

    @commands.command(name="play", aliases=["p"], help="Play or queue a song.")
    async def play(self, ctx, *, query: str):
        player = await self.ensure_voice(ctx)
        if player is None:
            return

        async with ctx.typing():
            song = await asyncio.to_thread(search_youtube, query)

        if not song:
            await ctx.send("Couldn't find that song.")
            return

        await player.add(song)
        logger.info(
            "User %s requested '%s' in guild %s",
            ctx.author.id,
            song["title"],
            ctx.guild.id,
        )
        await ctx.send(f"Added to queue: **{song['title']}**")

    @commands.command(name="pause")
    async def pause(self, ctx):
        player = self.players.get(ctx.guild.id) if ctx.guild else None

        if player and player.is_playing:
            player.voice.pause()
            logger.info("User %s paused guild %s", ctx.author.id, ctx.guild.id)
            await ctx.send("Playback paused.")
        else:
            await ctx.send("Nothing is playing.")

    @commands.command(name="resume", aliases=["r"])
    async def resume(self, ctx):
        player = self.players.get(ctx.guild.id) if ctx.guild else None

        if player and player.is_paused:
            player.voice.resume()
            logger.info("User %s resumed guild %s", ctx.author.id, ctx.guild.id)
            await ctx.send("Playback resumed.")
        else:
            await ctx.send("Nothing is paused.")

    @commands.command(name="skip")
    async def skip(self, ctx):
        player = self.players.get(ctx.guild.id) if ctx.guild else None

        if not player:
            await ctx.send("Nothing is playing.")
            return

        song = await player.skip()
        if song:
            await ctx.send(f"Skipped: **{song['title']}**")
        else:
            await ctx.send("Nothing is playing.")

    @commands.command(name="volume", aliases=["vol"])
    async def volume(self, ctx, level: int = None):
        player = self.players.get(ctx.guild.id) if ctx.guild else None
        if player is None:
            await ctx.send("The music player hasn't been initialized.")
            return

        if level is None:
            await ctx.send(f"Current volume: **{round(player.volume * 100)}%**")
            return

        try:
            await player.set_volume(level)
            await ctx.send(f"Volume set to **{level}%**.")
        except ValueError as exc:
            await ctx.send(str(exc))

    @commands.command(name="repeat")
    async def repeat(self, ctx, mode: str = None):
        player = self.get_player(ctx.guild.id) if ctx.guild else None
        if player is None:
            await ctx.send("Use this command in a server.")
            return

        if mode is None:
            player.repeat = not player.repeat
        elif mode.lower() in ("on", "off"):
            player.repeat = mode.lower() == "on"
        else:
            await ctx.send("Usage: `.repeat [on|off]`")
            return

        logger.info(
            "User %s set repeat=%s in guild %s",
            ctx.author.id,
            player.repeat,
            ctx.guild.id,
        )
        await ctx.send(
            f"Queue repeat **{'enabled' if player.repeat else 'disabled'}**."
        )

    @commands.command(name="queue", aliases=["q"])
    async def queue(self, ctx):
        player = self.players.get(ctx.guild.id) if ctx.guild else None

        if player is None:
            await ctx.send("The queue is empty.")
            return

        lines = []
        if player.current:
            lines.append(f"**Now playing:** {player.current['title']}")

        lines.extend(
            f"{index}. {song['title']}"
            for index, song in enumerate(player.queue, start=1)
        )

        if not lines:
            await ctx.send("The queue is empty.")
            return

        # Keep the message below Discord's 2000-character limit.
        message = "\n".join(lines)
        await ctx.send(message[:1990])

    @commands.command(name="clear", aliases=["stop", "s"])
    async def clear(self, ctx):
        player = self.players.get(ctx.guild.id) if ctx.guild else None

        if player:
            await player.clear()

        await ctx.send("Music queue cleared and playback stopped.")

    @commands.command(name="leave", aliases=["l"])
    async def leave(self, ctx):
        player = self.players.get(ctx.guild.id) if ctx.guild else None

        if player:
            await player.disconnect()

        await ctx.send("Disconnected from the voice channel.")

    # ---------- Playlists ----------

    @commands.command(name="saveplaylist")
    async def save_playlist(self, ctx, *, name: str):
        player = self.players.get(ctx.guild.id) if ctx.guild else None
        songs = list(player.queue) if player else []

        if player and player.current:
            songs.insert(0, player.current)

        try:
            self.playlists.save(ctx.author.id, name, songs)
            await ctx.send(f"Playlist **{name}** saved.")
        except ValueError as exc:
            await ctx.send(str(exc))
        except Exception:
            logger.exception("Failed to save playlist for user %s", ctx.author.id)
            await ctx.send("Couldn't save the playlist.")

    @commands.command(name="loadplaylist")
    async def load_playlist(self, ctx, *, name: str):
        player = await self.ensure_voice(ctx)
        if player is None:
            return

        try:
            playlist = self.playlists.load(ctx.author.id, name)
            if not playlist:
                await ctx.send("Playlist not found.")
                return

            added = 0
            async with ctx.typing():
                for item in playlist["songs"]:
                    song = await asyncio.to_thread(search_youtube, item["url"])
                    if song:
                        await player.add(song)
                        added += 1

            await ctx.send(
                f"Loaded **{playlist['name']}**: {added} songs added."
            )
        except Exception:
            logger.exception("Failed to load playlist '%s'", name)
            await ctx.send("Couldn't load the playlist.")

    @commands.command(name="myplaylists")
    async def my_playlists(self, ctx):
        names = self.playlists.list_names(ctx.author.id)

        if names:
            await ctx.send("Your playlists: " + ", ".join(names))
        else:
            await ctx.send("You haven't saved any playlists.")

    @commands.command(name="shareplaylist")
    async def share_playlist(self, ctx, *, name: str):
        try:
            path = self.playlists.export(ctx.author.id, name)
            await ctx.send(
                f"Share playlist **{name}** using this file:",
                file=discord.File(path, filename=f"{name}.json"),
            )
        except FileNotFoundError:
            await ctx.send("Playlist not found.")
        except PermissionError:
            await ctx.send("You don't own that playlist.")
        except Exception:
            logger.exception("Failed to export playlist '%s'", name)
            await ctx.send("Couldn't export the playlist.")

    @commands.command(name="importplaylist")
    async def import_playlist(self, ctx):
        if not ctx.message.attachments:
            await ctx.send("Attach a playlist `.json` file to your message.")
            return

        attachment = ctx.message.attachments[0]

        if not attachment.filename.lower().endswith(".json"):
            await ctx.send("The attachment must be a `.json` file.")
            return

        try:
            content = await attachment.read()
            self.playlists.import_data(ctx.author.id, content)
            await ctx.send("Playlist imported successfully.")
        except Exception:
            logger.exception("Playlist import failed for user %s", ctx.author.id)
            await ctx.send("Invalid playlist file or unsupported playlist data.")

    @commands.command(name="help", aliases=["musichelp"])
    async def music_help(self, ctx, *, command: str = None):
        help_messages = {
            "play": GlobalDeclaration.MESSAGE_HELP_PLAY,
            "p": GlobalDeclaration.MESSAGE_HELP_PLAY,
            "pause": GlobalDeclaration.MESSAGE_HELP_PAUSE,
            "skip": GlobalDeclaration.MESSAGE_HELP_SKIP,
            "queue": GlobalDeclaration.MESSAGE_HELP_QUEUE,
            "q": GlobalDeclaration.MESSAGE_HELP_QUEUE,
            "resume": GlobalDeclaration.MESSAGE_HELP_RESUME,
            "r": GlobalDeclaration.MESSAGE_HELP_RESUME,
            "stop": GlobalDeclaration.MESSAGE_HELP_STOP,
            "s": GlobalDeclaration.MESSAGE_HELP_STOP,
            "help": GlobalDeclaration.MESSAGE_HELP_DEFAULT,
        }

        if command:
            message = help_messages.get(command.lower())
            if message:
                await ctx.send(message)
            else:
                await ctx.send(f"Unknown command: {command}")
            return

        await ctx.send(
            "**Music commands**\n"
            "`.play <song>` / `.p <song>` — Play a song\n"
            "`.pause` — Pause playback\n"
            "`.resume` / `.r` — Resume playback\n"
            "`.skip` — Skip and announce the current song\n"
            "`.queue` / `.q` — Show the queue\n"
            "`.volume [0-100]` — Set or view volume\n"
            "`.repeat [on|off]` — Toggle queue repeat\n"
            "`.stop` / `.s` — Clear queue and stop playback\n"
            "`.leave` / `.l` — Disconnect the bot\n\n"
            "**Playlists**\n"
            "`.saveplaylist <name>` — Save the current queue\n"
            "`.loadplaylist <name>` — Load your playlist\n"
            "`.myplaylists` — List your playlists\n"
            "`.shareplaylist <name>` — Export a JSON file\n"
            "`.importplaylist` — Import an attached JSON file"
        )


async def setup(bot):
    await bot.add_cog(Music(bot))
    logger.info("Music cog loaded")
