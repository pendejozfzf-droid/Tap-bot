# main.py
"""
TempVoice Mod — Python (discord.py)
Features:
- /setuptap <voice_channel>  (owner only) -> set the Join-To-Create channel
- When a user joins the configured Join-To-Crate channel:
    -> create a private voice channel named "<user>'s Room"
    -> move the user there
- Prefix commands starting with ".v "
    .v name   .v lock   .v unlock   .v hide   .v unhide
    .v transfer   .v addco   .v info   .v close   .v commands   .v claim   .v reject
- Auto delete room when empty
- Uses data.json to store tap_channel id + owner + coowners
"""

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import json
import os

# -------------------------
# Intents & Bot
# -------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix=".v ", intents=intents)

DATA_FILE = "data.json"

# -------------------------
# Load & Save Data
# -------------------------
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"tap_channel": None, "voice_owners": {}, "coowners": {}}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"tap_channel": None, "voice_owners": {}, "coowners": {}}

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

data = load_data()

# -------------------------
# Utils
# -------------------------
def get_owner_vc_by_user(user_id: int):
    for vcid, owner in data.get("voice_owners", {}).items():
        if owner == user_id:
            vc = bot.get_channel(int(vcid))
            if vc:
                return vc
    return None

# -------------------------
# Ready
# -------------------------
@bot.event
async def on_ready():
    print(f"🔥 Logged in as {bot.user}")
    try:
        await bot.tree.sync()
        print("✔ Slash commands synced.")
    except Exception as e:
        print("❌ Sync error:", e)

# -------------------------
# /setuptap
# -------------------------
@bot.tree.command(name="setuptap", description="Set Join-To-Create Voice Channel (Owner Only)")
@app_commands.describe(channel="Select the voice channel to be JTC")
async def setuptap(interaction: discord.Interaction, channel: discord.VoiceChannel):
    if interaction.user.id != interaction.guild.owner_id:
        return await interaction.response.send_message("❌ Only server owner can use this.", ephemeral=True)

    data["tap_channel"] = channel.id
    save_data()

    await interaction.response.send_message(
        f"✅ Join-To-Create channel set to **{channel.name}**.",
        ephemeral=True
    )

# -------------------------
# Voice System
# -------------------------
@bot.event
async def on_voice_state_update(member, before, after):
    try:
        tap_id = data.get("tap_channel")
        if not tap_id:
            return

        # 1) Create room when user joins TAP
        if after.channel and after.channel.id == tap_id and before.channel != after.channel:

            guild = member.guild
            category = after.channel.category

            vc_name = f"{member.display_name}'s Room"
            vc = await guild.create_voice_channel(name=vc_name, category=category)

            data["voice_owners"][str(vc.id)] = member.id
            save_data()

            await member.move_to(vc)

            await asyncio.sleep(1)

        # 2) Auto delete room when empty
        if before.channel and (after.channel is None or before.channel.id != after.channel.id):

            vc = before.channel
            vc_id = str(vc.id)

            if vc_id in data["voice_owners"]:
                if len(vc.members) == 0:

                    try:
                        await vc.delete()
                        print(f"[AUTO] Deleted empty VC: {vc.name}")
                    except Exception as e:
                        print(f"[WARN] Failed to delete VC {vc.id}: {e}")

                    data["voice_owners"].pop(vc_id, None)
                    data.get("coowners", {}).pop(vc_id, None)
                    save_data()

    except Exception as e:
        print("VOICE ERROR:", e)

# -------------------------
# .v COMMANDS
# -------------------------
@bot.event
async def on_message(msg):
    if msg.author.bot:
        return
    await bot.process_commands(msg)

# .v name
@bot.command(name="name")
async def v_name(ctx, *, new_name=None):
    if not new_name:
        return await ctx.reply("❌ Usage: `.v name <new name>`")
    vc = get_owner_vc_by_user(ctx.author.id)
    if not vc:
        return await ctx.reply("❌ You don't own a room.")
    await vc.edit(name=new_name)
    await ctx.reply(f"✨ Room renamed to **{new_name}**")

# .v lock
@bot.command(name="lock")
async def v_lock(ctx):
    vc = get_owner_vc_by_user(ctx.author.id)
    if not vc:
        return await ctx.reply("❌ You don't own a room.")
    await vc.set_permissions(ctx.guild.default_role, connect=False)
    await ctx.reply("🔒 Room locked.")

# .v unlock
@bot.command(name="unlock")
async def v_unlock(ctx):
    vc = get_owner_vc_by_user(ctx.author.id)
    if not vc:
        return await ctx.reply("❌ You don't own a room.")
    await vc.set_permissions(ctx.guild.default_role, connect=True)
    await ctx.reply("🔓 Room unlocked.")

# .v hide
@bot.command(name="hide")
async def v_hide(ctx):
    vc = get_owner_vc_by_user(ctx.author.id)
    if not vc:
        return await ctx.reply("❌ You don't own a room.")
    await vc.set_permissions(ctx.guild.default_role, view_channel=False)
    await ctx.reply("👁 Room hidden.")

# .v unhide
@bot.command(name="unhide")
async def v_unhide(ctx):
    vc = get_owner_vc_by_user(ctx.author.id)
    if not vc:
        return await ctx.reply("❌ You don't own a room.")
    await vc.set_permissions(ctx.guild.default_role, view_channel=True)
    await ctx.reply("👁 Room visible.")

