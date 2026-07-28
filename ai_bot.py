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
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            print(f"Synced {len(synced)} slash commands for AI bot in {guild.name}")
    except Exception as e:
        print(f"Failed sync: {e}")
    await bot.change_presence(activity=discord.Game(name="🤖 พิมพ์ /ask เพื่อคุยกับ AI"))

# --- Slash Command 1: /setup_aichat (ส่งการ์ดคู่มือเฉพาะคำสั่ง /ask) ---
@bot.tree.command(name="setup_aichat", description="ส่งและปักหมุดการ์ดคู่มือวิธีใช้งาน AI Chat ในช่อง 🤖︱ᴀɪ-ᴄʜᴀᴛ")
async def slash_setup_aichat(interaction: discord.Interaction):
    guild = interaction.guild
    channel = interaction.channel

    embed = discord.Embed(
        title="🤖 คู่มือการใช้งาน AI CHAT BOT (24/7 CLOUD AI)",
        description=(
            "ยินดีต้อนรับสู่ระบบปัญญาประดิษฐ์ **AI Assistant 24 ชั่วโมง**!\n"
            "ระบบขับเคลื่อนด้วยโมเดล **MiniMax M3** ทำงานผ่านคลาวด์บน AWS EC2 ตลอด 24 ชม.\n\n"
            "📌 **วิธีใช้งานคำสั่ง AI:**\n"
            "👉 พิมพ์คำสั่ง **`/ask [คำถามของคุณ]`** ➡️ เพื่อส่งคำถามให้ AI ตอบทันที\n\n"
            "✨ **ความสามารถของ AI:**\n"
            "• ตอบคำถามทั่วไป เขียนโปรแกรม แปลภาษา สรุปเนื้อหา\n"
            "• ให้คำแนะนำและแก้ไขข้อผิดพลาดทางเทคนิคได้ทันที"
        ),
        color=discord.Color.blue()
    )
    embed.set_footer(text="ระบบ AI Assistant 24/7 Automatic Response")

    msg = await channel.send(embed=embed)
    try:
        await msg.pin()
    except Exception:
        pass

    await interaction.response.send_message(
        f"✅ **ส่งการ์ดคู่มือและปักหมุดวิธีใช้งาน AI ในช่อง {channel.mention} เรียบร้อยแล้ว!**",
        ephemeral=True
    )

# --- Slash Command 2: /ask (คำสั่งหลักตัวเดียว) ---
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
