# ---------------------------------------------------
# File Name: WhoIs!?.2.py
# Author: MyselfNeon
# Original Repo: https://github.com/MyselfNeon/NeonFilter-Bot
# GitHub: https://github.com/MyselfNeon/
# Telegram: https://t.me/MyelfNeon
# ---------------------------------------------------

import html
import io  # For in-memory handling
from datetime import datetime
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from pyrogram.errors import PeerIdInvalid, UsernameInvalid, UserNotParticipant
from info import ADMINS

# --- Helpers ---
def get_user_status(status):
    """Converts Pyrogram UserStatus enum to readable text."""
    status_map = {
        enums.UserStatus.ONLINE: "🟢 Online",
        enums.UserStatus.OFFLINE: "🔴 Offline",
        enums.UserStatus.RECENTLY: "🟡 Recently",
        enums.UserStatus.LAST_WEEK: "⚪ Last Week",
        enums.UserStatus.LAST_MONTH: "⚪ Last Month",
        enums.UserStatus.LONG_AGO: "⚫ Long Ago"
    }
    return status_map.get(status, "❓ Unknown")

WHOIS_TXT = """<b><i>
🕵️ Whois Pro Module

Usage:
• /whois @username
• /whois user_id
• Reply to a message with /whois
</i></b>"""

# --- Main Handler ---
@Client.on_message(filters.command("whois") & filters.private)
async def whois_user(client: Client, message: Message):
    # Visual feedback
    status_msg = await message.reply("<b><i>🎉 Fetching User Details ...</i></b>", quote=True)

    try:
        user = None
        user_id = None

        # 1. Identify Target
        if message.reply_to_message:
            user = message.reply_to_message.from_user
        elif len(message.command) > 1:
            target = message.command[1]
            if target.startswith("@"):
                try:
                    user = await client.get_users(target)
                except UsernameInvalid:
                    return await status_msg.edit("<b><i>❌ Invalid Username provided.</i></b>")
            else:
                try:
                    user_id = int(target)
                    user = await client.get_users(user_id)
                except ValueError:
                    return await status_msg.edit("<b><i>❌ Invalid User ID.</i></b>")
        else:
            return await status_msg.edit(WHOIS_TXT)

        if not user:
            return await status_msg.edit("<b><i>❌ Could not resolve user.</i></b>")

        # 2. Fetch Full Chat Details (Bio)
        try:
            full_chat = await client.get_chat(user.id)
            user_bio = full_chat.bio if full_chat.bio else "N/A"
        except Exception:
            user_bio = "N/A"

        # 3. Get Common Chats (Safe Mode)
        try:
            common_chats = await client.get_common_chats(user.id)
            common_count = len(common_chats)
        except Exception:
            common_count = 0

        # 4. Formatting Data (With HTML Escaping)
        first_name = html.escape(user.first_name or "")
        last_name = html.escape(user.last_name or "")
        full_name = f"{first_name} {last_name}".strip()
        user_username = html.escape(user.username or "None")
        safe_bio = html.escape(user_bio)
        
        # Profile Link
        user_link = f"<a href='tg://user?id={user.id}'>{full_name}</a>"

        # Status Logic
        u_status = get_user_status(user.status)
        
        # Tags
        tags = []
        if user.is_verified: tags.append("☑️ Verified")
        if user.is_scam: tags.append("🚫 Scam")
        if user.is_fake: tags.append("📵 Fake")
        if user.is_premium: tags.append("💎 Premium")
        if user.is_bot: tags.append("🤖 Bot")
        
        tags_text = " | ".join(tags) if tags else "Normal User"

        # Construct Text
        text = (
            f"<b><i>👤 USER INFORMATION</i></b>\n"
            f"<b><i>━━━━━━━━━━━━━━━━━━</i></b>\n"
            f"<b><i>🆔 ID :</i></b> <code>{user.id}</code>\n"
            f"<b><i>📛 Name : {user_link}</i></b>\n"
            f"<b><i>🖇️ Username : @{user_username}</i></b>\n"
            f"<b><i>🏳️ Tags : {tags_text}</i></b>\n"
            f"<b><i>🧾 DC ID : {user.dc_id or 'Unknown'}</i></b>\n"
            f"<b><i>🕓 Status : {u_status}</i></b>\n"
            f"<b><i>👥 Common Groups : {common_count}</i></b>\n"
            f"<b><i>🌐 Language : {user.language_code.upper() if user.language_code else 'Unknown'}</i></b>\n"
        )

        if safe_bio != "N/A":
            text += f"\n<b><i>💬 Bio:</i></b>\n<blockquote><b><i>{safe_bio}</i></b></blockquote>"

        # 5. Buttons
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("👤 Profile Link", url=f"tg://user?id={user.id}"),
                InlineKeyboardButton("❌ Close", callback_data="close_whois")
            ]
        ])

        # 6. Send Result
        if user.photo:
            # Download to Memory (RAM) then send.
            photo_file = await client.download_media(user.photo.big_file_id, in_memory=True)
            
            await message.reply_photo(
                photo=photo_file,
                caption=text,
                reply_markup=buttons,
                quote=True
            )
        else:
            await message.reply_text(
                text=text,
                reply_markup=buttons,
                quote=True,
                disable_web_page_preview=True
            )
            
        # If successful, delete the loading message
        await status_msg.delete()

    except PeerIdInvalid:
        await status_msg.edit("<b><i>❌ Error: I haven't met this user yet.</i></b>")
    except Exception as e:
        # Error message is plain text to avoid further HTML errors
        await status_msg.edit(f"⚠️ Error: {str(e)}")

