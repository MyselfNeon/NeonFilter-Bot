# ---------------------------------------------------
# File Name: StreamPro.py
# Author: NeonAnurag
# GitHub: https://github.com/MyselfNeon/
# Telegram: https://t.me/MyelfNeon
# ---------------------------------------------------

import asyncio
import logging
import re
from urllib.parse import quote_plus

import motor.motor_asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from pyrogram.errors import FloodWait, MessageNotModified

# Custom Imports (Ensure these exist in your util/info files)
from info import STREAM_MODE, URL, LOG_CHANNEL, DATABASE_URI, DATABASE_NAME
from Neon.util.file_properties import get_name, get_hash, get_media_file_size
from Neon.util.human_readable import humanbytes

# --- LOGGER SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- MONGODB MANAGER ---
class StreamDatabase:
    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.files

    async def add_file(self, file_info):
        """Saves file information. Updates if exists, inserts if new."""
        # We use unique_id to prevent duplicates in DB
        await self.col.replace_one(
            {"unique_id": file_info["unique_id"]}, 
            file_info, 
            upsert=True
        )

    async def get_file_by_unique_id(self, unique_id):
        """Check if file already exists in DB to avoid re-uploading to Log Channel"""
        return await self.col.find_one({"unique_id": unique_id})

    async def delete_file(self, log_id):
        """Deletes file information based on Log Message ID"""
        await self.col.delete_one({"log_id": int(log_id)})

# Initialize Database
db = StreamDatabase(DATABASE_URI, DATABASE_NAME)

# --- HELPER FUNCTIONS ---
def get_file_details(message: Message):
    """Extracts media object and unique ID dynamically."""
    valid_types = [
        enums.MessageMediaType.VIDEO, 
        enums.MessageMediaType.DOCUMENT, 
        enums.MessageMediaType.AUDIO
    ]
    if message.media not in valid_types:
        return None, None
    
    media_type = message.media.value
    file = getattr(message, media_type)
    return file, media_type

# --- MAIN HANDLER ---
@Client.on_message(filters.private & filters.command(["stream", "link"]))
async def stream_start_handler(client: Client, message: Message):
    if not STREAM_MODE:
        return await message.reply("🚫 **System is currently in maintenance.**")

    # 1️⃣ Acquire Media
    target_msg = message.reply_to_message if (message.reply_to_message and message.reply_to_message.media) else None

    if not target_msg:
        try:
            ask = await client.ask(
                message.chat.id, 
                "**📤 Send me the file (Video/Document/Audio).**\n"
                "__I will generate a high-speed direct link.__",
                timeout=60,
                filters=filters.media
            )
            target_msg = ask
        except asyncio.TimeoutError:
            return await message.reply("⚠️ **Session Timed Out.** Type /stream to try again.")
        except Exception as e:
            return await message.reply(f"❌ **Error:** {e}")

    file_obj, media_type = get_file_details(target_msg)
    if not file_obj:
        return await message.reply("❌ **Unsupported Media Type.** Please send Video, Audio, or Document.")

    # 2️⃣ Processing
    status_msg = await message.reply_text("⏳ **Processing File...**")

    try:
        # Extract Meta Data
        file_unique_id = file_obj.file_unique_id
        file_id = file_obj.file_id
        filename = get_name(target_msg)
        filesize = humanbytes(get_media_file_size(target_msg))
        user = message.from_user

        # 🚀 SMART CHECK: Check if file exists in DB (De-duplication)
        existing_file = await db.get_file_by_unique_id(file_unique_id)
        
        if existing_file:
            # -- FAST PATH: File exists, just return credentials --
            log_id = existing_file['log_id']
            stream_link = existing_file['stream_link']
            download_link = existing_file['download_link']
            await status_msg.edit("♻️ **File found in database! Retrieving links...**")
        else:
            # -- SLOW PATH: New File, Upload to Log Channel --
            log_msg = await client.send_cached_media(
                chat_id=LOG_CHANNEL,
                file_id=file_id,
                caption=f"**User:** {user.mention} (`{user.id}`)\n**File:** `{filename}`\n**Size:** {filesize}"
            )
            
            log_id = log_msg.id
            file_name_encoded = quote_plus(filename)
            file_hash = get_hash(log_msg) # Your custom hash function

            stream_link = f"{URL}watch/{log_id}/{file_name_encoded}?hash={file_hash}"
            download_link = f"{URL}{log_id}/{file_name_encoded}?hash={file_hash}"

            # Save to MongoDB
            file_data = {
                "unique_id": file_unique_id, # Crucial for deduplication
                "user_id": user.id,
                "log_id": log_id,
                "file_name": filename,
                "file_size": filesize,
                "file_id": file_id,
                "media_type": media_type,
                "stream_link": stream_link,
                "download_link": download_link
            }
            await db.add_file(file_data)

        # 3️⃣ Construct Response
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🖥 Sᴛʀᴇᴀᴍ", url=stream_link),
                InlineKeyboardButton("📥 Dᴏᴡɴʟᴏᴀᴅ", url=download_link)
            ],
            [
                InlineKeyboardButton("🗑️ Rᴇᴠᴏᴋᴇ Lɪɴᴋ", callback_data=f"ask_revoke_{log_id}")
            ]
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
            reply_markup=buttons
        )

    except FloodWait as e:
        await asyncio.sleep(e.value)
        await message.reply(f"⚠️ **FloodWait:** Please wait {e.value} seconds.")
    except Exception as e:
        logger.error(f"Stream Error: {e}", exc_info=True)
        await status_msg.edit(f"**❌ An error occurred:** `{e}`")


