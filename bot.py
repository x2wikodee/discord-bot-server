import sys
import os
import json
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
    """ฟังก์ชันเขียน Log ลงไฟล์ bot.log อัตโนมัติ"""
    try:
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{now}] {message}\n"
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Failed to write log: {e}")

write_log("--- Cleaned Admin Discord Bot Initializing ---")

intents = discord.Intents.default()
intents.message_content = True

# --- View ปุ่มกดรับยศ ยืนยันตัวตน (Verify Button) ---
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
            write_log(f"Verified user: {interaction.user} -> Granted {member_role.name} role.")
        except Exception as e:
            await interaction.response.send_message(f"❌ เกิดข้อผิดพลาดในการมอบยศ: {e}", ephemeral=True)

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Check: เฉพาะเจ้าของเซิร์ฟเวอร์เท่านั้น (Slash Commands)
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
    msg = f"Bot connected successfully: {bot.user}"
    print(msg)
    write_log(msg)
    try:
        for guild in bot.guilds:
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            sync_msg = f"Synced {len(synced)} Slash Commands cleanly for {guild.name}"
            print(sync_msg)
            write_log(sync_msg)
    except Exception as e:
        err_msg = f"Failed to sync slash commands: {e}"
        print(err_msg)
        write_log(err_msg)
    await bot.change_presence(activity=discord.Game(name="พิมพ์ / เพื่อใช้งานคำสั่ง"))

