import sys
import os
import gc
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
    msg = f"Admin Bot connected: {bot.user} - Clearing all slash commands..."
    print(msg)
    write_log(msg)
    
    # ล้างคำสั่ง Slash Commands ทั้งหมดของ Admin Bot ออก 100%
    bot.tree.clear_commands(guild=None)
    for guild in bot.guilds:
        bot.tree.clear_commands(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        print(f"Cleared all slash commands for {guild.name} (Remaining: {len(synced)})")
        
    await bot.tree.sync()
    gc.collect()
    await bot.change_presence(activity=discord.Game(name="ระบบ Admin (ล้างคำสั่งทั้งหมด)"))

if __name__ == "__main__":
    if not TOKEN or TOKEN == "your_bot_token_here":
        print("Error: Please set DISCORD_TOKEN in .env file")
    else:
        bot.run(TOKEN)