# --- CALLBACKS: REVOKE FLOW ---
@Client.on_callback_query(filters.regex(r"^ask_revoke_"))
async def confirm_revoke_handler(client: Client, query: CallbackQuery):
    """Step 1: Ask for confirmation"""
    log_id = query.data.split("_")[-1]
    
    # Check permission (Optional: Only allow the user who created it)
    # For now, allowing anyone who has the message handle (standard behavior)
    
    btns = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes, Delete", callback_data=f"do_revoke_{log_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_revoke")
        ]
    ])
    await query.message.edit_reply_markup(reply_markup=btns)

@Client.on_callback_query(filters.regex(r"^cancel_revoke"))
async def cancel_revoke_handler(client: Client, query: CallbackQuery):
    """Step 2a: Restore original buttons (Recovery Mode)"""
    try:
        # Regex to find URLs in the message text
        urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', query.message.text)
        
        # Logic: Usually Stream Link contains 'watch', Download does not (or based on your logic)
        # Adjust logic if your URL structure changes
        st_link = next((u for u in urls if "watch" in u), None)
        dl_link = next((u for u in urls if "watch" not in u and u != st_link), None)

        if not st_link or not dl_link:
            await query.answer("⚠️ Cannot restore buttons automatically.", show_alert=True)
            return await query.message.delete()

        # Try to parse log_id from URL to restore the revoke button too
        # URL structure: DOMAIN/watch/12345/name...
        try:
            log_id_restored = st_link.split("/watch/")[1].split("/")[0]
            
            restored_btns = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🖥 Sᴛʀᴇᴀᴍ", url=st_link),
                    InlineKeyboardButton("📥 Dᴏᴡɴʟᴏᴀᴅ", url=dl_link)
                ],
                [
                    InlineKeyboardButton("🗑️ Rᴇᴠᴏᴋᴇ Lɪɴᴋ", callback_data=f"ask_revoke_{log_id_restored}")
                ]
            ])
            await query.message.edit_reply_markup(reply_markup=restored_btns)
        except:
            # Fallback if parsing fails: Just show links
            await query.message.edit_reply_markup(
                InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Link", url=dl_link)]])
            )
            
    except Exception as e:
        logger.error(f"Cancel Revoke Error: {e}")
        await query.answer("Error restoring view.", show_alert=True)


@Client.on_callback_query(filters.regex(r"^do_revoke_"))
async def execute_revoke_handler(client: Client, query: CallbackQuery):
    """Step 2b: Execute Deletion"""
    log_id = int(query.data.split("_")[-1])
    
    try:
        # 1. Delete from MongoDB
        await db.delete_file(log_id)
        
        # 2. Delete from Telegram Log Channel
        try:
            await client.delete_messages(chat_id=LOG_CHANNEL, message_ids=log_id)
        except Exception as e:
            logger.warning(f"Message {log_id} already deleted from channel or not found: {e}")

        # 3. Update User Message
        await query.message.edit_text(
            "<b>🚫 <i>Link Revoked.</i></b>\n\n"
            "__The file is no longer accessible via this link.__"
        )
    except Exception as e:
        logger.error(f"Revoke Failed: {e}")
        await query.answer("Failed to revoke link. Check logs.", show_alert=True)
        
