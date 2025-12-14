# ---------------------------------------------------
# File Name: StreamPro.py
# Author: NeonAnurag
# GitHub: https://github.com/MyselfNeon/
# Telegram: https://t.me/MyelfNeon
# ---------------------------------------------------

from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from info import STREAM_MODE, URL, LOG_CHANNEL
from urllib.parse import quote_plus
from Neon.util.file_properties import get_name, get_hash, get_media_file_size
from Neon.util.human_readable import humanbytes
import asyncio

@Client.on_message(filters.private & filters.command(["stream", "link", "gen"]))
async def stream_start(client: Client, message: Message):
    if not STREAM_MODE:
        return await message.reply("🚫 **Streaming Mode is Disabled via Config.**")

    # --- 1️⃣ INPUT HANDLING (Reply vs Interactive) ---
    target_msg = None
    
    if message.reply_to_message and message.reply_to_message.media:
        target_msg = message.reply_to_message
    else:
        # Interactive Mode: Ask user to send file
        try:
            ask_msg = await client.ask(
                message.chat.id, 
                "**__Now send me your File, Video or Audio.__**\n"
                "__I will generate a direct Stream & Download link.__",
                timeout=60,
                filters=filters.media
            )
            if ask_msg.media:
                target_msg = ask_msg
        except asyncio.TimeoutError:
            return await message.reply("❌ **Time Up!** Please run the command again.")
        except Exception as e:
            return await message.reply(f"❌ **Error:** {e}")

    # --- 2️⃣ VALIDATION ---
    if not target_msg:
        return await message.reply("**❌ No Media Found!**")
        
    # Support Video, Document, and Audio
    valid_types = [
        enums.MessageMediaType.VIDEO, 
        enums.MessageMediaType.DOCUMENT, 
        enums.MessageMediaType.AUDIO
    ]
    if target_msg.media not in valid_types:
        return await message.reply("**❌ Unsupported Media Type.**\n__Please Send: Video, Document, or Audio.__")

    # --- 3️⃣ PROCESSING ---
    status_msg = await message.reply_text("🔄 **Generating Link...**")

    try:
        # Dynamic Attribute Extraction (Fixes your getattr issue)
        media_type = target_msg.media.value  # e.g., "video", "document"
        file = getattr(target_msg, media_type)
        
        filename = get_name(target_msg)
        filesize = humanbytes(get_media_file_size(target_msg))
        fileid = file.file_id
        user = message.from_user

        # Send to Log Channel
        log_msg = await client.send_cached_media(
            chat_id=LOG_CHANNEL,
            file_id=fileid,
            caption=f"**User:** {user.mention} (`{user.id}`)\n**File:** `{filename}`"
        )

        # Generate Data
        file_name_encoded = quote_plus(filename)
        file_hash = get_hash(log_msg)

        stream_link = f"{URL}watch/{log_msg.id}/{file_name_encoded}?hash={file_hash}"
        download_link = f"{URL}{log_msg.id}/{file_name_encoded}?hash={file_hash}"

        # --- 4️⃣ UI RESPONSE ---
        # Button for Log Channel (Admins can see who generated it)
        await log_msg.edit_reply_markup(
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚀 Fᴀsᴛ Dᴏᴡɴʟᴏᴀᴅ", url=download_link),
                 InlineKeyboardButton("🖥 Wᴀᴛᴄʜ Oɴʟɪɴᴇ", url=stream_link)]
            ])
        )

        # Buttons for User
        user_buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🖥 Sᴛʀᴇᴀᴍ", url=stream_link),
             InlineKeyboardButton("📥 Dᴏᴡɴʟᴏᴀᴅ", url=download_link)]
        ])

        msg_text = (
            "<b><i><u>⚡ 𝗟𝗶𝗻𝗸 𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗲𝗱 𝗦𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆!</u></i></b>\n\n"
            f"<b><i>📂 File Name:</b>\n{filename}</i>\n"
            f"<b><i>📦 File Size:</b> {filesize}</i>\n\n"
            f"<b><i>📥 Download:</i></b>\n<blockquote expandable><code>{download_link}</code></blockquote>\n"
            f"<b><i>🖥 Watch:</i></b>\n<blockquote expandable><code>{stream_link}</code></blockquote>\n\n"
            "<b><i>⚠️ Note: Link will not expire unless deleted.</i></b>"
        )

        await status_msg.edit(
            text=msg_text,
            disable_web_page_preview=True,
            reply_markup=user_buttons
        )

    except Exception as e:
        await status_msg.edit(f"**❌ Critical Error:** `{e}`")
        # Optional: Print traceback to console for debugging
        print(f"Stream Gen Error: {e}")
        
