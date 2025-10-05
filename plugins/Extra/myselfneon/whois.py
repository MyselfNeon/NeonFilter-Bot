# ====================== PLUGINS/WHOIS.PY ======================
from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaPhoto
from datetime import datetime
import os
import asyncio

WHOIS_TXT = """<b>📇 ᴡʜᴏɪꜱ ᴍᴏᴅᴜʟᴇ</b>

__Use to get Telegram user details.__

<b>Usage:</b>
• /whois @username
• /whois user_id
• Reply to a message with /whois
"""

# ====================== HELP COMMAND ======================
@Client.on_message(filters.command("whoishelp") & filters.private)
async def whois_help(client: Client, message: Message):
    await message.reply(WHOIS_TXT)

# ====================== MAIN WHOIS HANDLER ======================
@Client.on_message(filters.command("whois") & filters.private)
async def whois_user(client: Client, message: Message):
    try:
        # Determine target user
        if message.reply_to_message:
            user = message.reply_to_message.from_user
        elif len(message.command) > 1:
            target = message.command[1]
            if target.startswith("@"):
                user = await client.get_users(target)
            else:
                user_id = int(target)
                user = await client.get_users(user_id)
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

        text += f"🤖 <b>Bot:</b> {'Yes' if user.is_bot else 'No'}\n"
        text += f"✅ <b>Verified:</b> {'Yes' if user.is_verified else 'No'}\n"
        text += f"💎 <b>Premium:</b> {'Yes' if getattr(user,'is_premium',False) else 'No'}\n"

        # Language
        if getattr(user, "language_code", None):
            text += f"🌐 <b>Language:</b> {user.language_code.upper()}\n"

        # Bio
        bio = "N/A"
        try:
            chat = await client.get_chat(user.id)
            bio = getattr(chat, "bio", "N/A") or "N/A"
        except Exception:
            pass
        text += f"💬 <b>Bio:</b> {bio}\n"

        # Online status
        status = getattr(user, "status", "Hidden / Unavailable")
        text += f"🕓 <b>Status:</b> {status}\n"

        # ====================== PROFILE PHOTOS ======================
        photos = await client.get_profile_photos(user.id)
        total_photos = getattr(photos, "total_count", 0)

        main_photo_path = None
        other_photos_paths = []

        if total_photos > 0:
            # Main profile photo (first one)
            main_photo_path = await client.download_media(photos.photos[0][-1].file_id, file_name=f"whois_{user.id}_main.jpg")

            # Rest of the photos
            for photo_set in photos.photos[1:]:
                largest_photo = photo_set[-1]  # choose largest size
                path = await client.download_media(largest_photo.file_id, file_name=f"whois_{user.id}_{largest_photo.file_id}.jpg")
                other_photos_paths.append(path)

        # ====================== SEND MAIN INFO ======================
        if main_photo_path:
            await message.reply_photo(photo=main_photo_path, caption=text)
            try: os.remove(main_photo_path)
            except: pass
        else:
            await message.reply(text)

        # ====================== SEND OTHER PHOTOS AS ALBUM ======================
        if other_photos_paths:
            media_group = [InputMediaPhoto(f) for f in other_photos_paths]
            await client.send_media_group(chat_id=message.chat.id, media=media_group)
            # cleanup
            for f in other_photos_paths:
                try: os.remove(f)
                except: pass

    except Exception as e:
        await message.reply(f"⚠️ Error: {e}")
