# ====================== PLUGINS/WHOIS.PY ======================
from pyrogram import Client, filters
from pyrogram.types import Message
from datetime import datetime

WHOIS_TXT = """<b>📇 ᴡʜᴏɪꜱ ᴍᴏᴅᴜʟᴇ</b>

__Use to get Telegram user details.__

<b>Usage:</b>
• /whois @username
• /whois user_id
• Reply to a message with /whois
"""

# ====================== MAIN HANDLER ======================
@Client.on_message(filters.command("whois") & filters.private)
async def whois_user(client: Client, message: Message):
    try:
        # determine target
        if message.reply_to_message:
            user = message.reply_to_message.from_user
        elif len(message.command) > 1:
            target = message.command[1]
            if target.startswith("@"):
                user = await client.get_users(target)
            else:
                try:
                    user_id = int(target)
                    user = await client.get_users(user_id)
                except ValueError:
                    return await message.reply("**❌ Invalid user ID or username!**")
        else:
            return await message.reply(WHOIS_TXT)

        # ====================== BUILD USER INFO ======================
        text = f"<b>👤 USER INFO</b>\n\n"
        text += f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
        text += f"📛 <b>Name:</b> {user.first_name or 'N/A'}"
        if user.last_name:
            text += f" {user.last_name}\n"
        else:
            text += "\n"

        if user.username:
            text += f"🔗 <b>Username:</b> @{user.username}\n"
        else:
            text += "🔗 <b>Username:</b> None\n"

        text += f"🧾 <b>DC ID:</b> {user.dc_id or 'Unknown'}\n"
        text += f"🤖 <b>Is Bot:</b> {'Yes' if user.is_bot else 'No'}\n"
        text += f"✅ <b>Is Verified:</b> {'Yes' if user.is_verified else 'No'}\n"
        text += f"🚫 <b>Is Scam:</b> {'Yes' if user.is_scam else 'No'}\n"
        text += f"📵 <b>Is Fake:</b> {'Yes' if user.is_fake else 'No'}\n"

        # premium check
        text += f"💎 <b>Is Premium:</b> {'Yes' if getattr(user, 'is_premium', False) else 'No'}\n"

        # language, if available
        if getattr(user, "language_code", None):
            text += f"🌐 <b>Language:</b> {user.language_code.upper()}\n"

        # status line
        if getattr(user, "status", None):
            text += f"🕓 <b>Status:</b> {user.status}\n"

        # bio if retrievable
        try:
            full = await client.get_chat(user.id)
            if getattr(full, "bio", None):
                text += f"\n💬 <b>Bio:</b>\n{full.bio}"
        except Exception:
            pass

        # last seen formatting
        if getattr(user, "last_online_date", None):
            time_ago = datetime.fromtimestamp(user.last_online_date)
            text += f"\n🕰️ <b>Last Online:</b> {time_ago.strftime('%Y-%m-%d %H:%M:%S')}"

        # profile photo (if available)
        if user.photo:
            photo = await client.download_media(user.photo.big_file_id)
            await message.reply_photo(photo, caption=text)
        else:
            await message.reply(text)

    except Exception as e:
        await message.reply(f"**⚠️ Error:** `{e}`\n\nMight be an invalid username or restricted account.")

# ====================== HELP COMMAND ======================
@Client.on_message(filters.command("whoishelp") & filters.private)
async def whois_help(client: Client, message: Message):
    await message.reply(WHOIS_TXT)
