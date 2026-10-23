
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from logging_config import configure_logging

load_dotenv()
configure_logging()

logger = logging.getLogger("bot")


def create_bot():
    intents = discord.Intents.default()
    intents.message_content = True
    intents.voice_states = True

    bot = commands.Bot(
        command_prefix=".",
        intents=intents,
    )

    owner_id = os.getenv("OWNER_ID")
    if owner_id and owner_id.isdigit():
        bot.owner_id = int(owner_id)

    # The music cog provides its own help command.
    bot.remove_command("help")

    return bot


bot = create_bot()


@bot.event
async def on_ready():
    logger.info(
        "Connected to Discord as %s (ID: %s)",
        bot.user,
        bot.user.id if bot.user else "unknown",
    )


@bot.event
async def on_connect():
    logger.info("Discord gateway connection established.")


@bot.event
async def on_disconnect():
    logger.warning("Disconnected from the Discord gateway.")


@bot.event
async def on_resumed():
    logger.info("Discord gateway session resumed.")


@bot.event
async def on_command(ctx):
    logger.info(
        "Command received: command=%s user=%s guild=%s channel=%s",
        ctx.command.qualified_name if ctx.command else "unknown",
        ctx.author.id,
        ctx.guild.id if ctx.guild else "DM",
        ctx.channel.id,
    )


@bot.event
async def on_command_completion(ctx):
    logger.info(
        "Command completed: command=%s user=%s guild=%s",
        ctx.command.qualified_name if ctx.command else "unknown",
        ctx.author.id,
        ctx.guild.id if ctx.guild else "DM",
    )


@bot.event
async def on_command_error(ctx, error):
    # Commands handled by other command-level error handlers
    # should not be logged twice.
    if ctx.command and ctx.command.has_error_handler():
        return

    original = getattr(error, "original", error)

    if isinstance(error, commands.CommandNotFound):
        logger.debug("Unknown command received: %s", ctx.message.content)
        return

    if isinstance(error, commands.MissingRequiredArgument):
        logger.warning(
            "Missing command argument: command=%s argument=%s user=%s",
            ctx.command.qualified_name if ctx.command else "unknown",
            error.param.name,
            ctx.author.id,
        )
        await ctx.send(
            f"Missing argument: `{error.param.name}`. "
            "Use `.help` to see command usage."
        )
        return

    if isinstance(error, commands.BadArgument):
        logger.warning(
            "Invalid command argument: command=%s user=%s error=%s",
            ctx.command.qualified_name if ctx.command else "unknown",
            ctx.author.id,
            error,
        )
        await ctx.send("Invalid argument. Please check the command usage.")
        return

    if isinstance(error, commands.NoPrivateMessage):
        await ctx.send("This command can only be used in a server.")
        return

    logger.error(
        "Command failed: command=%s user=%s guild=%s",
        ctx.command.qualified_name if ctx.command else "unknown",
        ctx.author.id,
        ctx.guild.id if ctx.guild else "DM",
        exc_info=(type(original), original, original.__traceback__),
    )

    try:
        await ctx.send("An unexpected error occurred. Check the bot logs.")
    except discord.HTTPException:
        logger.exception("Could not send command error message to Discord.")


async def main():
    token = os.getenv("TOKEN")

    if not token:
        raise RuntimeError("TOKEN is missing from your .env file.")

    logger.info("Loading music extension...")

    async with bot:
        await bot.load_extension("cogs.music")
        logger.info("Music extension loaded successfully.")
        logger.info("Starting Discord bot...")
        await bot.start(token)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception:
        logger.exception("Fatal error while running the bot.")
        raise
