from discord.ext import commands

import ClsError
import GloablDeclaration as gbl


class Help(commands.Cog):
    text_channel_text = []

    @commands.Cog.listener()
    async def on_read(self):
        try:
            for guild in self.bot.guilds:
                for channel in guild.text_channels:
                    self.text_channel_text.append(channel)

            await self.send_to_all(gbl.MESSAGE_HELP_DEFAULT)
        except Exception as e:
            ClsError.Error.log(self.on_read.__name__, e)

    async def send_to_all(self, msg):
        try:
            for text_channel in self.text_channel_text:
                await text_channel.send(msg)
        except Exception as e:
            ClsError.Error.log(self.send_to_all.__name__, e)

    @commands.command(name="help", help="Display all commands")
    async def help(self, ctx, *args):
        try:
            for cmd in args:
                match cmd.toupper:
                    case gbl.CMD_HELP:
                        await ctx.send(gbl.MESSAGE_HELP_DEFAULT)
                    case gbl.CMD_PAUSE:
                        await ctx.send(gbl.MESSAGE_HELP_PAUSE)
                    case gbl.CMD_QUEUE:
                        await ctx.send(gbl.MESSAGE_HELP_QUEUE)
                    case gbl.CMD_PLAY:
                        await ctx.send(gbl.MESSAGE_HELP_PLAY)
                    case gbl.CMD_SKIP:
                        await ctx.send(gbl.MESSAGE_HELP_SKIP)
                    case gbl.CMD_STOP:
                        await ctx.send(gbl.MESSAGE_HELP_STOP)
                    case gbl.CMD_RESUME:
                        await ctx.send(gbl.MESSAGE_HELP_RESUME)

        except Exception as e:
            ClsError.Error.log(self.help.__name__, e)
