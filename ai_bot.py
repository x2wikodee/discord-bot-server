import sys
import os
import gc
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

# ตั้งค่า System Prompt ให้ AI จำชื่อตนเอง บทบาท และบุคลิกได้อย่างถูกต้องถาวร
SYSTEM_PROMPT = os.getenv(
    "AI_SYSTEM_PROMPT",
    "คุณคือ AI Assistant บอทประจำเซิร์ฟเวอร์ดิสคอร์ด ให้จำชื่อตนเอง ตอบคำถามอย่างเป็นมิตร สุภาพ และช่วยเหลือผู้ใช้งานอย่างเต็มที่เสมอ"
).strip()

intents = discord.Intents.default()
cache_flags = discord.MemberCacheFlags.none()

bot = commands.Bot(
    command_prefix="?",
    intents=intents,
    member_cache_flags=cache_flags,
    max_messages=None,
    help_command=None
)

@bot.event
async def on_ready():
    print(f"🤖 Dedicated AI Bot Connected: {bot.user}")
    print(f"AI Endpoint Target: {AI_ENDPOINT}")
    print(f"AI Model Name Target: {MODEL_NAME}")
    print(f"AI Persona System Prompt: {SYSTEM_PROMPT}")
    try:
        for guild in bot.guilds:
            bot.tree.clear_commands(guild=guild)
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            print(f"Synced {len(synced)} slash command cleanly for AI bot in {guild.name}")
    except Exception as e:
        print(f"Failed sync: {e}")
    gc.collect()
    await bot.change_presence(activity=discord.Game(name="🤖 พิมพ์ /ask เพื่อคุยกับ AI"))

# --- Slash Command เพียงตัวเดียว: /ask (รองรับ System Prompt จำชื่อบอท) ---
@bot.tree.command(name="ask", description="ถามคำถามคุยกับ AI อัตโนมัติ")
async def slash_ask(interaction: discord.Interaction, question: str):
    await interaction.response.defer()
    headers = {"Content-Type": "application/json"}
    if NINEROUTER_KEY:
        headers["Authorization"] = f"Bearer {NINEROUTER_KEY}"
    
    # ใส่ System Prompt กำหนดบุคลิกและชื่อของบอท
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question}
    ]
    
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
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
    gc.collect()

if __name__ == "__main__":
    if not TOKEN:
        print("Error: Please set AI_DISCORD_TOKEN in .env")
    else:
        bot.run(TOKEN)
