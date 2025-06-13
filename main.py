import discord
from dotenv import load_dotenv
import os
from discord.ext import commands
import ezcord
import asyncio

load_dotenv()
bot = ezcord.Bot(
    intents=discord.Intents.default(),
    error_webhook_url=os.getenv("ERROR-HOOK"),
    language="en",
)
@bot.event
async def on_ready():
    bot.remove_ready_info("Guilds")  # Remove an information
    bot.remove_ready_info(0)  # Remove the first information

    # Add an information at the end
    bot.add_ready_info("Title", "This is a custom info")

    # Add an information at the first position with a custom color
    bot.add_ready_info("Title", "This is another custom info", 0, "red")

    bot.ready(
        title="Bot is online!",
        style=ezcord.ReadyEvent.default,
    )

bot.load_cogs("cogs")
bot.run(os.getenv("TOKEN"))
