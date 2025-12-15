# ---------------------------------------------------
# File Name: StreamPro.py
# Author: NeonAnurag
# GitHub: https://github.com/MyselfNeon/
# Telegram: https://t.me/MyelfNeon
# ---------------------------------------------------

from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from info import STREAM_MODE, URL, LOG_CHANNEL, DATABASE_URI, DATABASE_NAME
from urllib.parse import quote_plus
from Neon.util.file_properties import get_name, get_hash, get_media_file_size
from Neon.util.human_readable import humanbytes
import asyncio
import re
import motor.motor_asyncio

# --- MONGODB SETUP ---
class Database:
    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.files

    async def add_file(self, file_info):
        """Saves file information to MongoDB"""
        await self.col.insert_one(file_info)

    async def delete_file(self, log_id):
        """Deletes file information from MongoDB based on Log ID"""
        await self.col.delete_one({"log_id": log_id})

    async def get_file(self, log_id):
        """(Optional) Retrieve file info"""
        return await self.col.find_one({"log_id": log_id})

# Initialize Database
db = Database(DATABASE_URI, DATABASE_NAME)


@Client.on_message(filters.private & filters.command(["stream"]))
async def stream_start(client: Client, message: Message):
    if not STREAM_MODE:
        return await message.reply("🚫 **Streaming Mode is Disabled via Config.**")

    # --- 1️⃣ INPUT HANDLING ---
    target_msg = None
    if message.reply_to_message and message.reply_to_message.media:
        target_msg = message.reply_to_message
    else:
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

    if not target_msg:
        return await message.reply("**❌ No Media Found!**")
        
    valid_types = [enums.MessageMediaType.VIDEO, enums.MessageMediaType.DOCUMENT, enums.MessageMediaType.AUDIO]
    if target_msg.media not in valid_types:
        return await message.reply("**❌ Unsupported Media Type.**")

    # --- 2️⃣ PROCESSING ---
    status_msg = await message.reply_text("🔄 **Generating Link & Saving to DB...**")

    try:
        media_type = target_msg.media.value
        file = getattr(target_msg, media_type)
        filename = get_name(target_msg)
        filesize = humanbytes(get_media_file_size(target_msg))
        fileid = file.file_id
        user = message.from_user

        # --- LOG CHANNEL ---
        log_msg = await client.send_cached_media(
            chat_id=LOG_CHANNEL,
            file_id=fileid,
            caption=f"**User:** {user.mention} (`{user.id}`)\n**File:** `{filename}`"
        )

        # Generate Link details
        file_name_encoded = quote_plus(filename)
        file_hash = get_hash(log_msg)
        
        stream_link = f"{URL}watch/{log_msg.id}/{file_name_encoded}?hash={file_hash}"
        download_link = f"{URL}{log_msg.id}/{file_name_encoded}?hash={file_hash}"

        # --- SAVE TO MONGODB ---
        file_data = {
            "user_id": user.id,
            "log_id": log_msg.id,
            "file_name": filename,
            "file_size": filesize,
            "file_id": fileid,
            "media_type": media_type,
            "stream_link": stream_link,
            "download_link": download_link,
            "caption": target_msg.caption or ""
        }
        await db.add_file(file_data)

        # --- 3️⃣ SEND LINK TO USER ---
        user_buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🖥 Sᴛʀᴇᴀᴍ", url=stream_link),
                InlineKeyboardButton("📥 Dᴏᴡɴʟᴏᴀᴅ", url=download_link)
            ],
            [
                InlineKeyboardButton("🗑️ Rᴇᴠᴏᴋᴇ Lɪɴᴋ", callback_data=f"ask_revoke_{log_msg.id}")
            ]
        ])

        msg_text = (
            "<b><i><u>⚡ 𝗟𝗶𝗻𝗸 𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗲𝗱 & 𝗦𝗮𝘃𝗲𝗱!</u></i></b>\n\n"
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


# --- 4️⃣ CALLBACK HANDLERS FOR REVOKE ---

@Client.on_callback_query(filters.regex(r"^ask_revoke_"))
async def ask_revoke_handler(client: Client, query: CallbackQuery):
    log_id = query.data.split("_")[-1]
    
    confirm_buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes, Delete", callback_data=f"do_revoke_{log_id}"),
            InlineKeyboardButton("❌ No, Cancel", callback_data="cancel_revoke")
        ]
    ])
    
    await query.message.edit_reply_markup(reply_markup=confirm_buttons)


@Client.on_callback_query(filters.regex(r"^cancel_revoke"))
async def cancel_revoke_handler(client: Client, query: CallbackQuery):
    msg_text = query.message.text
    try:
        urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', msg_text)
        dl_link = next((u for u in urls if "watch" not in u), None)
        st_link = next((u for u in urls if "watch" in u), None)

        if dl_link and st_link:
            # Attempt to extract log_id from the link to restore the exact state
            # Link format assumption: URL/log_id/filename...
            try:
                parts = dl_link.replace(URL, "").split("/")
                # usually parts[0] is log_id if URL ends with /
                log_id_restored = parts[0] 
                
                original_buttons = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("🖥 Sᴛʀᴇᴀᴍ", url=st_link),
                        InlineKeyboardButton("📥 Dᴏᴡɴʟᴏᴀᴅ", url=dl_link)
                    ],
                    [
                        InlineKeyboardButton("🗑️ Rᴇᴠᴏᴋᴇ Lɪɴᴋ", callback_data=f"ask_revoke_{log_id_restored}")
                    ]
                ])
            except:
                # Fallback if parsing fails
                original_buttons = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("🖥 Sᴛʀᴇᴀᴍ", url=st_link),
                        InlineKeyboardButton("📥 Dᴏᴡɴʟᴏᴀᴅ", url=dl_link)
                    ]
                ])

            await query.message.edit_reply_markup(reply_markup=original_buttons)
        else:
            await query.answer("Could not restore buttons.", show_alert=True)
            
    except Exception as e:
        await query.answer("Cancelled", show_alert=True)
        await query.message.edit_reply_markup(None)


@Client.on_callback_query(filters.regex(r"^do_revoke_"))
async def do_revoke_handler(client: Client, query: CallbackQuery):
    log_id = int(query.data.split("_")[-1])
    
    try:
        # 1. Delete from Telegram Log Channel
        await client.delete_messages(chat_id=LOG_CHANNEL, message_ids=log_id)
        
        # 2. Delete from MongoDB
        await db.delete_file(log_id)
        
        # 3. Update User UI
        await query.message.edit_text(
            "<b>🚫 <i>Link Revoked Successfully.</i></b>\n\n"
            "__The file has been deleted from the database and server.__"
        )
    except Exception as e:
        await query.answer(f"Error: {e}", show_alert=True)
