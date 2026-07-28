import sys
import os
import json
import gc
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
LOG_FILE_PATH = os.path.join(os.path.dirname(__file__), "bot.log")
BACKUP_FILE_PATH = os.path.join(os.path.dirname(__file__), "server_backup.json")

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

def is_slash_guild_owner():
    async def predicate(interaction: discord.Interaction):
        if interaction.guild and interaction.guild.owner_id == interaction.user.id:
            return True
        await interaction.response.send_message("⚠️ You do not have permission to use this command. (Server Owner only)", ephemeral=True)
        return False
    return app_commands.check(predicate)

@bot.event
async def on_ready():
    bot.add_view(VerifyView())
    msg = f"Admin Bot connected: {bot.user}"
    print(msg)
    write_log(msg)
    try:
        for guild in bot.guilds:
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
    except Exception as e:
        print(f"Failed sync: {e}")
    gc.collect()
    await bot.change_presence(activity=discord.Game(name="พิมพ์ / เพื่อใช้งานคำสั่ง"))

# --- 8 Core Slash Commands ---
@bot.tree.command(name="help", description="ดูคำสั่งทั้งหมดของ Admin Bot")
async def slash_help(interaction: discord.Interaction):
    embed = discord.Embed(title="👑 Admin Bot - คำสั่งจัดการเซิร์ฟเวอร์", color=discord.Color.gold())
    embed.add_field(name="1. /setup_bypass_guide", value="ส่งและปักหมุดการ์ดคู่มือใช้งาน Zen Bypass ในช่อง ⚡︱ʙʏᴘᴀss", inline=False)
    embed.add_field(name="2. /organize_existing_server", value="ย้ายจัดระเบียบช่องเดิมเป็น Smallcaps และรวม 15 ฟีดขยะเหลือ 4 ช่องหลัก", inline=False)
    embed.add_field(name="3. /setup_verify", value="ส่งการ์ดปุ่มกดรับยศยืนยันตัวตนในช่อง ✅︱ᴠᴇʀɪꜰʏ", inline=False)
    embed.add_field(name="4. /setup_bot_roles", value="สร้างและมอบยศเฉพาะตัวให้บอททุกตัว (1 บอท : 1 ยศ)", inline=False)
    embed.add_field(name="5. /clean_webhooks", value="ลบและเคลียร์ Webhooks ขยะที่ค้างซ้ำซ้อนออกทั้งหมด", inline=False)
    embed.add_field(name="6. /backup_server", value="สำรองข้อมูลโครงสร้างเซิร์ฟเวอร์ปัจจุบันลง server_backup.json", inline=False)
    embed.add_field(name="7. /restore_server", value="กู้คืนข้อมูลโครงสร้างเซิร์ฟเวอร์จากไฟล์สำรอง", inline=False)
    embed.add_field(name="8. /inspect_server", value="สแกนละเอียดทุกสิทธิ์ ยศ Webhooks บันทึกลง bot.log", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# --- Slash Command: /setup_bypass_guide ---
@bot.tree.command(name="setup_bypass_guide", description="ส่งและปักหมุดการ์ดคู่มือวิธีใช้งาน Zen Bypass ในช่อง ⚡︱ʙʏᴘᴀss")
@is_slash_guild_owner()
async def slash_setup_bypass_guide(interaction: discord.Interaction):
    channel = interaction.channel

    embed = discord.Embed(
        title="⚡ คู่มือการใช้งาน ZEN BYPASS BOT",
        description=(
            "📌 **วิธีใช้งานคำสั่งปลดล็อกลิงก์:**\n"
            "👉 พิมพ์คำสั่ง **`/bypass url: [ใส่ลิงก์สั้น/ลิงก์ติดโฆษณา]`**\n\n"
            "✨ **ตัวอย่างการพิมพ์:**\n"
            "`/bypass url: https://link-to-unlock.com/xyz`\n\n"
            "🛡️ **คำแนะนำ:**\n"
            "• ผลลัพธ์จะส่งกลับให้คุณทันทีแบบส่วนตัว (Only you can see this)\n"
            "• ช่วยปลดล็อกลิงก์โฆษณา ลิงก์ย่อ และลิงก์ติดดาวน์โหลดได้อย่างรวดเร็ว"
        ),
        color=discord.Color.green()
    )
    embed.set_footer(text="ระบบปลดล็อกลิงก์อัตโนมัติด้วย Zen Bypass")

    msg = await channel.send(embed=embed)
    try:
        await msg.pin()
    except Exception:
        pass

    await interaction.response.send_message(
        f"✅ **ส่งการ์ดคู่มือและปักหมุดวิธีใช้งาน Zen Bypass ในช่อง {channel.mention} เรียบร้อยแล้ว!**",
        ephemeral=True
    )

@bot.tree.command(name="organize_existing_server", description="รวม 15 ช่องฟีดเดิมเหลือ 4 ช่องหลัก และจัดดีไซน์ Smallcaps สวยงาม 100%")
@is_slash_guild_owner()
async def slash_organize_existing_server(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    creator_role = discord.utils.get(guild.roles, name="ผู้สร้าง") or await guild.create_role(name="ผู้สร้าง", color=discord.Color.gold())
    dev_role = discord.utils.get(guild.roles, name="Dev") or await guild.create_role(name="Dev", color=discord.Color.purple())

    cats = {}
    cat_definitions = [
        ("📌︱ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ & ᴡᴇʟᴄᴏᴍᴇ", False),
        ("💬︱ᴄᴏᴍᴍᴜɴɪᴛʏ", False),
        ("🎮︱ꜰᴇᴇᴅꜱ & ᴜᴘᴅᴀᴛᴇꜱ", False),
        ("⚽︱ꜰᴏᴏᴛʙᴀʟʟ", False),
        ("🎁︱ɢɪᴠᴇᴀᴡᴀʏꜱ & ʀᴇᴡᴀʀᴅꜱ", False),
        ("⚙️︱ʙᴏᴛꜱ & ᴄᴏᴍᴍᴀɴᴅꜱ", False),
        ("🔒︱ꜱᴛᴀꜰꜰ ᴏɴʟʏ", True)
    ]

    for name, is_staff in cat_definitions:
        category = discord.utils.get(guild.categories, name=name)
        if is_staff:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                creator_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                dev_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_channels=True)
            }
        else:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_channels=True)
            }

        if not category:
            category = await guild.create_category(name, overwrites=overwrites)
        else:
            await category.edit(overwrites=overwrites)
        cats[name] = category

    feed_cat = cats["🎮︱ꜰᴇᴇᴅꜱ & ᴜᴘᴅᴀᴛᴇꜱ"]

    game_news_ch = discord.utils.get(feed_cat.text_channels, name="🎮︱ɢᴀᴍᴇ-ɴᴇᴡꜱ") or await feed_cat.create_text_channel("🎮︱ɢᴀᴍᴇ-ɴᴇᴡꜱ")
    free_games_ch = discord.utils.get(feed_cat.text_channels, name="📦︱ꜰʀᴇᴇ-ɢᴀᴍᴇꜱ") or await feed_cat.create_text_channel("📦︱ꜰʀᴇᴇ-ɢᴀᴍᴇꜱ")
    ai_updates_ch = discord.utils.get(feed_cat.text_channels, name="🤖︱ᴀɪ-ᴜᴘᴅᴀᴛᴇꜱ") or await feed_cat.create_text_channel("🤖︱ᴀɪ-ᴜᴘᴅᴀᴛᴇꜱ")
    driver_updates_ch = discord.utils.get(feed_cat.text_channels, name="🟢︱ᴅʀɪᴠᴇʀ-ᴜᴘᴅᴀᴛᴇꜱ") or await feed_cat.create_text_channel("🟢︱ᴅʀɪᴠᴇʀ-ᴜᴘᴅᴀᴛᴇꜱ")

    for channel in list(guild.channels):
        if isinstance(channel, discord.CategoryChannel):
            continue

        c_name = channel.name.lower()

        if ("wuwa" in c_name or "minecraft" in c_name or "counter-strike" in c_name or "overwatch" in c_name or "valorant" in c_name) and channel.id != game_news_ch.id:
            try: await channel.delete()
            except Exception: pass
        elif ("steam-free" in c_name or "epic-free" in c_name or "gog-free" in c_name) and channel.id != free_games_ch.id:
            try: await channel.delete()
            except Exception: pass
        elif ("chatgpt" in c_name or "gemini" in c_name or "claude" in c_name or "openclaw" in c_name) and channel.id != ai_updates_ch.id:
            try: await channel.delete()
            except Exception: pass
        elif ("nvidia" in c_name or "amd-radeon" in c_name or "intel-arc" in c_name) and channel.id != driver_updates_ch.id:
            try: await channel.delete()
            except Exception: pass

    rename_map = {
        "rules": "📜︱ʀᴜʟᴇꜱ", "faq": "❓︱ꜰᴀǫ", "welcome": "👋︱ᴡᴇʟᴄᴏᴍᴇ", "goodbye": "🕊️︱ɢᴏᴏᴅʙʏᴇ",
        "announcements": "📢︱ᴀɴɴᴏᴜɴᴄᴇᴍᴇɴᴛꜱ", "general-chat": "💬︱ɢᴇɴᴇʀᴀʟ-ᴄʜᴀᴛ", "image-chat": "🖼︱ᴍᴇᴅɪᴀ-ꜱʜᴀʀɪɴɢ",
        "video-clips": "🎬︱ᴠɪᴅᴇᴏ-ᴄʟɪᴘꜱ", "works": "📚︱ᴡᴏʀᴋꜱ", "meme-center": "🎭︱ᴍᴇᴍᴇ-ᴄᴇɴᴛᴇʀ",
        "la-liga": "🇪🇸︱ʟᴀ-ʟɪɢᴀ", "premier-league": "🏴󠁧󠁢󠁥󠁮󠁧󠁿︱ᴘʀᴇᴍɪᴇʀ-ʟᴇᴀɢᴜᴇ", "uefa-champions-league": "🏆︱ᴄʜᴀᴍᴘɪᴏɴꜱ-ʟᴇᴀɢᴜᴇ",
        "world-cup": "⚽︱ᴡᴏʀʟᴅ-ᴄᴜᴘ", "modded-apks": "📦︱ᴍᴏᴅᴅᴇᴅ-ᴀᴘᴋꜱ", "freemium": "💎︱ꜰʀᴇᴇᴍɪᴜᴍ",
        "bot-cmds": "🤖︱ʙᴏᴛ-ᴄᴏᴍᴍᴀɴᴅꜱ", "ai-chat": "🤖︱ᴀɪ-ᴄʜᴀᴛ", "bypass": "⚡︱ʙʏᴘᴀss", "moderator-only": "🛠︱ᴍᴏᴅ-ʟᴏɢꜱ"
    }

    for channel in guild.channels:
        if isinstance(channel, discord.CategoryChannel):
            continue

        c_name = channel.name.lower()
        new_name = None

        for key, val in rename_map.items():
            if key in c_name:
                new_name = val
                break

        if "moderator-only" in c_name or "mod-log" in c_name or "staff" in c_name:
            await channel.edit(category=cats["🔒︱ꜱᴛᴀꜰꜰ ᴏɴʟʏ"], name=new_name or channel.name)
        elif "rules" in c_name or "faq" in c_name or "welcome" in c_name or "announcement" in c_name or "goodbye" in c_name:
            await channel.edit(category=cats["📌︱ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ & ᴡᴇʟᴄᴏᴍᴇ"], name=new_name or channel.name)
        elif "general-chat" in c_name or "image-chat" in c_name or "video-clips" in c_name or "works" in c_name or "meme" in c_name:
            await channel.edit(category=cats["💬︱ᴄᴏᴍᴍᴜɴɪᴛʏ"], name=new_name or channel.name)
        elif "liga" in c_name or "league" in c_name or "cup" in c_name or "football" in c_name or "ball" in c_name:
            await channel.edit(category=cats["⚽︱ꜰᴏᴏᴛʙᴀʟʟ"], name=new_name or channel.name)
        elif "modded-apks" in c_name or "freemium" in c_name or "giveaway" in c_name:
            await channel.edit(category=cats["🎁︱ɢɪᴠᴇᴀᴡᴀʏꜱ & ʀᴇᴡᴀʀᴅꜱ"], name=new_name or channel.name)
        elif "bot-cmds" in c_name or "bot-commands" in c_name or "ai-chat" in c_name or "bot-status" in c_name or "bypass" in c_name:
            await channel.edit(category=cats["⚙️︱ʙᴏᴛꜱ & ᴄᴏᴍᴍᴀɴᴅꜱ"], name=new_name or channel.name)

    gc.collect()
    await interaction.followup.send("✅ **ปรับปรุงโครงสร้างเซิร์ฟเวอร์เรียบร้อย!**", ephemeral=True)

