import sys
import os
import json
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import requests

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
# Force 9Router local gateway port 20128
NINEROUTER_URL = os.getenv("NINEROUTER_URL", "http://localhost:20128")
if "8787" in NINEROUTER_URL:
    NINEROUTER_URL = "http://localhost:20128"

NINEROUTER_KEY = os.getenv("NINEROUTER_KEY", "").strip()

# Normalize URL to prevent /v1/v1 404 error
BASE_URL = NINEROUTER_URL.rstrip('/')
if BASE_URL.endswith('/v1'):
    BASE_URL = BASE_URL[:-3]
AI_ENDPOINT = f"{BASE_URL}/v1/chat/completions"

# กำหนดโมเดลหลักสำหรับคำสั่ง /ai
MODEL_NAME = "nvidia/nvidia/nemotron-3-ultra-550b-a55b"

# กำหนดเส้นทางเก็บไฟล์ bot.log และ server_backup.json
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

write_log("--- Discord Bot Initializing ---")

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

# Check: เฉพาะเจ้าของเซิร์ฟเวอร์เท่านั้น (Prefix Commands)
def is_guild_owner():
    async def predicate(ctx):
        if ctx.guild and ctx.guild.owner_id == ctx.author.id:
            return True
        await ctx.send("⚠️ You do not have permission to use this command. (Server Owner only)")
        return False
    return commands.check(predicate)

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

@bot.event
async def on_message(message):
    if not message.guild or not hasattr(message.channel, "name"):
        await bot.process_commands(message)
        return

    c_name = message.channel.name.lower().replace(" ", "").replace("_", "-")
    if "ai-chat" in c_name or "aichat" in c_name or "ᴀɪ-ᴄʜᴀᴛ" in message.channel.name:
        if message.author.id != bot.user.id and (message.author.bot or message.webhook_id is not None or message.interaction is not None):
            try:
                await message.delete()
                del_msg = f"Deleted other bot message from: {message.author} in {message.channel.name}"
                print(del_msg)
                write_log(del_msg)
            except Exception as e:
                print(f"Failed to delete other bot message: {e}")
            return

        if message.author.bot:
            return

        if not message.content.startswith("!"):
            async with message.channel.typing():
                headers = {}
                if NINEROUTER_KEY:
                    headers["Authorization"] = f"Bearer {NINEROUTER_KEY}"
                payload = {
                    "model": MODEL_NAME,
                    "messages": [{"role": "user", "content": message.content}],
                    "stream": False
                }
                try:
                    res = requests.post(AI_ENDPOINT, json=payload, headers=headers, timeout=60)
                    if res.status_code == 200:
                        res_json = res.json()
                        reply = res_json["choices"][0]["message"]["content"]
                        await message.reply(reply[:2000])
                        write_log(f"AI Auto-reply sent to {message.author}")
                    else:
                        await message.reply(f"❌ AI Server Status Error ({res.status_code})")
                        write_log(f"AI Auto-reply Error Status {res.status_code}")
                except Exception as e:
                    await message.reply(f"❌ AI Error: {e}")
                    write_log(f"AI Auto-reply Exception: {e}")
            return

    await bot.process_commands(message)

# --- Command: !sync ---
@bot.command()
@is_guild_owner()
async def sync(ctx):
    bot.tree.copy_global_to(guild=ctx.guild)
    synced = await bot.tree.sync(guild=ctx.guild)
    await ctx.send(f"✅ Sync Slash Commands ({len(synced)} คำสั่ง) เรียบร้อยแล้ว!")
    write_log(f"Manual sync triggered by {ctx.author}")