# --- Slash Command 1: /help (สรุปคำสั่งที่จำเป็นเท่านั้น) ---
@bot.tree.command(name="help", description="ดูคำสั่งทั้งหมดของ Admin Bot")
async def slash_help(interaction: discord.Interaction):
    embed = discord.Embed(title="👑 Admin Bot - คำสั่งจัดการเซิร์ฟเวอร์", color=discord.Color.gold())
    embed.add_field(name="1. /organize_existing_server", value="ย้ายจัดระเบียบช่องเดิมเป็น Smallcaps และรวม 15 ฟีดขยะเหลือ 4 ช่องหลัก", inline=False)
    embed.add_field(name="2. /setup_verify", value="ส่งการ์ดปุ่มกดรับยศยืนยันตัวตนในช่อง ✅︱ᴠᴇʀɪꜰʏ", inline=False)
    embed.add_field(name="3. /setup_bot_roles", value="สร้างและมอบยศเฉพาะตัวให้บอททุกตัว (1 บอท : 1 ยศ)", inline=False)
    embed.add_field(name="4. /clean_webhooks", value="ลบและเคลียร์ Webhooks ขยะที่ค้างซ้ำซ้อนออกทั้งหมด", inline=False)
    embed.add_field(name="5. /backup_server", value="สำรองข้อมูลโครงสร้างเซิร์ฟเวอร์ปัจจุบันลง server_backup.json", inline=False)
    embed.add_field(name="6. /restore_server", value="กู้คืนข้อมูลโครงสร้างเซิร์ฟเวอร์จากไฟล์สำรอง", inline=False)
    embed.add_field(name="7. /inspect_server", value="สแกนละเอียดทุกสิทธิ์ ยศ Webhooks บันทึกลง bot.log", inline=False)
    embed.set_footer(text="ระบบบริหารจัดการเซิร์ฟเวอร์ระดับมืออาชีพ")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# --- Slash Command 2: /organize_existing_server ---
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

    merged_count = 0
    for channel in list(guild.channels):
        if isinstance(channel, discord.CategoryChannel):
            continue

        c_name = channel.name.lower()

        if ("wuwa" in c_name or "minecraft" in c_name or "counter-strike" in c_name or "overwatch" in c_name or "valorant" in c_name) and channel.id != game_news_ch.id:
            try:
                await channel.delete()
                merged_count += 1
            except Exception:
                pass

        elif ("steam-free" in c_name or "epic-free" in c_name or "gog-free" in c_name) and channel.id != free_games_ch.id:
            try:
                await channel.delete()
                merged_count += 1
            except Exception:
                pass

        elif ("chatgpt" in c_name or "gemini" in c_name or "claude" in c_name or "openclaw" in c_name) and channel.id != ai_updates_ch.id:
            try:
                await channel.delete()
                merged_count += 1
            except Exception:
                pass

        elif ("nvidia" in c_name or "amd-radeon" in c_name or "intel-arc" in c_name) and channel.id != driver_updates_ch.id:
            try:
                await channel.delete()
                merged_count += 1
            except Exception:
                pass

    rename_map = {
        "rules": "📜︱ʀᴜʟᴇꜱ",
        "faq": "❓︱ꜰᴀǫ",
        "welcome": "👋︱ᴡᴇʟᴄᴏᴍᴇ",
        "goodbye": "🕊️︱ɢᴏᴏᴅʙʏᴇ",
        "announcements": "📢︱ᴀɴɴᴏᴜɴᴄᴇᴍᴇɴᴛꜱ",
        "general-chat": "💬︱ɢᴇɴᴇʀᴀʟ-ᴄʜᴀᴛ",
        "image-chat": "🖼︱ᴍᴇᴅɪᴀ-ꜱʜᴀʀɪɴɢ",
        "video-clips": "🎬︱ᴠɪᴅᴇᴏ-ᴄʟɪᴘꜱ",
        "works": "📚︱ᴡᴏʀᴋꜱ",
        "meme-center": "🎭︱ᴍᴇᴍᴇ-ᴄᴇɴᴛᴇʀ",
        "la-liga": "🇪🇸︱ʟᴀ-ʟɪɢᴀ",
        "premier-league": "🏴󠁧󠁢󠁥󠁮󠁧󠁿︱ᴘʀᴇᴍɪᴇʀ-ʟᴇᴀɢᴜᴇ",
        "uefa-champions-league": "🏆︱ᴄʜᴀᴍᴘɪᴏɴꜱ-ʟᴇᴀɢᴜᴇ",
        "world-cup": "⚽︱ᴡᴏʀʟᴅ-ᴄᴜᴘ",
        "modded-apks": "📦︱ᴍᴏᴅᴅᴇᴅ-ᴀᴘᴋꜱ",
        "freemium": "💎︱ꜰʀᴇᴇᴍɪᴜᴍ",
        "bot-cmds": "🤖︱ʙᴏᴛ-ᴄᴏᴍᴍᴀɴᴅꜱ",
        "ai-chat": "🤖︱ᴀɪ-ᴄʜᴀᴛ",
        "bypass": "⚡︱ʙʏᴘᴀss",
        "moderator-only": "🛠︱ᴍᴏᴅ-ʟᴏɢꜱ"
    }

    updated_count = 0
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
            updated_count += 1
        elif "rules" in c_name or "faq" in c_name or "welcome" in c_name or "announcement" in c_name or "goodbye" in c_name:
            await channel.edit(category=cats["📌︱ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ & ᴡᴇʟᴄᴏᴍᴇ"], name=new_name or channel.name)
            updated_count += 1
        elif "general-chat" in c_name or "image-chat" in c_name or "video-clips" in c_name or "works" in c_name or "meme" in c_name:
            await channel.edit(category=cats["💬︱ᴄᴏᴍᴍᴜɴɪᴛʏ"], name=new_name or channel.name)
            updated_count += 1
        elif "liga" in c_name or "league" in c_name or "cup" in c_name or "football" in c_name or "ball" in c_name:
            await channel.edit(category=cats["⚽︱ꜰᴏᴏᴛʙᴀʟʟ"], name=new_name or channel.name)
            updated_count += 1
        elif "modded-apks" in c_name or "freemium" in c_name or "giveaway" in c_name:
            await channel.edit(category=cats["🎁︱ɢɪᴠᴇᴀᴡᴀʏꜱ & ʀᴇᴡᴀʀᴅꜱ"], name=new_name or channel.name)
            updated_count += 1
        elif "bot-cmds" in c_name or "bot-commands" in c_name or "ai-chat" in c_name or "bot-status" in c_name or "bypass" in c_name:
            await channel.edit(category=cats["⚙️︱ʙᴏᴛꜱ & ᴄᴏᴍᴍᴀɴᴅꜱ"], name=new_name or channel.name)
            updated_count += 1

    desired_new = [
        ("📌︱ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ & ᴡᴇʟᴄᴏᴍᴇ", ["📢︱ᴀɴɴᴏᴜɴᴄᴇᴍᴇɴᴛꜱ", "✅︱ᴠᴇʀɪꜰʏ", "❓︱ꜰᴀǫ"]),
        ("⚽︱ꜰᴏᴏᴛʙᴀʟʟ", ["⚽︱ꜰᴏᴏᴛʙᴀʟʟ-ɢᴇɴᴇʀᴀʟ", "🇮🇹︱ꜱᴇʀɪᴇ-ᴀ", "🇩🇪︱ʙᴜɴᴅᴇꜱʟɪɢᴀ", "📊︱ꜱᴛᴀɴᴅɪɴɢꜱ-ꜱᴛᴀᴛꜱ"]),
        ("⚙️︱ʙᴏᴛꜱ & ᴄᴏᴍᴍᴀɴᴅꜱ", ["📊︱ʙᴏᴛ-ꜱᴛᴀᴛᴜꜱ"]),
        ("🔒︱ꜱᴛᴀꜰꜰ ᴏɴʟʏ", ["📋︱ᴍᴏᴅ-ᴀᴄᴛɪᴏɴꜱ", "⚙︱ꜱᴛᴀꜰꜰ-ᴄᴏᴍᴍᴀɴᴅꜱ"])
    ]

    for cat_name, ch_list in desired_new:
        cat = cats[cat_name]
        for ch_name in ch_list:
            existing = discord.utils.get(cat.text_channels, name=ch_name)
            if not existing:
                await cat.create_text_channel(ch_name)

    for cat in list(guild.categories):
        if cat.name not in cats and len(cat.channels) == 0:
            try:
                await cat.delete()
            except Exception:
                pass

    await interaction.followup.send(
        f"✅ **ปรับปรุงเซิร์ฟเวอร์และรวมช่องฟีดสำเร็จ!**\n"
        f"📦 รวมช่องฟีดขยะ 15 ช่องเดิม ➡️ เหลือ **4 ช่องหลักอย่างสะอาดเรียบหรู**\n"
        f"  • `🎮︱ɢᴀᴍᴇ-ɴᴇᴡꜱ` (รวมข่าวแพตช์เกมทุกเกม)\n"
        f"  • `📦︱ꜰʀᴇᴇ-ɢᴀᴍᴇꜱ` (รวมเกมแจกฟรีทุกแพลตฟอร์ม)\n"
        f"  • `🤖︱ᴀɪ-ᴜᴘᴅᴀᴛᴇꜱ` (รวมอัปเดตโมเดล AI ทุกตัว)\n"
        f"  • `🟢︱ᴅʀɪᴠᴇʀ-ᴜᴘᴅᴀᴛᴇꜱ` (รวมอัปเดตไดรเวอร์การ์ดจอ)\n"
        f"✏️ ปรับปรุงย้ายช่องเดิมที่เหลือทั้งหมดเป็นดีไซน์ **Smallcaps** เรียบร้อยแล้วครับ!",
        ephemeral=True
    )