# --- Callback ---
@Client.on_callback_query(filters.regex("close_whois"))
async def close_whois_callback(client, callback_query):
    await callback_query.message.delete()

# --- EDIT COMMANDS HERE ----
COMMANDS_TEXT = """
Start - 🚀 MyselfNeon Bot Start
help - 📘 Show Help Menu
index - 🗂️ Index File From Channel
setskip - ⏭️ Skip Files When Indexing
logs - 📜 To Get Recent Errors
stats - 📊 Files Stats In DB
connections - 🔗 See All Connected Groups
settings - ⚙️ Group Settings Menu
connect - 🔌 Connect To PM
disconnect - ❌ Disconnect From PM
delete - 🗑️ Delete Specific File From Index
deleteall - 💥 Delete All Indexed Files
info - 👤 Get User Info
id - 🆔 Get Telegram IDs
imdb - 🎬 Get Info From IMDB
search - 🔍 Search From Various Sources
chats - 💬 List of My Chats and IDs
leave - 👋 Leave From a Chat
disable - 🚫 Disable a Chat
enable - ✅ Re-Enable Chat
ban - 🔨 Ban a User
unban - 🤝 Unban User
channel - 📢 Total Connected Channels List
broadcast - 📡 Broadcast a Msg To All Users
grp_broadcast - 📣 Broadcast in Connected Groups
set_template - 📝 Set a Custom IMDB Template For Groups
deletefiles - 🧹 To Delete PreDVD and CamRip Files From Bot's Database
plan - 💎 Check Plan Details
myplan - 💳 Check Your Plan Stats
add_premium - ➕ Add User To Premium
remove_premium - ➖ Remove User From Premium
shortlink - ✂️ Set Your URL Shortner
setshortlinkon - 🟢 Turn ShortLink ON
setshortlinkoff - 🔴 Turn ShortLink OFF
shortlink_off - 🗒️ Check ShortLinks Details
set_tutorial - 👨‍🏫 Set URL Shortner Guide
remove_tutorial - 🗑️ Remove Tutorial
rename - ✏️ Rename Any File | Video | Audio
fsub - 🔒 Add Force Subscribe
nofsub - 🔓 Delete Force Subscribe
font - 🔠 Create Multiple Font Styles
repo - 💻 Find Any GitHub Repo
tts - 🗣️ Text To Audio Converter
ping - 🛜 Check Ping
genpw - 🔐 Generate Password
purgerequests - 🗑️ Delete All Join Requests
totalrequests - 🔢 Total Join Request
share - 📤 Share Your Texts
song - 🎵 Download Songs By Name Or Link
sticker - 🤩 Get ID of a Sticker
json - 💻 Get Raw JSON Details of a Message
telegraph - 📝 Telegraph Module
plink - 🖇️ Generate Permanent Link for Media
pbatch - 📦 Generate Permanent Batch Link for Multiple Files
batch - 📚 Create Batch Links for Media
dl - 📥 Download any URL Links as Media or Document File
stream - ▶️ Generate a Streamable Link for Media
set_caption - ✍️ Set Default Caption for Your Uploads
see_caption - 👁️ View Your Saved Caption
del_caption - 🗑️ Delete Your Saved Caption
set_thumb - 🖼️ Set Thumbnail for Uploads
view_thumb - 👁️ View Your Saved Thumbnail
del_thumb - 🗑️ Delete Your Saved Thumbnail
filter - ⚡ Add a Filter in Chat
filters - 📋 List All Filters in Chat
del - ❌ Delete a Specific Filter
delall - 🧨 Delete All Filters in Chat
gfilter - 🌍 Add a Global Filter
gfilters - 🌐 List All Global Filters
delg - 🗑️ Delete a Global Filter
delallg - 🧨 Delete All Global Filters
users - 👥 Get List of Users and IDs
whois - 🕵️ Get Full Details of Any User
request - 📩 Send a Movie/Series Request to All Admins
restart - 🔄 Restart Bot Server
"""

@Client.on_message(filters.command("setcmd") & filters.user(ADMINS))
async def set_commands(client, message):
    commands = []
    
    # Parse the text block line by line
    for line in COMMANDS_TEXT.strip().split("\n"):
        if "-" in line:
            cmd, desc = line.split("-", 1)
            commands.append(BotCommand(cmd.strip(), desc.strip()))

    if not commands:
        return await message.reply_text("❌ No commands found in the configuration list.")

    try:
        await client.set_bot_commands(commands)
        await message.reply_text(f"✅ **Success!** Updated {len(commands)} commands.")
    except Exception as e:
        await message.reply_text(f"❌ **Error:** `{e}`")

# MyselfNeon
# Don't Remove Credit 🥺
# Telegram Channel @NeonFiles