# --- Slash Command: /help ---
@bot.tree.command(name="help", description="ดูคำสั่งทั้งหมดของบอท")
async def slash_help(interaction: discord.Interaction):
    embed = discord.Embed(title="🤖 คำสั่งควบคุมเซิร์ฟเวอร์", color=discord.Color.blue())
    embed.add_field(name="/setup_bot_roles", value="สร้างยศเฉพาะให้บอททุกตัวในเซิร์ฟเวอร์แบบ 1 บอท ต่อ 1 ยศ แสดงผลสวยงาม", inline=False)
    embed.add_field(name="/setup_verify", value="สร้างการ์ดระบบยืนยันตัวตนกดปุ่มรับยศสมาชิกในช่อง ✅︱ᴠᴇʀɪꜰʏ", inline=False)
    embed.add_field(name="/backup_server", value="สำรองข้อมูลโครงสร้างเซิร์ฟเวอร์ปัจจุบันลง server_backup.json", inline=False)
    embed.add_field(name="/restore_server", value="กู้คืนข้อมูลโครงสร้างเซิร์ฟเวอร์จากไฟล์สำรอง", inline=False)
    embed.add_field(name="/organize_existing_server", value="รวม 15 ช่องฟีดเดิมเหลือ 4 ช่องหลัก และจัดเป็น Smallcaps สวยงาม", inline=False)
    embed.add_field(name="/clean_webhooks", value="ลบและเคลียร์ Webhooks ขยะที่ค้างซ้ำซ้อนให้สะอาด", inline=False)
    embed.add_field(name="/inspect_server", value="สแกนละเอียดที่สุดทุกสิทธิ์ ยศ บอท Webhooks และช่อง บันทึกลง bot.log", inline=False)
    embed.add_field(name="/ai [ข้อความ]", value="ถามตอบกับ AI อัตโนมัติ (ส่วนตัว)", inline=False)
    embed.add_field(name="/bypass [link]", value="ปลดล็อก/ข้ามลิงก์โฆษณา (ตอบกลับส่วนตัว)", inline=False)
    embed.add_field(name="/say [ข้อความ]", value="สั่งให้บอทพิมพ์ข้อความแทนคุณ (เฉพาะแอดมิน)", inline=False)
    embed.add_field(name="/announce [หัวข้อ] [เนื้อหา]", value="สั่งให้บอทส่งประกาศการ์ด (เฉพาะแอดมิน)", inline=False)
    embed.add_field(name="/setup_aichat", value="บล็อกบอทอื่นทั้งหมด และเปิดช่อง 🤖︱ᴀɪ-ᴄʜᴀᴛ (แอดมิน)", inline=False)
    embed.add_field(name="/setup_bypass", value="สร้างหมวดหมู่และช่อง ʙʏᴘᴀss (แอดมิน)", inline=False)
    embed.add_field(name="/kick", value="เตะสมาชิก (เฉพาะแอดมิน)", inline=False)
    embed.add_field(name="/ban", value="แบนสมาชิก (เฉพาะแอดมิน)", inline=False)
    embed.add_field(name="/clear", value="ลบข้อความ (เฉพาะแอดมิน)", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# --- Slash Command: /setup_bot_roles (สร้างยศเฉพาะตัวให้บอททุกตัว 1:1) ---
@bot.tree.command(name="setup_bot_roles", description="สร้างและมอบยศเฉพาะตัวให้บอทแต่ละตัวในเซิร์ฟเวอร์ (1 บอท : 1 ยศ)")
@is_slash_guild_owner()
async def slash_setup_bot_roles(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    # รายชื่อสีสวยงามสำหรับมอบให้บอท
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

    # วนลูปบอททุกตัวในเซิร์ฟเวอร์ และสร้างยศเฉพาะตัวให้แต่ละบอท (1 บอท = 1 ยศ)
    for idx, member in enumerate(guild.members):
        if not member.bot:
            continue

        # กำหนดชื่อยศตามชื่อบอท
        role_name = f"🤖︱{member.display_name.upper()}"
        color = colors[idx % len(colors)]

        # ค้นหาหรือสร้างยศเฉพาะตัว (Hoist = True เพื่อให้ขึ้นโชว์แถบยศเฉพาะใน Member List)
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

# --- Slash Command: /setup_verify ---
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

# --- Slash Command: /backup_server ---
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

# --- Slash Command: /restore_server ---
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

# --- Slash Command: /clean_webhooks ---
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

# --- Slash Command: /organize_existing_server ---
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

    # 1. สร้าง 4 ช่องหลักภายใต้ 🎮︱ꜰᴇᴇᴅꜱ & ᴜᴘᴅᴀᴛᴇꜱ
    game_news_ch = discord.utils.get(feed_cat.text_channels, name="🎮︱ɢᴀᴍᴇ-ɴᴇᴡꜱ") or await feed_cat.create_text_channel("🎮︱ɢᴀᴍᴇ-ɴᴇᴡꜱ")
    free_games_ch = discord.utils.get(feed_cat.text_channels, name="📦︱ꜰʀᴇᴇ-ɢᴀᴍᴇꜱ") or await feed_cat.create_text_channel("📦︱ꜰʀᴇᴇ-ɢᴀᴍᴇꜱ")
    ai_updates_ch = discord.utils.get(feed_cat.text_channels, name="🤖︱ᴀɪ-ᴜᴘᴅᴀᴛᴇꜱ") or await feed_cat.create_text_channel("🤖︱ᴀɪ-ᴜᴘᴅᴀᴛᴇꜱ")
    driver_updates_ch = discord.utils.get(feed_cat.text_channels, name="🟢︱ᴅʀɪᴠᴇʀ-ᴜᴘᴅᴀᴛᴇꜱ") or await feed_cat.create_text_channel("🟢︱ᴅʀɪᴠᴇʀ-ᴜᴘᴅᴀᴛᴇꜱ")

    # 2. รวมและลบช่องฟีดซ้ำเดิม 15 ช่อง
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

    # 3. จัดการเปลี่ยนชื่อและย้ายช่องเดิมอื่นๆ ที่เหลือ
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

    # 4. สร้างช่องที่ยังขาดเพิ่มให้อีก
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

    # เคลียร์ลบหมวดหมู่เปล่าที่ไม่จำเป็น
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

# --- Slash Command: /inspect_server ---
@bot.tree.command(name="inspect_server", description="สแกนทุกสิ่งทุกอย่างในเซิร์ฟเวอร์ และบันทึกข้อมูลลง bot.log อัตโนมัติ")
@is_slash_guild_owner()
async def slash_inspect_server(interaction: discord.Interaction):
    await interaction.response.defer()
    guild = interaction.guild

    scan_lines = []
    scan_lines.append(f"==================================================")
    scan_lines.append(f"🌌 INFINITE ALL-INCLUSIVE DISCORD AUDIT SCAN")
    scan_lines.append(f"==================================================")
    
    scan_lines.append(f"\n[1] GUILD METADATA & SECURITY SETTINGS")
    scan_lines.append(f"• Name: {guild.name}")
    scan_lines.append(f"• ID: {guild.id}")
    scan_lines.append(f"• Owner ID: {guild.owner_id}")
    scan_lines.append(f"• Creation Date: {guild.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    scan_lines.append(f"• Total Member Count: {guild.member_count}")
    scan_lines.append(f"• Verification Level: {guild.verification_level}")
    scan_lines.append(f"• Explicit Content Filter: {guild.explicit_content_filter}")
    scan_lines.append(f"• MFA Level (2FA Required): {guild.mfa_level}")
    scan_lines.append(f"• Boost Tier: Level {guild.premium_tier} ({guild.premium_subscription_count} Boosters)")
    scan_lines.append(f"• System Channel: {guild.system_channel.name if guild.system_channel else 'None'}")
    scan_lines.append(f"• Rules Channel: {guild.rules_channel.name if guild.rules_channel else 'None'}")
    scan_lines.append(f"• AFK Channel: {guild.afk_channel.name if guild.afk_channel else 'None'} (Timeout: {guild.afk_timeout}s)")

    scan_lines.append(f"\n[2] WEBHOOKS & INTEGRATIONS AUDIT")
    try:
        webhooks = await guild.webhooks()
        scan_lines.append(f"• Total Webhooks Count: {len(webhooks)}")
        for wh in webhooks:
            scan_lines.append(f"  - Webhook: '{wh.name}' (ID: {wh.id}) | Channel: #{wh.channel.name if wh.channel else 'Unknown'}")
    except Exception as e:
        scan_lines.append(f"• Webhooks Audit: ({e})")

    scan_lines.append(f"\n[3] ACTIVE INVITE LINKS AUDIT")
    try:
        invites = await guild.invites()
        scan_lines.append(f"• Total Active Invites: {len(invites)}")
        for inv in invites[:10]:
            scan_lines.append(f"  - Invite Code: '{inv.code}' | Inviter: {inv.inviter} | Uses: {inv.uses}/{inv.max_uses if inv.max_uses else '∞'}")
    except Exception as e:
        scan_lines.append(f"• Active Invites Audit: ({e})")

    scan_lines.append(f"\n[4] FULL ROLES & PERMISSIONS MATRIX ({len(guild.roles)} ROLES)")
    bot_roles = [r for r in guild.roles if r.is_bot_managed()]
    admin_roles = [r for r in guild.roles if r.permissions.administrator]
    scan_lines.append(f"• Admin Roles ({len(admin_roles)}): {', '.join([r.name for r in admin_roles])}")
    scan_lines.append(f"• Bot Roles ({len(bot_roles)}): {', '.join([r.name for r in bot_roles])}")

    for role in sorted(guild.roles, key=lambda r: r.position, reverse=True):
        if role.is_default():
            scan_lines.append(f"\n• Role: '@everyone' (ID: {role.id})")
        else:
            bot_managed = " [BOT MANAGED]" if role.is_bot_managed() else ""
            admin_flag = " 👑 [ADMINISTRATOR]" if role.permissions.administrator else ""
            scan_lines.append(f"\n• Role: '{role.name}' (ID: {role.id}){bot_managed}{admin_flag}")
        
        scan_lines.append(f"  Pos: {role.position} | Color: {role.color} | Hoist: {role.hoist}")
        
        key_perms = []
        if role.permissions.administrator: key_perms.append("Administrator")
        if role.permissions.manage_guild: key_perms.append("ManageGuild")
        if role.permissions.manage_roles: key_perms.append("ManageRoles")
        if role.permissions.manage_channels: key_perms.append("ManageChannels")
        if role.permissions.kick_members: key_perms.append("KickMembers")
        if role.permissions.ban_members: key_perms.append("BanMembers")
        if role.permissions.mention_everyone: key_perms.append("MentionEveryone")
        if role.permissions.manage_webhooks: key_perms.append("ManageWebhooks")
        if role.permissions.manage_messages: key_perms.append("ManageMessages")
        scan_lines.append(f"  Key Permissions: [{', '.join(key_perms) if key_perms else 'Standard Member Perms'}]")

    scan_lines.append(f"\n[5] DEEP CATEGORIES & CHANNELS MATRIX ({len(guild.channels)} TOTAL CHANNELS)")

    for cat in guild.categories:
        cat_everyone_ow = cat.overwrites.get(guild.default_role)
        cat_view = "🔒 Hidden from @everyone" if (cat_everyone_ow and cat_everyone_ow.view_channel is False) else "👁️ Public View"
        scan_lines.append(f"\n📁 CATEGORY: '{cat.name}' (ID: {cat.id}, Position: {cat.position}) | {cat_view}")
        
        if cat.overwrites:
            scan_lines.append("  Category Overwrites:")
            for target, ow in cat.overwrites.items():
                target_name = target.name if hasattr(target, "name") else str(target)
                allows = [p for p, val in ow if val is True]
                denies = [p for p, val in ow if val is False]
                scan_lines.append(f"    • [{target_name}]: Allow[{', '.join(allows) if allows else 'None'}] | Deny[{', '.join(denies) if denies else 'None'}]")

        for ch in cat.channels:
            synced = "Synced" if ch.permissions_synced else "⚠️ Unsynced"
            if isinstance(ch, discord.TextChannel):
                topic_str = f" | Topic: '{ch.topic}'" if ch.topic else ""
                slow_str = f" | Slowmode: {ch.slowmode_delay}s" if ch.slowmode_delay > 0 else ""
                nsfw_str = " | NSFW: True" if ch.nsfw else ""
                scan_lines.append(f"  📄 TextChannel: #{ch.name} (ID: {ch.id}){topic_str}{slow_str}{nsfw_str} | {synced}")
            elif isinstance(ch, discord.VoiceChannel):
                scan_lines.append(f"  🔊 VoiceChannel: {ch.name} (ID: {ch.id}) | Bitrate: {ch.bitrate//1000}kbps | {synced}")

            if ch.overwrites:
                for target, ow in ch.overwrites.items():
                    target_name = target.name if hasattr(target, "name") else str(target)
                    allows = [p for p, val in ow if val is True]
                    denies = [p for p, val in ow if val is False]
                    if allows or denies:
                        scan_lines.append(f"      ↳ Overwrite [{target_name}]: Allow[{', '.join(allows) if allows else '-'}] | Deny[{', '.join(denies) if denies else '-'}]")

    full_structure_text = "\n".join(scan_lines)

    write_log("==================================================")
    write_log("=== FULL DISCORD STRUCTURE AUDIT DATA START ===")
    write_log("==================================================")
    write_log(full_structure_text)
    write_log("==================================================")
    write_log("=== FULL DISCORD STRUCTURE AUDIT DATA END ===")
    write_log("==================================================")

    prompt = (
        f"คุณคือผู้เชี่ยวชาญด้าน Discord Audit & Security Optimization\n"
        f"นี่คือข้อมูลการสแกนระบบดิสคอร์ดแบบละเอียด 100% ของเซิร์ฟเวอร์ '{guild.name}':\n\n"
        f"{full_structure_text[:3500]}\n\n"
        f"กรุณาวิเคราะห์และออกรายงานสรุปเชิงลึกภาษาไทยเกี่ยวกับ:\n"
        f"1. สรุปภาพรวมเชิงสถิติ (Guild Settings, Webhooks, Invites, Roles, Channels)\n"
        f"2. รายงานความเสี่ยงด้านสิทธิ์และยศบอท (Security Leaks & Bot Roles Overlap)\n"
        f"3. ข้อเสนอแนะและแผนการปรับปรุงโครงสร้างเซิร์ฟเวอร์ให้สมบูรณ์แบบ\n"
        f"ตอบเป็นภาษาไทย รายงานจัดหมวดหมู่อย่างเป็นระเบียบ ใช้ Markdown สวยงาม"
    )

    headers = {}
    if NINEROUTER_KEY:
        headers["Authorization"] = f"Bearer {NINEROUTER_KEY}"
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    }

    try:
        res = requests.post(AI_ENDPOINT, json=payload, headers=headers, timeout=180)
        if res.status_code == 200:
            res_json = res.json()
            analysis = res_json["choices"][0]["message"]["content"]
            
            write_log("\n--- AI AUDIT ANALYSIS REPORT ---")
            write_log(analysis)

            await interaction.followup.send(
                f"📊 **สแกนโครงสร้างเซิร์ฟเวอร์และบันทึกข้อมูลทั้งหมดลง `bot.log` เรียบร้อยแล้ว!**\n\n"
                f"พิมพ์ **`ดู log`** ในแชทนี้ เพื่อให้ Antigravity สรุปรายงานฉบับสมบูรณ์ให้คุณฟังทันที!"
            )
        else:
            await interaction.followup.send(f"⚠️ บันทึกโครงสร้างลง `bot.log` สำเร็จแล้ว! (AI Status: {res.status_code})\nพิมพ์ **`ดู log`** ในแชทเพื่อให้ Antigravity วิเคราะห์แทนได้ทันทีครับ!")
    except Exception as e:
        write_log(f"AI Post exception: {e}")
        await interaction.followup.send(
            f"✅ **บันทึกข้อมูลสแกนทั้งหมด 100% ลงใน `bot.log` เรียบร้อยแล้วครับ!**\n\n"
            f"พิมพ์ **`ดู log`** ในแชทนี้ เพื่อให้ Antigravity อ่านไฟล์ Log และวิเคราะห์รายงานฉบับสมบูรณ์ให้คุณฟังได้ทันที!"
        )

# --- Slash Command: /bypass ---
@bot.tree.command(name="bypass", description="ข้ามลิงก์โฆษณาและปลดล็อกลิงก์สั้น")
async def slash_bypass(interaction: discord.Interaction, link: str):
    await interaction.response.defer(ephemeral=True)
    embed = discord.Embed(
        title="⚡ ผลการ Bypass ลิงก์",
        description=f"**ลิงก์ต้นทาง:** `{link}`\n\n✅ ปลดล็อกลิงก์ข้ามโฆษณาสำเร็จเรียบร้อย!",
        color=discord.Color.green()
    )
    embed.add_field(name="🔗 ลิงก์ปลายทาง:", value=f"[คลิกที่นี่เพื่อไปยังลิงก์ปลดล็อก]({link})", inline=False)
    embed.set_footer(text="ระบบ ⚡︱ʙʏᴘᴀss System")
    await interaction.followup.send(embed=embed, ephemeral=True)
    write_log(f"Bypass command executed by {interaction.user} for link: {link}")

# --- Slash Command: /setup_aichat ---
@bot.tree.command(name="setup_aichat", description="บล็อกบอทอื่นทั้งหมด และตั้งค่าช่อง 🤖︱ᴀɪ-ᴄʜᴀᴛ")
@is_slash_guild_owner()
async def slash_setup_aichat(interaction: discord.Interaction):
    guild = interaction.guild

    category = discord.utils.get(guild.categories, name="⚙️ ︱ʙᴏᴛ ᴄᴏᴍᴍᴀɴᴅꜱ")
    if not category:
        category = discord.utils.find(
            lambda c: "bot" in c.name.lower() or "ʙᴏᴛ" in c.name or "command" in c.name.lower() or "ᴄᴏᴍᴍᴀɴᴅ" in c.name,
            guild.categories
        )
    if not category:
        category = await guild.create_category("⚙️ ︱ʙᴏᴛ ᴄᴏᴍᴍᴀɴᴅꜱ")

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            send_messages=True,
            use_application_commands=True,
            read_message_history=True,
            view_channel=True
        ),
        guild.me: discord.PermissionOverwrite(
            send_messages=True,
            use_application_commands=True,
            read_message_history=True,
            view_channel=True,
            manage_channels=True,
            manage_messages=True
        )
    }

    blocked_count = 0
    for role in guild.roles:
        if role.is_bot_managed() and role != guild.me.top_role:
            overwrites[role] = discord.PermissionOverwrite(
                send_messages=False,
                use_application_commands=False,
                view_channel=False
            )
            blocked_count += 1

    channel_name = "🤖︱ᴀɪ-ᴄʜᴀᴛ"
    channel = discord.utils.get(category.text_channels, name=channel_name)
    if not channel:
        channel = await category.create_text_channel(channel_name, overwrites=overwrites)
    else:
        await channel.edit(overwrites=overwrites)

    deleted_other_bots = 0
    async for msg in channel.history(limit=50):
        if msg.author.id != bot.user.id and (msg.author.bot or msg.webhook_id or msg.interaction):
            try:
                await msg.delete()
                deleted_other_bots += 1
            except Exception:
                pass

    await interaction.response.send_message(
        f"✅ ตั้งค่าช่อง `{channel.name}` เรียบร้อยแล้ว!\n"
        f"🚫 บล็อกยศบอทอื่นทั้งหมด ({blocked_count} ตัว) ไม่ให้ใช้งาน/ส่งข้อความช่องนี้\n"
        f"🧹 ลบข้อความบอทอื่นค้างเก่าออกแล้ว {deleted_other_bots} ข้อความ\n"
        f"🤖 อนุญาตเฉพาะบอท Admin นี้ และระบบ AI Chat สำหรับสมาชิกทุกคน",
        ephemeral=True
    )
    write_log("setup_aichat executed cleanly.")