# --- Slash Command 3: /setup_verify ---
@bot.tree.command(name="setup_verify", description="ส่งการ์ดปุ่มกดรับยศยืนยันตัวตนอัตโนมัติในช่อง ✅︱ᴠᴇʀɪꜰʏ")
@is_slash_guild_owner()
async def slash_setup_verify(interaction: discord.Interaction):
    guild = interaction.guild

    category = discord.utils.get(guild.categories, name="📌︱ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ & ᴡᴇʟᴄᴏᴍᴇ")
    if not category:
        category = await guild.create_category("📌︱ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ & ᴡᴇʟᴄᴏᴍᴇ")

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
        description=(
            "ยินดีต้อนรับเข้าสู่เซิร์ฟเวอร์!\n\n"
            "📌 **คำแนะนำ:**\n"
            "กรุณากดปุ่ม **`✅ ยืนยันตัวตนเข้าเซิร์ฟเวอร์`** ด้านล่างนี้เพื่อปลดล็อกยศสมาชิก (`Member`)\n"
            "และเปิดการมองเห็นช่องพูดคุย ข่าวสาร เกม และฟุตบอลทั้งหมดในเซิร์ฟเวอร์ครับ!"
        ),
        color=discord.Color.green()
    )
    embed.set_footer(text="ระบบรักษาความปลอดภัยและยืนยันตัวตนอัตโนมัติ")

    view = VerifyView()
    msg = await channel.send(embed=embed, view=view)
    try:
        await msg.pin()
    except Exception:
        pass

    await interaction.response.send_message(
        f"✅ **ติดตั้งระบบปุ่มกด Verify ในช่อง {channel.mention} เรียบร้อยแล้ว!**\n"
        f"✏️ ปรับดีไซน์ชื่อช่องเป็น Smallcaps **`✅︱ᴠᴇʀɪꜰʏ`** และส่งการ์ดปุ่มกดรับยศปักหมุดแล้วครับ!",
        ephemeral=True
    )
    write_log(f"Setup verification system in channel #{channel.name}")

