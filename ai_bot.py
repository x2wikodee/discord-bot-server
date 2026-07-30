import sys
import os
import gc
import discord
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

MODEL_NAME = os.getenv("AI_MODEL_NAME", "deepseek/deepseek-v4-pro").strip()

SYSTEM_PROMPT = os.getenv(
    "AI_SYSTEM_PROMPT",
    "คุณคือ AI Assistant บอทประจำเซิร์ฟเวอร์ดิสคอร์ด ให้จำชื่อตนเอง ตอบคำถามอย่างเป็นมิตร สุภาพ และช่วยเหลือผู้ใช้งานอย่างเต็มที่เสมอ"
).strip()

intents = discord.Intents.default()
intents.message_content = True

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
    gc.collect()
    await bot.change_presence(activity=discord.Game(name="🤖 พิมพ์คุยในช่อง AI ได้เลยทันที (ไม่ต้องใช้ /)"))

# --- พิมพ์ข้อความในช่อง 🤖︱ᴀɪ-ᴄʜᴀᴛ คุยกับ AI ได้ทันทีโดยไม่ต้องใช้ / ---
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    ch_name = message.channel.name.lower()
    if "ai-chat" in ch_name or "ᴀɪ-ᴄʜᴀᴛ" in message.channel.name:
        async with message.channel.typing():
            headers = {"Content-Type": "application/json"}
            if NINEROUTER_KEY:
                headers["Authorization"] = f"Bearer {NINEROUTER_KEY}"
            
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message.content}
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
                    await message.reply(reply[:2000], mention_author=False)
                else:
                    await message.channel.send(f"❌ AI Status Error ({res.status_code}): {res.text[:150]}")
            except Exception as e:
                await message.channel.send(f"❌ AI Error: {e}")
            gc.collect()

    await bot.process_commands(message)

if __name__ == "__main__":
    if not TOKEN:
        print("Error: Please set AI_DISCORD_TOKEN in .env")
    else:
        bot.run(TOKEN)