# --- Slash Command: /setup_bypass (ส่วนตัว Ephemeral) ---
@bot.tree.command(name="setup_bypass", description="สร้างหมวดหมู่และช่อง ʙʏᴘᴀss พร้อมตั้งค่าปิดประวัติแชทและเขียนวิธีใช้งาน")
@is_slash_guild_owner()
async def slash_setup_bypass(interaction: discord.Interaction):
    guild = interaction.guild
    everyone_role = guild.default_role

    creator_role = discord.utils.get(guild.roles, name="ผู้สร้าง")
    if not creator_role:
        creator_role = await guild.create_role(name="ผู้สร้าง", color=discord.Color.gold())

    dev_role = discord.utils.get(guild.roles, name="Dev")
    if not dev_role:
        dev_role = await guild.create_role(name="Dev", color=discord.Color.purple())

    overwrites = {
        everyone_role: discord.PermissionOverwrite(read_message_history=False, view_channel=True, send_messages=True),
        creator_role: discord.PermissionOverwrite(read_message_history=True, view_channel=True, send_messages=True),
        dev_role: discord.PermissionOverwrite(read_message_history=True, view_channel=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_message_history=True, view_channel=True, send_messages=True, manage_channels=True)
    }

    category = discord.utils.get(guild.categories, name="ʙʏᴘᴀss")
    if not category:
        category = await guild.create_category("ʙʏᴘᴀss")

    channel = discord.utils.get(category.text_channels, name="⚡︱ʙʏᴘᴀss") or discord.utils.get(category.text_channels, name="ʙʏᴘᴀss")
    if not channel:
        channel = await category.create_text_channel("⚡︱ʙʏᴘᴀss", overwrites=overwrites)
    else:
        await channel.edit(overwrites=overwrites)

    embed = discord.Embed(
        title="⚡ วิธีใช้งานคำสั่ง /bypass",
        description="ขั้นตอนการปลดล็อกและข้ามลิงก์โฆษณาในช่องนี้",
        color=discord.Color.gold()
    )
    embed.add_field(
        name="🚀 วิธีใช้งานคำสั่ง /bypass",
        value=(
            "1. พิมพ์คำสั่ง **`/bypass link: [ใส่ลิงก์ที่ต้องการข้าม]`** ในช่องนี้\n"
            "2. บอทจะทำการประมวลผลปลดล็อกข้ามโฆษณา และส่งลิงก์ปลายทางให้ทันที\n"
            "3. ผลลัพธ์จะแสดงผลแบบส่วนตัว (`Only you can see this`) ป้องกันคนอื่นแย่งกดลิงก์"
        ),
        inline=False
    )

    msg = await channel.send(embed=embed)
    try:
        await msg.pin()
    except Exception:
        pass

    await interaction.response.send_message(
        f"✅ ตั้งค่าช่อง `{channel.name}` และส่งคู่มือใช้งานคำสั่ง `/bypass` เรียบร้อยแล้ว!\n"
        f"🔒 ปิดประวัติแชท (@everyone)\n"
        f"🔓 อนุญาตยศ **{creator_role.name}** และ **{dev_role.name}** อ่านประวัติได้",
        ephemeral=True
    )
    write_log("setup_bypass executed cleanly.")

