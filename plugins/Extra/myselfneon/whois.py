# ---------------------------------------------------
# File Name: WhoIs??-V0.2.py
# Author: MyselfNeon
# GitHub: https://github.com/MyselfNeon/
# Telegram: https://t.me/MyelfNeon
# ---------------------------------------------------

import os
from datetime import datetime
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import PeerIdInvalid, UsernameInvalid, UserNotParticipant

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

# ====================== MAIN HANDLER ======================
@Client.on_message(filters.command("whois") & filters.private)
async def whois_user(client: Client, message: Message):
    # Visual feedback that bot is working (Bold + Italic)
    status_msg = await message.reply("<b><i>⚡ Fetching user details...</i></b>", quote=True)

    try:
        user = None
        user_id = None

        # 1. IDENTIFY TARGET
        if message.reply_to_message:
            user = message.reply_to_message.from_user
        elif len(message.command) > 1:
            target = message.command[1]
            # Strip @ if present
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
            # If no args, show help
            return await status_msg.edit(WHOIS_TXT)

        if not user:
            return await status_msg.edit("<b><i>❌ Could not resolve user.</i></b>")

        # 2. FETCH FULL CHAT DETAILS (For Bio & Common Chats)
        try:
            full_chat = await client.get_chat(user.id)
            user_bio = full_chat.bio if full_chat.bio else "N/A"
        except Exception:
            user_bio = "N/A"

        # 3. GET COMMON CHATS COUNT
        try:
            common_chats = await client.get_common_chats(user.id)
            common_count = len(common_chats)
        except Exception:
            common_count = 0

        # 4. FORMATTING DATA
        # Name handling
        full_name = user.first_name
        if user.last_name:
            full_name += f" {user.last_name}"
        
        # Profile Link (Mention) -> Kept inside bold/italic tags
        user_link = f"<a href='tg://user?id={user.id}'>{full_name}</a>"

        # Status Logic
        u_status = get_user_status(user.status)
        
        # Verification Badges
        tags = []
        if user.is_verified: tags.append("☑️ Verified")
        if user.is_scam: tags.append("🚫 Scam")
        if user.is_fake: tags.append("📵 Fake")
        if user.is_premium: tags.append("💎 Premium")
        if user.is_bot: tags.append("🤖 Bot")
        
        tags_text = " | ".join(tags) if tags else "Normal User"

        # Construct the text (ALL BOLD + ITALIC)
        # Note: <code> tags are nested inside <b><i> but usually render monospaced.
        text = (
            f"<b><i>👤 USER INFORMATION</i></b>\n"
            f"<b><i>━━━━━━━━━━━━━━━━━━</i></b>\n"
            f"<b><i>🆔 ID:</i></b> <code>{user.id}</code>\n"
            f"<b><i>📛 Name: {user_link}</i></b>\n"
            f"<b><i>🖇️ Username: @{user.username if user.username else 'None'}</i></b>\n"
            f"<b><i>🏳️ Tags: {tags_text}</i></b>\n"
            f"<b><i>🧾 DC ID: {user.dc_id or 'Unknown'}</i></b>\n"
            f"<b><i>🕓 Status: {u_status}</i></b>\n"
            f"<b><i>👥 Common Groups: {common_count}</i></b>\n"
            f"<b><i>🌐 Language: {user.language_code.upper() if user.language_code else 'Unknown'}</i></b>\n"
        )

        # Add Bio if it exists
        if user_bio != "N/A":
            text += f"\n<b><i>💬 Bio:</i></b>\n<blockquote><b><i>{user_bio}</i></b></blockquote>"

        # 5. BUTTONS
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("👤 Profile Link", url=f"tg://user?id={user.id}"),
                InlineKeyboardButton("🗑️ Close", callback_data="close_whois")
            ]
        ])

        # 6. SEND RESULT
        # Delete processing message
        await status_msg.delete()

        # Send Photo (Using file_id for speed) or just Text
        if user.photo:
            await message.reply_photo(
                photo=user.photo.big_file_id,
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

    except PeerIdInvalid:
        await status_msg.edit("<b><i>❌ Error: I haven't met this user yet (PeerIdInvalid).</i></b>")
    except Exception as e:
        await status_msg.edit(f"<b><i>⚠️ Error:</i></b>\n<blockquote><b><i>{str(e)}</i></b></blockquote>")

# ====================== CALLBACK FOR CLOSE BUTTON ======================
@Client.on_callback_query(filters.regex("close_whois"))
async def close_whois_callback(client, callback_query):
    await callback_query.message.delete()
