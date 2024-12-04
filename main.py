#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import asyncio
from dotenv import load_dotenv
from discord.ext import commands
from Music import Music
from Help import Help
import discord

# Load environment variables
load_dotenv()

# Define intents
intents = discord.Intents.default()
intents.messages = True
intents.presences = True
intents.message_content = True  # Enable message content intent

# Create bot instance
bot = commands.Bot(command_prefix='.', intents=intents)
bot.owner_id = os.getenv('owner_id')

# Remove default help command
bot.remove_command("help")

# Setup function to add cogs
async def setup():
    await bot.add_cog(Music(bot))
    await bot.add_cog(Help(bot))

# Event to confirm bot is ready
@bot.event
async def on_ready():
    print(f'{bot.owner_id} has connected to Discord!')

# Main entry point
async def main():
    await setup()  # Add cogs
    await bot.start(os.getenv('TOKEN'))  # Start the bot

# Run the bot
if __name__ == '__main__':
    asyncio.run(main())