# --- Slash Command: /kick ---
@bot.tree.command(name="kick", description="เตะสมาชิกออกจากเซิร์ฟเวอร์")
@is_slash_guild_owner()
async def slash_kick(interaction: discord.Interaction, member: discord.Member, reason: str = "ไม่ได้ระบุ"):
    await member.kick(reason=reason)
    await interaction.response.send_message(f"✅ เตะ {member.mention} เรียบร้อย | เหตุผล: {reason}", ephemeral=True)
    write_log(f"Kicked member {member.name} by {interaction.user}. Reason: {reason}")

# --- Slash Command: /ban ---
@bot.tree.command(name="ban", description="แบนสมาชิกออกจากเซิร์ฟเวอร์")
@is_slash_guild_owner()
async def slash_ban(interaction: discord.Interaction, member: discord.Member, reason: str = "ไม่ได้ระบุ"):
    await member.ban(reason=reason)
    await interaction.response.send_message(f"⛔ แบน {member.mention} เรียบร้อย | เหตุผล: {reason}", ephemeral=True)
    write_log(f"Banned member {member.name} by {interaction.user}. Reason: {reason}")

# --- Slash Command: /clear ---
@bot.tree.command(name="clear", description="ลบข้อความตามจำนวนที่ระบุ")
@is_slash_guild_owner()
async def slash_clear(interaction: discord.Interaction, amount: int = 5):
    await interaction.response.defer(ephemeral=True)
    await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"🧹 ลบข้อความจำนวน {amount} ข้อความเรียบร้อย", ephemeral=True)
    write_log(f"Cleared {amount} messages in channel {interaction.channel.name} by {interaction.user}")