# .v transfer
@bot.command(name="transfer")
async def v_transfer(ctx, member: discord.Member = None):
    if not member:
        return await ctx.reply("❌ Usage: `.v transfer @user`")
    vc = get_owner_vc_by_user(ctx.author.id)
    if not vc:
        return await ctx.reply("❌ You don't own a room.")

    data["voice_owners"][str(vc.id)] = member.id
    save_data()
    await ctx.reply(f"👑 Ownership transferred to {member.mention}")

# .v addco
@bot.command(name="addco")
async def v_addco(ctx, member: discord.Member = None):
    if not member:
        return await ctx.reply("❌ Usage: `.v addco @user`")
    vc = get_owner_vc_by_user(ctx.author.id)
    if not vc:
        return await ctx.reply("❌ You don't own a room.")

    if str(vc.id) not in data["coowners"]:
        data["coowners"][str(vc.id)] = []

    if member.id not in data["coowners"][str(vc.id)]:
        data["coowners"][str(vc.id)].append(member.id)

    save_data()
    await ctx.reply(f"✨ {member.mention} added as co-owner.")

# .v info
@bot.command(name="info")
async def v_info(ctx):
    vc = get_owner_vc_by_user(ctx.author.id)
    if not vc:
        return await ctx.reply("❌ You don't own a room.")

    owner_id = data["voice_owners"].get(str(vc.id))
    owner = bot.get_user(owner_id)

    embed = discord.Embed(title="📊 Room Info", color=0x5865F2)
    embed.add_field(name="Room Name", value=vc.name, inline=False)
    embed.add_field(name="Owner", value=owner.mention if owner else "Unknown", inline=False)
    embed.add_field(name="Users", value=len(vc.members), inline=False)

    await ctx.reply(embed=embed)

# .v close
@bot.command(name="close")
async def v_close(ctx):
    vc = get_owner_vc_by_user(ctx.author.id)
    if not vc:
        return await ctx.reply("❌ You don't own a room.")
    await vc.delete()
    data["voice_owners"].pop(str(vc.id), None)
    data.get("coowners", {}).pop(str(vc.id), None)
    save_data()
    await ctx.reply("❌ Room closed.")

# -------------------------
# .v claim
# -------------------------
@bot.command(name="claim")
async def v_claim(ctx):

    if not ctx.author.voice:
        return await ctx.reply("❌ يجب أن تكون داخل روم مؤقت.")

    vc = ctx.author.voice.channel
    vc_id = str(vc.id)

    if vc_id not in data["voice_owners"]:
        return await ctx.reply("❌ هذا ليس روم مؤقت.")

    current_owner = data["voice_owners"][vc_id]
    owner_member = ctx.guild.get_member(current_owner)

    if owner_member and owner_member in vc.members:
        return await ctx.reply("❌ لا يمكنك أخذ الملكية — المالك موجود داخل الروم.")

    data["voice_owners"][vc_id] = ctx.author.id
    data.get("coowners", {}).pop(vc_id, None)
    save_data()

    await ctx.reply(f"👑 تم أخذ ملكية الروم — المالك الجديد هو {ctx.author.mention}")

# -------------------------
# .v reject  (NEW)
# -------------------------
@bot.command(name="reject")
async def v_reject(ctx, member: discord.Member = None):

    if not member:
        return await ctx.reply("❌ Usage: `.v reject @user`")

    if not ctx.author.voice:
        return await ctx.reply("❌ يجب أن تكون داخل روم مؤقت.")

    vc = ctx.author.voice.channel
    vc_id = str(vc.id)

    if vc_id not in data["voice_owners"]:
        return await ctx.reply("❌ هذا ليس روم مؤقت.")

    owner = data["voice_owners"][vc_id]
    coowners = data.get("coowners", {}).get(vc_id, [])

    if ctx.author.id != owner and ctx.author.id not in coowners:
        return await ctx.reply("❌ فقط مالك الروم أو الكو أونر يمكنه استخدام هذا الأمر.")

    if not member.voice or member.voice.channel != vc:
        return await ctx.reply("❌ هذا المستخدم ليس داخل رومك.")

    try:
        await member.move_to(None)
        await ctx.reply(f"👢 تم طرد {member.mention} من الروم.")
    except:
        await ctx.reply("❌ لا يمكن طرده. تأكد من صلاحيات البوت (Move Members).")

# -------------------------
# .v commands
# -------------------------
@bot.command(name="commands")
async def v_commands(ctx):
    embed = discord.Embed(title="📜 All .v Commands", color=0x00ffe5)
    embed.add_field(name=".v name <new>", value="Rename room", inline=False)
    embed.add_field(name=".v lock", value="Lock room", inline=False)
    embed.add_field(name=".v unlock", value="Unlock room", inline=False)
    embed.add_field(name=".v hide", value="Hide room", inline=False)
    embed.add_field(name=".v unhide", value="Unhide room", inline=False)
    embed.add_field(name=".v transfer @user", value="Transfer ownership", inline=False)
    embed.add_field(name=".v addco @user", value="Add co-owner", inline=False)
    embed.add_field(name=".v info", value="Show room info", inline=False)
    embed.add_field(name=".v close", value="Close your room", inline=False)
    embed.add_field(name=".v claim", value="Claim a room if owner left", inline=False)
    embed.add_field(name=".v reject @user", value="Kick a user from your room", inline=False)

    await ctx.reply(embed=embed)

# -------------------------
# Run Bot
# -------------------------
if __name__ == "__main__":
    bot.run("TOKEN")