@bot.tree.command(name="setup_verify", description="ส่งการ์ดปุ่มกดรับยศยืนยันตัวตนอัตโนมัติในช่อง ✅︱ᴠᴇʀɪꜰʏ")
@is_slash_guild_owner()
async def slash_setup_verify(interaction: discord.Interaction):
    guild = interaction.guild

    category = discord.utils.get(guild.categories, name="📌︱ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ & ᴡᴇʟᴄᴏᴍᴇ") or await guild.create_category("📌︱ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ & ᴡᴇʟᴄᴏᴍᴇ")

    channel = None
    for ch in guild.text_channels:
        if "verify" in ch.name.lower() or "ᴠᴇʀɪꜰʏ" in ch.name:
            channel = ch
            break

    if not channel:
        channel = await category.create_text_channel("✅︱ᴠᴇʀɪꜰʏ")
    else:
        await channel.edit(category=category, name="✅︱ᴠᴇʀɪꜰʏ")

    embed = discord.Embed(
        title="✅ ระบบยืนยันตัวตน (VERIFICATION SYSTEM)",
        description="กรุณากดปุ่ม **`✅ ยืนยันตัวตนเข้าเซิร์ฟเวอร์`** ด้านล่างนี้เพื่อปลดล็อกยศสมาชิก (`Member`)",
        color=discord.Color.green()
    )

    view = VerifyView()
    msg = await channel.send(embed=embed, view=view)
    try: await msg.pin()
    except Exception: pass

    await interaction.response.send_message(f"✅ **ติดตั้งระบบปุ่มกด Verify เรียบร้อยแล้ว!**", ephemeral=True)

