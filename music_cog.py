import discord
from youtube_dl import YoutubeDL
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()


class music_cog(commands.Cog):
    is_playing = False
    is_paused = False

    music_queue = []
    YDL_OPTIONS = {'format': "bestaudio/best", 'noplaylist': 'Ture'}
    FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                      'options': '-vn'}

    vc = None

    def search_yt(self, item):

        with YoutubeDL(self.YDL_OPTIONS) as ydl:
            try:
                info = ydl.extract_info("ytsearch:%s" % item, download=False)['entries'][0]
            except Exception:
                return False
            src = info['formats'][1]['url']
        return {'source': src, 'title': info['title']}

    def play_next(self):
        if len(self.music_queue) > 0:
            self.is_playing = True

            m_url = self.music_queue.pop(0)

            self.vc.play(discord.FFmpegOpusAudio(m_url, **self.FFMPEG_OPTIONS), after=lambda e: self.play_next())
        else:
            self.is_playing = False

    async def play_music(self, ctx):

        if len(self.music_queue) > 0:
            self.is_playing = True
            m_url = self.music_queue[0][0]['source']

            if self.vc is None or not self.vc.is_connected():
                self.vc = await self.music_queue[0][1].connect()

                if self.vc is None:
                    await ctx.send('cannot connect to vc')
                    return

            else:
                await self.vc.move_to(self.music_queue[0][1])

            self.music_queue.pop(0)

            self.vc.play(discord.FFmpegPCMAudio(m_url, **self.FFMPEG_OPTIONS), after=lambda e: self.play_next())

        else:
            self.is_playing = False

    @commands.command(name="play", aliases=["p", "playing"], help="Play the selected song from youtube")
    async def play(self, ctx, *args):

        query = " ".join(args)

        # print(query)
        # print("in play command")

        if ctx.author.voice is None or ctx.author.voice.channel is None:
            await ctx.send("connect to a voice channel")
        elif self.is_paused:
            self.vc.resume()
        else:
            if not len(query.strip()):
                await ctx.send("Invalid Song Name")
                return

            voice_channel = ctx.author.voice.channel
            song = self.search_yt(query)
            print(song)
            if type(song) == type(True):
                await ctx.send("could not download the song, incorrect format, Try a different keyword")
            else:
                await ctx.send("song added to Queue \n 1")
                await ctx.send(song['source'])
                self.music_queue.append([song, voice_channel])

                if self.is_playing == False:
                    await self.play_music(song)

    @commands.command(name="pause", help="Pause the Player")
    async def pause(self, ctx, *args):
        if self.is_playing:
            self.is_playing = False
            self.is_paused = True
            self.vc.pause()

        elif self.is_paused:
            self.is_playing = True
            self.is_paused = False
            self.vc.resume()

    @commands.command(name="resume", aliases=["r", "shuru"], help="Resume the Player ")
    async def resume(self, ctx, *args):
        if self.is_paused:
            self.is_playing = True
            self.is_paused = False
            self.vc.resume()

        elif self.is_paused:
            self.vc.resume()

    @commands.command(name="skip", aliases=["bhag", "s"], help="skip the song ")
    async def skip(self, ctx, *args):
        if self.vc != None and self.vc:
            self.vc.stop()
            await self.play_music(ctx)

    @commands.command(name="queue", aliases=["q"], help="skip the song ")
    async def queue(self, ctx, *args):
        retval = ""

        for i in range(0, len(self.music_queue)):
            if i > 4: break
            retval += self.music_queue[i][0]['title'] + '\n'

        if retval != '':
            await ctx.send(retval)
        else:
            await ctx.send('no music in queue')

    @commands.command(name="clear", aliases=["c"], help="clear the Queue")
    async def clear(self, ctx, *args):
        if self.vc != None and self.is_playing:
            self.vc.stop()
        self.music_queue = []
        await ctx.send("music Queue cleared")

    @commands.command(name="leave", aliases=["l", "disconnect", "dc"], help="Leave the voice channel")
    async def leave(self, ctx, *args):
        self.is_playing = False
        self.is_paused = False
        await self.vc.disconnect()
        await ctx.send("Bye!")