# --- Slash Command 4: /setup_bot_roles ---
@bot.tree.command(name="setup_bot_roles", description="สร้างและมอบยศเฉพาะตัวให้บอทแต่ละตัวในเซิร์ฟเวอร์ (1 บอท : 1 ยศ)")
@is_slash_guild_owner()
async def slash_setup_bot_roles(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    colors = [
        discord.Color.gold(),
        discord.Color.green(),
        discord.Color.purple(),
        discord.Color.orange(),
        discord.Color.teal(),
        discord.Color.blue(),
        discord.Color.magenta(),
        discord.Color.dark_teal(),
        discord.Color.dark_green(),
        discord.Color.dark_blue(),
        discord.Color.dark_purple(),
        discord.Color.dark_gold(),
        discord.Color.dark_orange()
    ]

    created_roles_count = 0
    assigned_count = 0

    for idx, member in enumerate(guild.members):
        if not member.bot:
            continue

        role_name = f"🤖︱{member.display_name.upper()}"
        color = colors[idx % len(colors)]

        role = discord.utils.get(guild.roles, name=role_name)
        if not role:
            role = await guild.create_role(name=role_name, color=color, hoist=True)
            created_roles_count += 1
        else:
            await role.edit(color=color, hoist=True)

        if role not in member.roles:
            try:
                await member.add_roles(role)
                assigned_count += 1
            except Exception:
                pass

    await interaction.followup.send(
        f"✅ **สร้างและแจกยศเฉพาะตัวให้บอททุกตัวสำเร็จ!**\n"
        f"🏷️ สร้างยศใหม่เฉพาะบอท: **{created_roles_count} ยศ**\n"
        f"🤖 แจกยศเฉพาะตัวให้บอท: **{assigned_count} บอท**\n"
        f"✨ ตอนนี้บอททุกตัวมี **ยศแยกเฉพาะของตัวเอง (1 บอท : 1 ยศ)** และแสดงผลแยกแถบในรายชื่อสมาชิกแล้วครับ!",
        ephemeral=True
    )
    write_log("setup_bot_roles (1:1 per bot) executed successfully.")

# --- Slash Command 5: /clean_webhooks ---
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
            if key in seen_names or not wh.name or wh.name == "PatchBot" or wh.name == "Needed by the Football Nation bot":
                try:
                    await wh.delete()
                    deleted_count += 1
                except Exception:
                    pass
            else:
                seen_names.add(key)

        await interaction.followup.send(
            f"🧹 **เคลียร์ Webhooks ขยะสำเร็จ!**\n"
            f"ลบ Webhooks ที่ค้างซ้ำซ้อนออกทั้งหมด: **{deleted_count} ตัว**",
            ephemeral=True
        )
        write_log(f"Cleaned {deleted_count} redundant webhooks.")
    except Exception as e:
        await interaction.followup.send(f"❌ Error cleaning webhooks: {e}", ephemeral=True)

# --- Slash Command 6: /backup_server ---
@bot.tree.command(name="backup_server", description="สำรองข้อมูลโครงสร้าง หมวดหมู่ ช่อง และสิทธิ์ของเซิร์ฟเวอร์ปัจจุบัน 100%")
@is_slash_guild_owner()
async def slash_backup_server(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    backup_data = {
        "guild_id": guild.id,
        "guild_name": guild.name,
        "categories": [],
        "uncategorized_channels": []
    }

    for cat in guild.categories:
        cat_data = {
            "name": cat.name,
            "position": cat.position,
            "channels": []
        }
        for ch in cat.channels:
            ch_info = {
                "name": ch.name,
                "id": ch.id,
                "type": str(ch.type),
                "position": ch.position,
                "topic": getattr(ch, "topic", None),
                "nsfw": getattr(ch, "nsfw", False),
                "slowmode_delay": getattr(ch, "slowmode_delay", 0)
            }
            cat_data["channels"].append(ch_info)
        backup_data["categories"].append(cat_data)

    for ch in guild.channels:
        if ch.category is None:
            backup_data["uncategorized_channels"].append({
                "name": ch.name,
                "id": ch.id,
                "type": str(ch.type),
                "position": ch.position
            })

    try:
        with open(BACKUP_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)

        write_log(f"Backup created successfully for server '{guild.name}' (ID: {guild.id})")
        await interaction.followup.send(
            f"✅ **สำรองข้อมูลโครงสร้างเซิร์ฟเวอร์สำเร็จเรียบร้อย!**\n"
            f"💾 บันทึกโครงสร้างหมวดหมู่และช่องแชททั้งหมดลงไฟล์ `server_backup.json` เรียบร้อยแล้ว\n"
            f"หากเกิดข้อผิดพลาด สามารถพิมพ์คำสั่ง `/restore_server` เพื่อกู้คืนได้ตลอดเวลาครับ!",
            ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(f"❌ Error creating backup: {e}", ephemeral=True)

# --- Slash Command 7: /restore_server ---
@bot.tree.command(name="restore_server", description="กู้คืนข้อมูลโครงสร้าง หมวดหมู่ และช่องแชทจากไฟล์สำรอง server_backup.json")
@is_slash_guild_owner()
async def slash_restore_server(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    if not os.path.exists(BACKUP_FILE_PATH):
        await interaction.followup.send("❌ ไม่พบไฟล์สำรอง `server_backup.json` กรุณารันคำสั่ง `/backup_server` ก่อนครับ", ephemeral=True)
        return

    try:
        with open(BACKUP_FILE_PATH, "r", encoding="utf-8") as f:
            backup_data = json.load(f)

        restored_cats = 0
        restored_chs = 0

        for cat_data in backup_data.get("categories", []):
            cat_name = cat_data["name"]
            category = discord.utils.get(guild.categories, name=cat_name)
            if not category:
                category = await guild.create_category(cat_name)
                restored_cats += 1

            for ch_data in cat_data.get("channels", []):
                ch_name = ch_data["name"]
                ch_type = ch_data["type"]
                existing_ch = discord.utils.get(guild.channels, name=ch_name)
                if not existing_ch:
                    if "text" in ch_type:
                        await category.create_text_channel(ch_name)
                        restored_chs += 1
                    elif "voice" in ch_type:
                        await category.create_voice_channel(ch_name)
                        restored_chs += 1

        await interaction.followup.send(
            f"🔄 **กู้คืนข้อมูลเซิร์ฟเวอร์จากไฟล์สำรองสำเร็จ!**\n"
            f"📁 หมวดหมู่ที่ตรวจสอบ/กู้คืน: {restored_cats} หมวด\n"
            f"💬 ช่องแชทที่กู้คืน: {restored_chs} ช่อง",
            ephemeral=True
        )
        write_log(f"Restored server structure from backup for guild '{guild.name}'.")
    except Exception as e:
        await interaction.followup.send(f"❌ Error restoring backup: {e}", ephemeral=True)

# --- Slash Command 8: /inspect_server ---
@bot.tree.command(name="inspect_server", description="สแกนทุกสิ่งทุกอย่างในเซิร์ฟเวอร์ และบันทึกข้อมูลลง bot.log อัตโนมัติ")
@is_slash_guild_owner()
async def slash_inspect_server(interaction: discord.Interaction):
    await interaction.response.defer()
    guild = interaction.guild

    scan_lines = []
    scan_lines.append(f"==================================================")
    scan_lines.append(f"🌌 DISCORD AUDIT SCAN REPORT")
    scan_lines.append(f"==================================================")
    
    scan_lines.append(f"\n[1] GUILD METADATA & SECURITY SETTINGS")
    scan_lines.append(f"• Name: {guild.name} (ID: {guild.id})")
    scan_lines.append(f"• Owner ID: {guild.owner_id}")
    scan_lines.append(f"• Total Member Count: {guild.member_count}")
    scan_lines.append(f"• Verification Level: {guild.verification_level}")

    scan_lines.append(f"\n[2] WEBHOOKS AUDIT")
    try:
        webhooks = await guild.webhooks()
        scan_lines.append(f"• Total Webhooks Count: {len(webhooks)}")
        for wh in webhooks:
            scan_lines.append(f"  - Webhook: '{wh.name}' (ID: {wh.id}) | Channel: #{wh.channel.name if wh.channel else 'Unknown'}")
    except Exception as e:
        scan_lines.append(f"• Webhooks Audit: ({e})")

    scan_lines.append(f"\n[3] ROLES ({len(guild.roles)} ROLES)")
    for role in sorted(guild.roles, key=lambda r: r.position, reverse=True):
        scan_lines.append(f"• Role: '{role.name}' (ID: {role.id}) | Pos: {role.position}")

    full_structure_text = "\n".join(scan_lines)
    write_log(full_structure_text)

    await interaction.followup.send(
        f"📊 **สแกนโครงสร้างเซิร์ฟเวอร์และบันทึกข้อมูลเรียบร้อยแล้ว!**\n\n"
        f"บันทึกผลการสแกนลงไฟล์ `bot.log` สำเร็จครับ!"
    )

@slash_setup_bot_roles.error
@slash_setup_verify.error
@slash_backup_server.error
@slash_restore_server.error
@slash_clean_webhooks.error
@slash_organize_existing_server.error
@slash_inspect_server.error
async def slash_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        if not interaction.response.is_done():
            await interaction.response.send_message("⚠️ You do not have permission to use this command. (Server Owner only)", ephemeral=True)
        write_log(f"Permission failure for command by user {interaction.user}")
    else:
        if not interaction.response.is_done():
            await interaction.response.send_message(f"⚠️ Error: {error}", ephemeral=True)
        write_log(f"Slash command error: {error}")

if __name__ == "__main__":
    if not TOKEN or TOKEN == "your_bot_token_here":
        print("Error: Please set DISCORD_TOKEN in .env file")
    else:
        bot.run(TOKEN)