@bot.tree.command(name="setup_bot_roles", description="สร้างและมอบยศเฉพาะตัวให้บอทแต่ละตัวในเซิร์ฟเวอร์ (1 บอท : 1 ยศ)")
@is_slash_guild_owner()
async def slash_setup_bot_roles(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    colors = [discord.Color.gold(), discord.Color.green(), discord.Color.purple(), discord.Color.orange(), discord.Color.blue()]

    for idx, member in enumerate(guild.members):
        if not member.bot: continue

        role_name = f"🤖︱{member.display_name.upper()}"
        role = discord.utils.get(guild.roles, name=role_name) or await guild.create_role(name=role_name, color=colors[idx % len(colors)], hoist=True)

        if role not in member.roles:
            try: await member.add_roles(role)
            except Exception: pass

    gc.collect()
    await interaction.followup.send("✅ **สร้างและแจกยศเฉพาะตัวให้บอทสำเร็จ!**", ephemeral=True)

@bot.tree.command(name="clean_webhooks", description="ลบและเคลียร์ Webhooks ขยะที่ค้างซ้ำซ้อนในดิสคอร์ด")
@is_slash_guild_owner()
async def slash_clean_webhooks(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    try:
        webhooks = await guild.webhooks()
        deleted_count = 0
        seen_names = set()

        for wh in webhooks:
            key = f"{wh.name}_{wh.channel_id}"
            if key in seen_names or not wh.name or wh.name == "PatchBot":
                try:
                    await wh.delete()
                    deleted_count += 1
                except Exception: pass
            else:
                seen_names.add(key)

        await interaction.followup.send(f"🧹 **เคลียร์ Webhooks ขยะสำเร็จ! ({deleted_count} ตัว)**", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

@bot.tree.command(name="backup_server", description="สำรองข้อมูลโครงสร้างเซิร์ฟเวอร์ปัจจุบัน 100%")
@is_slash_guild_owner()
async def slash_backup_server(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    backup_data = {"guild_id": guild.id, "guild_name": guild.name, "categories": []}
    for cat in guild.categories:
        cat_data = {"name": cat.name, "position": cat.position, "channels": [ch.name for ch in cat.channels]}
        backup_data["categories"].append(cat_data)

    try:
        with open(BACKUP_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
        await interaction.followup.send("✅ **สำรองข้อมูลโครงสร้างสำเร็จเรียบร้อย!**", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

@bot.tree.command(name="restore_server", description="กู้คืนข้อมูลโครงสร้างเซิร์ฟเวอร์จากไฟล์สำรอง")
@is_slash_guild_owner()
async def slash_restore_server(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    if not os.path.exists(BACKUP_FILE_PATH):
        await interaction.followup.send("❌ ไม่พบไฟล์สำรอง server_backup.json", ephemeral=True)
        return

    try:
        with open(BACKUP_FILE_PATH, "r", encoding="utf-8") as f:
            backup_data = json.load(f)

        for cat_data in backup_data.get("categories", []):
            cat_name = cat_data["name"]
            category = discord.utils.get(guild.categories, name=cat_name) or await guild.create_category(cat_name)
            for ch_name in cat_data.get("channels", []):
                if not discord.utils.get(guild.channels, name=ch_name):
                    await category.create_text_channel(ch_name)

        await interaction.followup.send("🔄 **กู้คืนข้อมูลจากไฟล์สำรองสำเร็จ!**", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

@bot.tree.command(name="inspect_server", description="สแกนทุกสิ่งทุกอย่างในเซิร์ฟเวอร์ และบันทึกข้อมูลลง bot.log")
@is_slash_guild_owner()
async def slash_inspect_server(interaction: discord.Interaction):
    await interaction.response.defer()
    guild = interaction.guild

    scan_lines = [f"GUILD: {guild.name} (ID: {guild.id})", f"Members: {guild.member_count}", f"Roles: {len(guild.roles)}"]
    write_log("\n".join(scan_lines))

    await interaction.followup.send("📊 **สแกนโครงสร้างเซิร์ฟเวอร์บันทึกลง bot.log เรียบร้อยแล้ว!**")

if __name__ == "__main__":
    if not TOKEN or TOKEN == "your_bot_token_here":
        print("Error: Please set DISCORD_TOKEN in .env file")
    else:
        bot.run(TOKEN)
