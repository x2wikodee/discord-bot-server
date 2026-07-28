import sys
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
LOG_FILE_PATH = os.path.join(os.path.dirname(__file__), "bot.log")

def write_log(message: str):
    """ฟังก์ชันเขียน Log ลงไฟล์ bot.log อัตโนมัติ"""
    try:
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{now}] {message}\n"
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Failed to write log: {e}")

write_log("--- Clearing All Slash Commands ---")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

@bot.event
async def on_ready():
    msg = f"Bot connected: {bot.user} - Clearing all commands..."
    print(msg)
    write_log(msg)
    
    # ล้างคำสั่ง Slash Commands ทั้งแบบ Global และ Guild ทั้งหมด
    bot.tree.clear_commands(guild=None)
    for guild in bot.guilds:
        bot.tree.clear_commands(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        print(f"Cleared slash commands for guild {guild.name} (Remaining: {len(synced)})")
        write_log(f"Cleared slash commands for guild {guild.name}")
        
    await bot.tree.sync()
    print("All slash commands cleared successfully 100%!")
    write_log("All slash commands cleared successfully 100%!")
    await bot.change_presence(activity=discord.Game(name="ระบบออฟไลน์คำสั่งชั่วคราว"))

if __name__ == "__main__":
    if not TOKEN or TOKEN == "your_bot_token_here":
        print("Error: Please set DISCORD_TOKEN in .env file")
    else:
        bot.run(TOKEN)
