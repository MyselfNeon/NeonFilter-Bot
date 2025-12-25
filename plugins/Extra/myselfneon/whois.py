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
from config import OWNER_ID 

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
start - 𝘔𝘺𝘴𝘦𝘭𝘧𝘕𝘦𝘰𝘯 𝘉𝘰𝘵 𝘚𝘵𝘢𝘳𝘵
help - 𝘚𝘩𝘰𝘸 𝘏𝘦𝘭𝘱 𝘔𝘦𝘯𝘶
index - 𝘐𝘯𝘥𝘦𝘹 𝘍𝘪𝘭𝘦 𝘍𝘳𝘰𝘮 𝘊𝘩𝘢𝘯𝘯𝘦𝘭
setskip - 𝘚𝘬𝘪𝘱 𝘍𝘪𝘭𝘦𝘴 𝘞𝘩𝘦𝘯 𝘐𝘯𝘥𝘦𝘹𝘪𝘯𝘨
logs - 𝘛𝘰 𝘎𝘦𝘵 𝘙𝘦𝘤𝘦𝘯𝘵 𝘌𝘳𝘳𝘰𝘳𝘴
stats - 𝘍𝘪𝘭𝘦𝘴 𝘚𝘵𝘢𝘵𝘴 𝘐𝘯 𝘋𝘉
connections - 𝘚𝘦𝘦 𝘈𝘭𝘭 𝘊𝘰𝘯𝘯𝘦𝘤𝘵𝘦𝘥 𝘎𝘳𝘰𝘶𝘱𝘴
settings - 𝘎𝘳𝘰𝘶𝘱 𝘚𝘦𝘵𝘵𝘪𝘯𝘨𝘴 𝘔𝘦𝘯𝘶
connect - 𝘊𝘰𝘯𝘯𝘦𝘤𝘵 𝘛𝘰 𝘗𝘔
disconnect - 𝘋𝘪𝘴𝘤𝘰𝘯𝘯𝘦𝘤𝘵 𝘍𝘳𝘰𝘮 𝘗𝘔
delete - 𝘋𝘦𝘭𝘦𝘵𝘦 𝘚𝘱𝘦𝘤𝘪𝘧𝘪𝘤 𝘍𝘪𝘭𝘦 𝘍𝘳𝘰𝘮 𝘐𝘯𝘥𝘦𝘹
deleteall - 𝘋𝘦𝘭𝘦𝘵𝘦 𝘈𝘭𝘭 𝘐𝘯𝘥𝘦𝘹𝘦𝘥 𝘍𝘪𝘭𝘦𝘴
info - 𝘎𝘦𝘵 𝘜𝘴𝘦𝘳 𝘐𝘯𝘧𝘰
id - 𝘎𝘦𝘵 𝘛𝘦𝘭𝘦𝘨𝘳𝘢𝘮 𝘐𝘋𝘴
imdb - 𝘎𝘦𝘵 𝘐𝘯𝘧𝘰 𝘍𝘳𝘰𝘮 𝘐𝘔𝘋𝘉
search - 𝘚𝘦𝘢𝘳𝘤𝘩 𝘍𝘳𝘰𝘮 𝘝𝘢𝘳𝘪𝘰𝘶𝘴 𝘚𝘰𝘶𝘳𝘤𝘦𝘴
chats - 𝘓𝘪𝘴𝘵 𝘰𝘧 𝘔𝘺 𝘊𝘩𝘢𝘵𝘴 𝘢𝘯𝘥 𝘐𝘋𝘴
leave - 𝘓𝘦𝘢𝘷𝘦 𝘍𝘳𝘰𝘮 𝘢 𝘊𝘩𝘢𝘵
disable - 𝘋𝘪𝘴𝘢𝘣𝘭𝘦 𝘢 𝘊𝘩𝘢𝘵
enable - 𝘙𝘦-𝘌𝘯𝘢𝘣𝘭𝘦 𝘊𝘩𝘢𝘵
ban - 𝘉𝘢𝘯 𝘢 𝘜𝘴𝘦𝘳
unban - 𝘜𝘯𝘣𝘢𝘯 𝘜𝘴𝘦𝘳
channel - 𝘛𝘰𝘵𝘢𝘭 𝘊𝘰𝘯𝘯𝘦𝘤𝘵𝘦𝘥 𝘊𝘩𝘢𝘯𝘯𝘦𝘭𝘴 𝘓𝘪𝘴𝘵
broadcast - 𝘉𝘳𝘰𝘢𝘥𝘤𝘢𝘴𝘵 𝘢 𝘔𝘴𝘨 𝘛𝘰 𝘈𝘭𝘭 𝘜𝘴𝘦𝘳𝘴
grp_broadcast - 𝘉𝘳𝘰𝘢𝘥𝘤𝘢𝘴𝘵 𝘪𝘯 𝘊𝘰𝘯𝘯𝘦𝘤𝘵𝘦𝘥 𝘎𝘳𝘰𝘶𝘱𝘴
set_template - 𝘚𝘦𝘵 𝘢 𝘊𝘶𝘴𝘵𝘰𝘮 𝘐𝘔𝘋𝘉 𝘛𝘦𝘮𝘱𝘭𝘢𝘵𝘦 𝘍𝘰𝘳 𝘎𝘳𝘰𝘶𝘱𝘴
deletefiles - 𝘛𝘰 𝘋𝘦𝘭𝘦𝘵𝘦 𝘗𝘳𝘦𝘋𝘝𝘋 𝘢𝘯𝘥 𝘊𝘢𝘮𝘙𝘪𝘱 𝘍𝘪𝘭𝘦𝘴 𝘍𝘳𝘰𝘮 𝘉𝘰𝘵'𝘴 𝘋𝘢𝘵𝘢𝘣𝘢𝘴𝘦
plan - 𝘊𝘩𝘦𝘤𝘬 𝘗𝘭𝘢𝘯 𝘋𝘦𝘵𝘢𝘪𝘭𝘴
myplan - 𝘊𝘩𝘦𝘤𝘬 𝘠𝘰𝘶𝘳 𝘗𝘭𝘢𝘯 𝘚𝘵𝘢𝘵𝘴
add_premium - 𝘈𝘥𝘥 𝘜𝘴𝘦𝘳 𝘛𝘰 𝘗𝘳𝘦𝘮𝘪𝘶𝘮
remove_premium - 𝘙𝘦𝘮𝘰𝘷𝘦 𝘜𝘴𝘦𝘳 𝘍𝘳𝘰𝘮 𝘗𝘳𝘦𝘮𝘪𝘶𝘮
shortlink - 𝘚𝘦𝘵 𝘠𝘰𝘶𝘳 𝘜𝘙𝘓 𝘚𝘩𝘰𝘳𝘵𝘯𝘦𝘳
setshortlinkon - 𝘛𝘶𝘳𝘯 𝘚𝘩𝘰𝘳𝘵𝘓𝘪𝘯𝘬 𝘖𝘕
setshortlinkoff - 𝘛𝘶𝘳𝘯 𝘚𝘩𝘰𝘳𝘵𝘓𝘪𝘯𝘬 𝘖𝘍𝘍
shortlink_off - 𝘊𝘩𝘦𝘤𝘬 𝘚𝘩𝘰𝘳𝘵𝘓𝘪𝘯𝘬𝘴 𝘋𝘦𝘵𝘢𝘪𝘭𝘴
set_tutorial - 𝘚𝘦𝘵 𝘜𝘙𝘓 𝘚𝘩𝘰𝘳𝘵𝘯𝘦𝘳 𝘎𝘶𝘪𝘥𝘦
remove_tutorial - 𝘙𝘦𝘮𝘰𝘷𝘦 𝘛𝘶𝘵𝘰𝘳𝘪𝘢𝘭
rename - 𝘙𝘦𝘯𝘢𝘮𝘦 𝘈𝘯𝘺 𝘍𝘪𝘭𝘦 | 𝘝𝘪𝘥𝘦𝘰 | 𝘈𝘶𝘥𝘪𝘰
fsub - 𝘈𝘥𝘥 𝘍𝘰𝘳𝘤𝘦 𝘚𝘶𝘣𝘴𝘤𝘳𝘪𝘣𝘦
nofsub - 𝘋𝘦𝘭𝘦𝘵𝘦 𝘍𝘰𝘳𝘤𝘦 𝘚𝘶𝘣𝘴𝘤𝘳𝘪𝘣𝘦
font - 𝘊𝘳𝘦𝘢𝘵𝘦 𝘔𝘶𝘭𝘵𝘪𝘱𝘭𝘦 𝘍𝘰𝘯𝘵 𝘚𝘵𝘺𝘭𝘦𝘴
repo - 𝘍𝘪𝘯𝘥 𝘈𝘯𝘺 𝘎𝘪𝘵𝘏𝘶𝘣 𝘙𝘦𝘱𝘰
tts - 𝘛𝘦𝘹𝘵 𝘛𝘰 𝘈𝘶𝘥𝘪𝘰 𝘊𝘰𝘯𝘷𝘦𝘳𝘵𝘦𝘳
ping - 𝘊𝘩𝘦𝘤𝘬 𝘗𝘪𝘯𝘨
genpw - 𝘎𝘦𝘯𝘦𝘳𝘢𝘵𝘦 𝘗𝘢𝘴𝘴𝘸𝘰𝘳𝘥
purgerequests - 𝘋𝘦𝘭𝘦𝘵𝘦 𝘈𝘭𝘭 𝘑𝘰𝘪𝘯 𝘙𝘦𝘲𝘶𝘦𝘴𝘵𝘴
totalrequests - 𝘛𝘰𝘵𝘢𝘭 𝘑𝘰𝘪𝘯 𝘙𝘦𝘲𝘶𝘦𝘴𝘵
share - 𝘚𝘩𝘢𝘳𝘦 𝘠𝘰𝘶𝘳 𝘛𝘦𝘹𝘵𝘴
song - 𝘋𝘰𝘸𝘯𝘭𝘰𝘢𝘥 𝘚𝘰𝘯𝘨𝘴 𝘉𝘺 𝘕𝘢𝘮𝘦 𝘖𝘳 𝘓𝘪𝘯𝘬
sticker - 𝘎𝘦𝘵 𝘐𝘋 𝘰𝘧 𝘢 𝘚𝘵𝘪𝘤𝘬𝘦𝘳
json - 𝘎𝘦𝘵 𝘙𝘢𝘸 𝘑𝘚𝘖𝘕 𝘋𝘦𝘵𝘢𝘪𝘭𝘴 𝘰𝘧 𝘢 𝘔𝘦𝘴𝘴𝘢𝘨𝘦
telegraph - 𝘛𝘦𝘭𝘦𝘨𝘳𝘢𝘱𝘩 𝘔𝘰𝘥𝘶𝘭𝘦
plink - 𝘎𝘦𝘯𝘦𝘳𝘢𝘵𝘦 𝘗𝘦𝘳𝘮𝘢𝘯𝘦𝘯𝘵 𝘓𝘪𝘯𝘬 𝘧𝘰𝘳 𝘔𝘦𝘥𝘪𝘢
pbatch - 𝘎𝘦𝘯𝘦𝘳𝘢𝘵𝘦 𝘗𝘦𝘳𝘮𝘢𝘯𝘦𝘯𝘵 𝘉𝘢𝘵𝘤𝘩 𝘓𝘪𝘯𝘬 𝘧𝘰𝘳 𝘔𝘶𝘭𝘵𝘪𝘱𝘭𝘦 𝘍𝘪𝘭𝘦𝘴
batch - 𝘊𝘳𝘦𝘢𝘵𝘦 𝘉𝘢𝘵𝘤𝘩 𝘓𝘪𝘯𝘬𝘴 𝘧𝘰𝘳 𝘔𝘦𝘥𝘪𝘢
dl - 𝘋𝘰𝘸𝘯𝘭𝘰𝘢𝘥 𝘢𝘯𝘺 𝘜𝘙𝘓 𝘓𝘪𝘯𝘬𝘴 𝘢𝘴 𝘔𝘦𝘥𝘪𝘢 𝘰𝘳 𝘋𝘰𝘤𝘶𝘮𝘦𝘯𝘵 𝘍𝘪𝘭𝘦
stream - 𝘎𝘦𝘯𝘦𝘳𝘢𝘵𝘦 𝘢 𝘚𝘵𝘳𝘦𝘢𝘮𝘢𝘣𝘭𝘦 𝘓𝘪𝘯𝘬 𝘧𝘰𝘳 𝘔𝘦𝘥𝘪𝘢
set_caption - 𝘚𝘦𝘵 𝘋𝘦𝘧𝘢𝘶𝘭𝘵 𝘊𝘢𝘱𝘵𝘪𝘰𝘯 𝘧𝘰𝘳 𝘠𝘰𝘶𝘳 𝘜𝘱𝘭𝘰𝘢𝘥𝘴
see_caption - 𝘝𝘪𝘦𝘸 𝘠𝘰𝘶𝘳 𝘚𝘢𝘷𝘦𝘥 𝘊𝘢𝘱𝘵𝘪𝘰𝘯
del_caption - 𝘋𝘦𝘭𝘦𝘵𝘦 𝘠𝘰𝘶𝘳 𝘚𝘢𝘷𝘦𝘥 𝘊𝘢𝘱𝘵𝘪𝘰𝘯
set_thumb - 𝘚𝘦𝘵 𝘛𝘩𝘶𝘮𝘣𝘯𝘢𝘪𝘭 𝘧𝘰𝘳 𝘜𝘱𝘭𝘰𝘢𝘥𝘴
view_thumb - 𝘝𝘪𝘦𝘸 𝘠𝘰𝘶𝘳 𝘚𝘢𝘷𝘦𝘥 𝘛𝘩𝘶𝘮𝘣𝘯𝘢𝘪𝘭
del_thumb - 𝘋𝘦𝘭𝘦𝘵𝘦 𝘠𝘰𝘶𝘳 𝘚𝘢𝘷𝘦𝘥 𝘛𝘩𝘶𝘮𝘣𝘯𝘢𝘪𝘭
filter - 𝘈𝘥𝘥 𝘢 𝘍𝘪𝘭𝘵𝘦𝘳 𝘪𝘯 𝘊𝘩𝘢𝘵
filters - 𝘓𝘪𝘴𝘵 𝘈𝘭𝘭 𝘍𝘪𝘭𝘵𝘦𝘳𝘴 𝘪𝘯 𝘊𝘩𝘢𝘵
del - 𝘋𝘦𝘭𝘦𝘵𝘦 𝘢 𝘚𝘱𝘦𝘤𝘪𝘧𝘪𝘤 𝘍𝘪𝘭𝘵𝘦𝘳
delall - 𝘋𝘦𝘭𝘦𝘵𝘦 𝘈𝘭𝘭 𝘍𝘪𝘭𝘵𝘦𝘳𝘴 𝘪𝘯 𝘊𝘩𝘢𝘵
gfilter - 𝘈𝘥𝘥 𝘢 𝘎𝘭𝘰𝘣𝘢𝘭 𝘍𝘪𝘭𝘵𝘦𝘳
gfilters - 𝘓𝘪𝘴𝘵 𝘈𝘭𝘭 𝘎𝘭𝘰𝘣𝘢𝘭 𝘍𝘪𝘭𝘵𝘦𝘳𝘴
delg - 𝘋𝘦𝘭𝘦𝘵𝘦 𝘢 𝘎𝘭𝘰𝘣𝘢𝘭 𝘍𝘪𝘭𝘵𝘦𝘳
delallg - 𝘋𝘦𝘭𝘦𝘵𝘦 𝘈𝘭𝘭 𝘎𝘭𝘰𝘣𝘢𝘭 𝘍𝘪𝘭𝘵𝘦𝘳𝘴
users - 𝘎𝘦𝘵 𝘓𝘪𝘴𝘵 𝘰𝘧 𝘜𝘴𝘦𝘳𝘴 𝘢𝘯𝘥 𝘐𝘋𝘴
whois - 𝘎𝘦𝘵 𝘍𝘶𝘭𝘭 𝘋𝘦𝘵𝘢𝘪𝘭𝘴 𝘰𝘧 𝘈𝘯𝘺 𝘜𝘴𝘦𝘳
request - 𝘚𝘦𝘯𝘥 𝘢 𝘔𝘰𝘷𝘪𝘦/𝘚𝘦𝘳𝘪𝘦𝘴 𝘙𝘦𝘲𝘶𝘦𝘴𝘵 𝘵𝘰 𝘈𝘭𝘭 𝘈𝘥𝘮𝘪𝘯𝘴
restart - 𝘙𝘦𝘴𝘵𝘢𝘳𝘵 𝘉𝘰𝘵 𝘚𝘦𝘳𝘷𝘦𝘳
"""

@Client.on_message(filters.command("setcmd") & filters.user(OWNER_ID))
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