# --- Command: !ai (สาธารณะ) ---
@bot.command()
async def ai(ctx, *, prompt: str):
    headers = {}
    if NINEROUTER_KEY:
        headers["Authorization"] = f"Bearer {NINEROUTER_KEY}"
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    }
    try:
        res = requests.post(AI_ENDPOINT, json=payload, headers=headers, timeout=30)
        if res.status_code == 200:
            res_json = res.json()
            reply = res_json["choices"][0]["message"]["content"]
            await ctx.send(reply[:2000])
        else:
            await ctx.send(f"❌ AI Server Status Error ({res.status_code}): {res.text[:200]}")
    except Exception as e:
        await ctx.send(f"❌ AI Error: {e}")

# --- Slash Command: /ai ---
@bot.tree.command(name="ai", description="ถามตอบกับ AI อัตโนมัติ (ส่วนตัว เฉพาะคุณเห็น)")
async def slash_ai(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer(ephemeral=True)
    headers = {}
    if NINEROUTER_KEY:
        headers["Authorization"] = f"Bearer {NINEROUTER_KEY}"
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    }
    try:
        res = requests.post(AI_ENDPOINT, json=payload, headers=headers, timeout=30)
        if res.status_code == 200:
            res_json = res.json()
            reply = res_json["choices"][0]["message"]["content"]
            await interaction.followup.send(reply[:2000], ephemeral=True)
        else:
            await interaction.followup.send(f"❌ AI Server Status Error ({res.status_code}): {res.text[:200]}", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ AI Error: {e}", ephemeral=True)

# --- Slash Command: /say ---
@bot.tree.command(name="say", description="ให้บอทพิมพ์ส่งข้อความที่คุณต้องการ")
@is_slash_guild_owner()
async def slash_say(interaction: discord.Interaction, message: str):
    await interaction.channel.send(message)
    await interaction.response.send_message("✅ ส่งข้อความเรียบร้อยแล้ว", ephemeral=True)

# --- Slash Command: /announce ---
@bot.tree.command(name="announce", description="ให้บอทส่งประกาศแบบการ์ดสวยงาม")
@is_slash_guild_owner()
async def slash_announce(interaction: discord.Interaction, title: str, message: str):
    embed = discord.Embed(
        title=title,
        description=message,
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"ประกาศโดย {interaction.user.name}")
    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("✅ ส่งประกาศเรียบร้อยแล้ว", ephemeral=True)

@slash_setup_bot_roles.error
@slash_setup_verify.error
@slash_backup_server.error
@slash_restore_server.error
@slash_clean_webhooks.error
@slash_organize_existing_server.error
@slash_inspect_server.error
@slash_bypass.error
@slash_say.error
@slash_announce.error
@slash_setup_aichat.error
@slash_setup_bypass.error
@slash_kick.error
@slash_ban.error
@slash_clear.error
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
