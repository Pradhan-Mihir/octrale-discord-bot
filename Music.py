import discord
import GloablDeclaration as gbl
from ClsError import Error as err
from yt_dlp import YoutubeDL
from discord.ext import commands
from dotenv import load_dotenv
import os

load_dotenv()


class Music(commands.Cog):
    is_playing = False
    is_paused = False
    err_message = ""
    vc = None

    music_queue = []
    YDL_OPTIONS = {'format': "bestaudio/best", 'noplaylist': True}
    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn',
        'executable': os.getenv('FFMPEG_PATH')  # Set FFmpeg path if necessary
    }

    # noinspection PyTypeChecker
    def search_yt(self, item):
        try:
            with YoutubeDL(self.YDL_OPTIONS) as ydl:
                try:
                    # Search YouTube and extract video info
                    info = ydl.extract_info(f"ytsearch:{item}", download=False)['entries'][0]
                except Exception as e:
                    err.log(e, self.search_yt.__name__)
                    return False
                src = info['url']  # Direct audio stream URL
            return {'source': src, 'title': info['title']}
        except Exception as e:
            err.log(e, self.search_yt.__name__)

    def play_next(self):
        try:
            if len(self.music_queue) > 0:
                self.is_playing = True
                m_url = self.music_queue.pop(0)[0]['source']
                self.vc.play(discord.FFmpegPCMAudio(m_url, **self.FFMPEG_OPTIONS), after=lambda x: self.play_next())
            else:
                self.is_playing = False
        except Exception as e:
            err.log(e, self.play_next.__name__)

    async def play_music(self, ctx):
        try:
            if len(self.music_queue) > 0:
                self.is_playing = True
                m_url = self.music_queue[0][0]['source']

                if self.vc is None or not self.vc.is_connected():
                    self.vc = await self.music_queue[0][1].connect()

                    if self.vc is None:
                        await ctx.send('Cannot connect to the voice channel.')
                        return
                else:
                    await self.vc.move_to(self.music_queue[0][1])

                self.music_queue.pop(0)

                self.vc.play(discord.FFmpegPCMAudio(m_url, **self.FFMPEG_OPTIONS), after=lambda x: self.play_next())
            else:
                self.is_playing = False
        except Exception as e:
            self.is_playing = False
            err.log(e, self.is_playing.__name__)
        finally:
            if len(self.music_queue) == 0:
                self.is_playing = False

    @commands.command(name="play", aliases=["p", "playing"], help="Play the selected song from YouTube.",
                      pass_context=True)
    async def play(self, ctx, *args):
        try:
            query = " ".join(args)

            if ctx.author.voice is None or ctx.author.voice.channel is None:
                await ctx.send("You need to connect to a voice channel first.")
            elif self.is_paused:
                self.vc.resume()
            else:
                if not query.strip():
                    await ctx.send("Please provide a valid song name or URL.")
                    return

                # Ensure the bot joins the author's voice channel
                joined = await self.join_voice_channel(ctx)
                if not joined:  # Exit if the bot could not connect
                    return

                voice_channel = ctx.author.voice.channel
                song = self.search_yt(query)

                if not song:
                    await ctx.send("Could not find or download the song. Try a different search term.")
                else:
                    await ctx.send(f"Added to queue: {song['title']}")

                    self.music_queue.append([song, voice_channel])

                    if not self.is_playing:
                        await self.play_music(ctx)
        except Exception as e:
            err.log(e, gbl.CMD_PLAY)

    @commands.command(name="pause", help="Pause the current song.")
    async def pause(self, ctx):
        try:
            if self.is_playing:
                self.is_playing = False
                self.is_paused = True
                self.vc.pause()
            else:
                await ctx.send("Nothing is playing to pause.")
        except Exception as e:
            err.log(e, gbl.CMD_PAUSE)

    @commands.command(name="resume", aliases=["r"], help="Resume the paused song.")
    async def resume(self, ctx):
        try:
            if self.is_paused:
                self.is_playing = True
                self.is_paused = False
                self.vc.resume()
            else:
                await ctx.send("Nothing is paused to resume.")
        except Exception as e:
            err.log(e, gbl.CMD_RESUME)

    @commands.command(name="skip", aliases=["s"], help="Skip the current song.")
    async def skip(self, ctx):
        try:
            if self.vc is not None and self.vc.is_playing():
                self.vc.stop()
                await self.play_music(ctx)
        except Exception as e:
            err.log(e, gbl.CMD_SKIP)

    @commands.command(name="queue", aliases=["q"], help="Show the current music queue.")
    async def queue(self, ctx):
        try:
            if len(self.music_queue) > 0:
                queue_list = "\n".join([song[0]['title'] for song in self.music_queue[:5]])
                await ctx.send(f"Current queue:\n{queue_list}")
            else:
                await ctx.send("The music queue is empty.")
        except Exception as e:
            err.log(e, gbl.CMD_QUEUE)

    @commands.command(name="clear", aliases=["c"], help="Clear the music queue.")
    async def clear(self, ctx):
        if self.vc is not None and self.is_playing:
            self.vc.stop()
        self.music_queue = []
        await ctx.send("The music queue has been cleared.")

    @commands.command(name="leave", aliases=["l", "disconnect", "dc"],
                      help="Disconnect the bot from the voice channel.")
    async def leave(self, ctx):
        self.is_playing = False
        self.is_paused = False
        if self.vc is not None:
            await self.vc.disconnect()
        await ctx.send("Disconnected from the voice channel.")

    async def join_voice_channel(self, ctx):
        """
        Ensures the bot joins the voice channel of the message author.
        If already connected to a different channel, it moves to the author's channel.
        Handles exceptions and permissions properly.
        """
        try:
            if ctx.author.voice and ctx.author.voice.channel:  # Check if the author is in a voice channel
                voice_channel = ctx.author.voice.channel

                if self.vc is None or not self.vc.is_connected():
                    try:
                        # Connect to the author's voice channel if not already connected
                        self.vc = await voice_channel.connect()
                    except discord.errors.ClientException as e:
                        await ctx.send(f"Error connecting to the channel: {e}")
                        return False
                    except discord.errors.DiscordException as e:
                        await ctx.send(f"Permission denied to join the channel: {e}")
                        return False
                    except Exception as e:
                        await ctx.send(f"An unexpected error occurred: {e}")
                        return False
                else:
                    # Move to the author's voice channel if connected to a different one
                    if self.vc.channel != voice_channel:
                        try:
                            await self.vc.move_to(voice_channel)
                        except discord.errors.ClientException as e:
                            await ctx.send(f"Error moving to the channel: {e}")
                            return False
                        except Exception as e:
                            await ctx.send(f"An unexpected error occurred while moving: {e}")
                            return False
            else:
                # Notify if the author is not in a voice channel
                await ctx.send("You need to be in a voice channel to use this command!")
                return False  # Return False if not connected successfully

            return True  # Return True if successfully connected or moved
        except Exception as e:
            print("Exception", {e})
            await ctx.send(f"An unexpected error occurred: {e}")
        finally:
            print("done")
