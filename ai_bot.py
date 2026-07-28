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

# อ่านชื่อโมเดลจาก .env (ค่าเริ่มต้นใช้ gpt-3.5-turbo)
MODEL_NAME = os.getenv("AI_MODEL_NAME", "gpt-3.5-turbo").strip()

intents = discord.Intents.default()
try:
    intents.message_content = True
except Exception:
    pass

bot = commands.Bot(command_prefix="?", intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f"🤖 Dedicated AI Bot Connected: {bot.user}")
    print(f"AI Endpoint Target: {AI_ENDPOINT}")
    print(f"AI Model Name Target: {MODEL_NAME}")
    try:
        for guild in bot.guilds:
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
    except Exception as e:
        print(f"Failed sync: {e}")
    await bot.change_presence(activity=discord.Game(name="🤖 คุยตอบ AI 24 ชม. ผ่าน Cloud"))

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    c_name = message.channel.name.lower()
    is_mentioned = bot.user in message.mentions
    is_ai_channel = "ai-chat" in c_name or "aichat" in c_name or "ᴀɪ-ᴄʜᴀᴛ" in message.channel.name

    if is_mentioned or is_ai_channel:
        clean_content = message.content.replace(f"<@{bot.user.id}>", "").strip()
        if not clean_content:
            clean_content = "สวัสดีครับ"

        async with message.channel.typing():
            headers = {"Content-Type": "application/json"}
            if NINEROUTER_KEY:
                headers["Authorization"] = f"Bearer {NINEROUTER_KEY}"
            payload = {
                "model": MODEL_NAME,
                "messages": [{"role": "user", "content": clean_content}],
                "stream": False
            }
            try:
                res = requests.post(AI_ENDPOINT, json=payload, headers=headers, timeout=60)
                if res.status_code == 200:
                    reply = res.json()["choices"][0]["message"]["content"]
                    await message.reply(reply[:2000])
                else:
                    await message.reply(f"❌ AI Status Error ({res.status_code}): {res.text[:150]}")
            except Exception as e:
                await message.reply(f"❌ AI Connection Error: {e}")

    await bot.process_commands(message)

# --- Slash Command: /ask ---
@bot.tree.command(name="ask", description="ถามคำถามคุยกับ AI อัตโนมัติ 24 ชม.")
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
