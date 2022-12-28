import os
from dotenv import load_dotenv
from discord.ext import commands
from music_cog import music_cog
from help_cog import help_cog
# import discord

load_dotenv()
bot = commands.Bot(command_prefix='\\')
bot.owner_id = os.getenv('owner_id')

bot.remove_command("help")


bot.add_cog((help_cog(bot)))
bot.add_cog((music_cog(bot)))


@bot.event
async def on_ready():
    print(f'{bot.owner_id} has connected to Discord!')


bot.run(os.getenv('TOKEN'))
