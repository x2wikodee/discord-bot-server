import sys
import os
import gc
import asyncio
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from datetime import datetime, timezone

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
LOG_FILE_PATH = os.path.join(os.path.dirname(__file__), "bot.log")

def write_log(message: str):
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{now}] {message}\n"
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception:
        pass

intents = discord.Intents.default()
intents.message_content = True

cache_flags = discord.MemberCacheFlags.none()

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ ยืนยันตัวตนเข้าเซิร์ฟเวอร์", style=discord.ButtonStyle.green, custom_id="verify_member_button")
    async def verify_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member_role = discord.utils.get(guild.roles, name="Member") or discord.utils.get(guild.roles, name="สมาชิก")
        
        if not member_role:
            member_role = await guild.create_role(name="Member", color=discord.Color.blue())

        if member_role in interaction.user.roles:
            await interaction.response.send_message("ℹ️ คุณได้ทำการยืนยันตัวตนและเป็นสมาชิกเรียบร้อยแล้ว!", ephemeral=True)
            return

        try:
            await interaction.user.add_roles(member_role)
            await interaction.response.send_message(
                f"🎉 **ยืนยันตัวตนสำเร็จ!**\n"
                f"ปลดล็อกยศ **{member_role.name}** และเปิดการมองเห็นช่องพูดคุยทั้งหมดเรียบร้อยแล้วครับ!",
                ephemeral=True
            )
            write_log(f"Verified user: {interaction.user}")
        except Exception as e:
            await interaction.response.send_message(f"❌ เกิดข้อผิดพลาดในการมอบยศ: {e}", ephemeral=True)

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    member_cache_flags=cache_flags,
    max_messages=None,
    help_command=None
)

# --- ระบบวนลูปตรวจสอบ ลบข้อความอัตโนมัติหากไม่มีคนใช้งานในช่อง 🤖︱ᴀɪ-ᴄʜᴀᴛ เกิน 1 ชั่วโมง ---
@tasks.loop(minutes=5)
async def auto_clean_inactive_ai_chat():
    await bot.wait_until_ready()
    for guild in bot.guilds:
        channel = None
        for ch in guild.text_channels:
            if "ai-chat" in ch.name.lower() or "ᴀɪ-ᴄʜᴀᴛ" in ch.name:
                channel = ch
                break

        if not channel:
            continue

        try:
            async for last_msg in channel.history(limit=1):
                now = datetime.now(timezone.utc)
                diff = now - last_msg.created_at
                # หากไม่มีคนใช้งานหรือส่งข้อความนานเกิน 1 ชั่วโมง (3600 วินาที)
                if diff.total_seconds() > 3600:
                    # ลบข้อความย้อนหลังทั้งหมด โดยเว้นการ์ดคู่มือที่ปักหมุดไว้ (pinned)
                    deleted = await channel.purge(limit=100, check=lambda m: not m.pinned)
                    if deleted:
                        write_log(f"Auto-cleaned {len(deleted)} inactive messages in {channel.name} (Idle > 1 hour)")
        except Exception as e:
            write_log(f"Failed auto-clean inactive channel: {e}")

@bot.event
async def on_ready():
    bot.add_view(VerifyView())
    msg = f"Admin Bot connected: {bot.user} - Strict /ask & 1h Idle Auto-clean active!"
    print(msg)
    write_log(msg)
    
    bot.tree.clear_commands(guild=None)
    await bot.tree.sync(guild=None)
    
    for guild in bot.guilds:
        bot.tree.clear_commands(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        print(f"Cleared all slash commands for Admin bot in {guild.name} (Remaining: {len(synced)})")
        
    if not auto_clean_inactive_ai_chat.is_running():
        auto_clean_inactive_ai_chat.start()
        
    gc.collect()
    await bot.change_presence(activity=discord.Game(name="🛡️ ระบบ Auto-Clean ช่อง AI (1 ชม. ไม่มีคนใช้)"))

# --- ระบบ Auto-Delete ข้อความธรรมดาของผู้ใช้ในช่อง 🤖︱ᴀɪ-ᴄʜᴀᴛ (ยกเว้นข้อความจากบอท) ---
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    ch_name = message.channel.name.lower()
    if "ai-chat" in ch_name or "ᴀɪ-ᴄʜᴀᴛ" in message.channel.name:
        try:
            await message.delete()
            write_log(f"Auto-mod deleted non-slash user message from {message.author} in {message.channel.name}")
            warn_msg = await message.channel.send(
                f"⚠️ {message.author.mention} **โปรดใช้คำสั่ง `/ask [คำถามของคุณ]` เพื่อคุยกับ AI เท่านั้นครับ!**"
            )
            await asyncio.sleep(5)
            await warn_msg.delete()
        except Exception as e:
            write_log(f"Failed auto-mod delete: {e}")

    await bot.process_commands(message)

if __name__ == "__main__":
    if not TOKEN or TOKEN == "your_bot_token_here":
        print("Error: Please set DISCORD_TOKEN in .env file")
    else:
        bot.run(TOKEN)
