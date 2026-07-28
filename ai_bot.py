import sys
import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import requests

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

TOKEN = os.getenv("AI_DISCORD_TOKEN") or os.getenv("DISCORD_TOKEN")
NINEROUTER_URL = os.getenv("NINEROUTER_URL", "https://xkiro.com/v1").strip()
NINEROUTER_KEY = os.getenv("NINEROUTER_KEY", "").strip()

BASE_URL = NINEROUTER_URL.rstrip('/')
if BASE_URL.endswith('/v1'):
    AI_ENDPOINT = f"{BASE_URL}/chat/completions"
else:
    AI_ENDPOINT = f"{BASE_URL}/v1/chat/completions"

MODEL_NAME = os.getenv("AI_MODEL_NAME", "minimax/minimax-m3").strip()

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="?", intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f"🤖 Dedicated AI Bot Connected: {bot.user}")
    print(f"AI Endpoint Target: {AI_ENDPOINT}")
    print(f"AI Model Name Target: {MODEL_NAME}")
    try:
        for guild in bot.guilds:
            # เคลียร์คำสั่งค้างเก่าทิ้งทั้งหมด ให้เหลือแค่ /ask เดียว 100%
            bot.tree.clear_commands(guild=guild)
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            print(f"Synced {len(synced)} slash command cleanly for AI bot in {guild.name}")
    except Exception as e:
        print(f"Failed sync: {e}")
    await bot.change_presence(activity=discord.Game(name="🤖 พิมพ์ /ask เพื่อคุยกับ AI"))

# --- Slash Command เพียงตัวเดียว: /ask ---
@bot.tree.command(name="ask", description="ถามคำถามคุยกับ AI อัตโนมัติ")
async def slash_ask(interaction: discord.Interaction, question: str):
    await interaction.response.defer()
    headers = {"Content-Type": "application/json"}
    if NINEROUTER_KEY:
        headers["Authorization"] = f"Bearer {NINEROUTER_KEY}"
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": question}],
        "stream": False
    }
    try:
        res = requests.post(AI_ENDPOINT, json=payload, headers=headers, timeout=60)
        if res.status_code == 200:
            reply = res.json()["choices"][0]["message"]["content"]
            await interaction.followup.send(reply[:2000])
        else:
            await interaction.followup.send(f"❌ AI Status Error ({res.status_code}): {res.text[:150]}")
    except Exception as e:
        await interaction.followup.send(f"❌ AI Error: {e}")

if __name__ == "__main__":
    if not TOKEN:
        print("Error: Please set AI_DISCORD_TOKEN in .env")
    else:
        bot.run(TOKEN)
