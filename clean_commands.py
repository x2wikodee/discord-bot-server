import sys
import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    print("Clearing duplicate guild commands...")
    for guild in bot.guilds:
        bot.tree.clear_commands(guild=guild)
        await bot.tree.sync(guild=guild)
        print(f"Cleared guild commands for: {guild.name}")
    
    print("Syncing global commands...")
    synced = await bot.tree.sync()
    print(f"Done! {len(synced)} Global commands synced cleanly.")
    await bot.close()

if __name__ == "__main__":
    bot.run(TOKEN)
