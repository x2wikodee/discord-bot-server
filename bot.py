import sys
import os
import re
import gc
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
LOG_FILE_PATH = os.path.join(os.path.dirname(__file__), "bot.log")

def write_log(message: str):
    try:
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{now}] {message}\n"
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception:
        pass

# Regex สำหรับตรวจจับ Custom Emojis (<:name:id>, <a:name:id>) และ Unicode Emojis ทั้งหมด
EMOJI_REGEX = re.compile(
    r"<a?:[a-zA-Z0-9_]+:[0-9]+>|"
    r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002600-\U000027BF\U0001F900-\U0001F9FF\U0001FA70-\U0001FAFF]"
)

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

@bot.event
async def on_ready():
    bot.add_view(VerifyView())
    msg = f"Admin Bot connected: {bot.user} - Auto-mod for #🤖︱ᴀɪ-ᴄʜᴀᴛ active!"
    print(msg)
    write_log(msg)
    
    bot.tree.clear_commands(guild=None)
    await bot.tree.sync(guild=None)
    
    for guild in bot.guilds:
        bot.tree.clear_commands(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        print(f"Cleared all slash commands for Admin bot in {guild.name} (Remaining: {len(synced)})")
        
    gc.collect()
    await bot.change_presence(activity=discord.Game(name="🛡️ ระบบ Auto-Mod ป้องกันขยะในช่อง AI"))

# --- ระบบ Auto-Delete รูปภาพ / สติกเกอร์ / อิโมจิ ในช่อง 🤖︱ᴀɪ-ᴄʜᴀᴛ ---
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    ch_name = message.channel.name.lower()
    if "ai-chat" in ch_name or "ᴀɪ-ᴄʜᴀᴛ" in message.channel.name:
        has_attachment = bool(message.attachments)
        has_sticker = bool(message.stickers)
        has_emoji = bool(EMOJI_REGEX.search(message.content))

        if has_attachment or has_sticker or has_emoji:
            try:
                await message.delete()
                write_log(f"Auto-mod deleted prohibited content from {message.author} in {message.channel.name}")
                warn_msg = await message.channel.send(
                    f"⚠️ {message.author.mention} **ช่องนี้อนุญาตให้ส่งเฉพาะข้อความตัวหนังสือเท่านั้น! (ลบรูป/สติกเกอร์/อิโมจิอัตโนมัติ)**"
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
