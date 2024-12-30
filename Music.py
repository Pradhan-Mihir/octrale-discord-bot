import discord
from yt_dlp import YoutubeDL
from discord.ext import commands
from dotenv import load_dotenv
import ffmpeg

import ClsError
import GlobalDeclaration

load_dotenv()


async def send_message(ctx, msg):
    msg = "```" + msg + "```"
    await ctx.send(msg)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.is_playing = False
        self.is_paused = False
        self.music_queue = []
        self.vc = None

        # YouTube Downloader Options
        self.YDL_OPTIONS = {'format': "bestaudio/best", 'noplaylist': True}

    def search_yt(self, query):
        """
        Searches for a YouTube video and retrieves audio stream details.
        """
        try:
            with YoutubeDL(self.YDL_OPTIONS) as ydl:
                info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
                return {'source': info['url'], 'title': info['title']}
        except Exception as e:
            print(f"Error in search_yt: {e}")
            return None

    def play_next(self):
        """
        Plays the next song in the queue.
        """
        if len(self.music_queue) > 1:
            self.is_playing = True
            self.music_queue.pop(0)
            m_url = self.music_queue.pop(0)['source']
            self.stream_audio(m_url)
        else:
            self.is_playing = False

    def stream_audio(self, m_url):
        """
        Streams audio using ffmpeg-python.
        """
        try:
            input_stream = ffmpeg.input(m_url)
            output_stream = ffmpeg.output(input_stream, 'pipe:', format='wav', acodec='pcm_s16le')
            process = output_stream.run_async(pipe_stdout=True, pipe_stderr=True)

            self.vc.play(discord.PCMAudio(process.stdout), after=lambda e: self.play_next())
        except Exception as e:
            print(f"Error streaming audio: {e}")
            self.is_playing = False

    async def play_music(self, ctx):
        """
        Starts playing music from the queue.
        """
        if len(self.music_queue) > 0:
            self.is_playing = True
            m_url = self.music_queue[0]['source']

            # Connect to voice channel
            if self.vc is None or not self.vc.is_connected():
                voice_channel = self.music_queue[0]['channel']
                self.vc = await voice_channel.connect()

            self.stream_audio(m_url)
        else:
            self.is_playing = False

    @commands.command(name="play", aliases=["p"], help="Plays a song from YouTube.")
    async def play(self, ctx, *args):
        """
        Play command to search and queue a song from YouTube.
        """
        query = " ".join(args)
        if not ctx.author.voice:
            await send_message(ctx, "You need to be in a voice channel to use this command!")
            return

        # Join the author's voice channel if not already connected
        if self.vc is None or not self.vc.is_connected():
            await self.join_voice_channel(ctx)

        song = self.search_yt(query)
        if not song:
            await send_message(ctx, "Could not find the song. Please try again with a different query.")
        else:
            await send_message(ctx, f"Added to queue: {song['title']}")
            self.music_queue.append(
                {'source': song['source'], 'title': song['title'], 'channel': ctx.author.voice.channel})

            if not self.is_playing:
                await self.play_music(ctx)

    @commands.command(name="pause", help="Pauses the current song.")
    async def pause(self, ctx):
        if self.is_playing:
            self.is_playing = False
            self.is_paused = True
            self.vc.pause()
        else:
            await send_message(ctx, "No music is playing.")

    @commands.command(name="resume", help="Resumes the paused song.")
    async def resume(self, ctx):
        if self.is_paused:
            self.is_playing = True
            self.is_paused = False
            self.vc.resume()
        else:
            await send_message(ctx, "No song is paused.")

    @commands.command(name="skip", help="Skips the current song.")
    async def skip(self, ctx):
        if self.vc.is_playing():
            self.vc.stop()
            self.play_next()

    @commands.command(name="queue", help="Displays the current music queue.")
    async def queue(self, ctx):
        if len(self.music_queue) > 0:
            queue_list = "\n".join([f"{idx + 1}. {song['title']}" for idx, song in enumerate(self.music_queue)])
            await send_message(ctx, f"**Current Queue:**\n{queue_list}")
        else:
            await send_message(ctx, "The queue is empty.")

    @commands.command(name="clear", help="Clears the music queue.")
    async def clear(self, ctx):
        self.music_queue.clear()
        if self.vc.is_playing():
            self.vc.stop()
        await send_message(ctx, "Music queue has been cleared.")

    @commands.command(name="leave", help="Disconnects the bot from the voice channel.")
    async def leave(self, ctx):
        self.is_playing = False
        self.is_paused = False
        if self.vc:
            await self.vc.disconnect()
        await send_message(ctx, "Disconnected from the voice channel.")

    async def join_voice_channel(self, ctx):
        """
        Ensures the bot joins the author's voice channel.
        """
        if ctx.author.voice and ctx.author.voice.channel:
            voice_channel = ctx.author.voice.channel
            if self.vc is None or not self.vc.is_connected():
                self.vc = await voice_channel.connect()
            else:
                await self.vc.move_to(voice_channel)
        else:
            await send_message(ctx, "You need to be in a voice channel!")

    @commands.command(name="help", help="Display all commands")
    async def help(self, ctx, *args):
        """
        Handles the help command and provides details for specific commands.
        """
        try:
            # Fallback default help message
            if not args:
                await send_message(ctx, GlobalDeclaration.MESSAGE_HELP_DEFAULT)
                return

            # Process arguments
            for token in args:
                match token.upper():
                    case GlobalDeclaration.CMD_HELP:
                        await send_message(ctx, GlobalDeclaration.MESSAGE_HELP_DEFAULT)
                    case GlobalDeclaration.CMD_PAUSE:
                        await send_message(ctx, GlobalDeclaration.MESSAGE_HELP_PAUSE)
                    case GlobalDeclaration.CMD_QUEUE:
                        await send_message(ctx, GlobalDeclaration.MESSAGE_HELP_QUEUE)
                    case GlobalDeclaration.CMD_PLAY:
                        await send_message(ctx, GlobalDeclaration.MESSAGE_HELP_PLAY)
                    case GlobalDeclaration.CMD_SKIP:
                        await send_message(ctx, GlobalDeclaration.MESSAGE_HELP_SKIP)
                    case GlobalDeclaration.CMD_STOP:
                        await send_message(ctx, GlobalDeclaration.MESSAGE_HELP_STOP)
                    case GlobalDeclaration.CMD_RESUME:
                        await send_message(ctx, GlobalDeclaration.MESSAGE_HELP_RESUME)
                    case _:
                        await send_message(ctx, f"Unknown command: {token}")
        except Exception as e:
            ClsError.Error.log(self.help.__name__, e)
