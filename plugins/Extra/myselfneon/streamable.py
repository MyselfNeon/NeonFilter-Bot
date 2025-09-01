import os
import aiohttp
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

# -------------------
# Streamable credentials (self-contained)
# -------------------
STREAMABLE_USER = "neon02@hi2.in"
STREAMABLE_PASS = "Casper2222"

# -------------------
# Constants
# -------------------
MAX_SIZE = 200 * 1024 * 1024  # 200 MB
STREAMABLE_API = "https://api.streamable.com/upload"
active_uploads = {}  # Track active uploads per user

# -------------------
# /streamable command
# -------------------
@Client.on_message(filters.command("streamable") & filters.private)
async def streamable_start(bot: Client, message: Message):
    user_id = message.from_user.id
    if not STREAMABLE_USER or not STREAMABLE_PASS:
        return await message.reply_text("**❌ Streamable credentials not set. Update plugin with your username/password.**")

    if user_id in active_uploads:
        return await message.reply_text("**⚠️ You already have an active upload. Use /scancel to abort.**")

    active_uploads[user_id] = {"message": message}
    await message.reply_text(
        "**📤 Send your video to upload to Streamable (Max 200 MB)**\n\n"
        "**⏰ 30 sec timeout, /scancel to cancel.**"
    )

    await asyncio.sleep(30)
    if user_id in active_uploads and "file_sent" not in active_uploads[user_id]:
        active_uploads.pop(user_id)
        timeout_msg = await message.reply_text(
            "**⏰ Time's Up! You did not send a file. Start again with /streamable**"
        )
        await asyncio.sleep(20)
        try:
            await timeout_msg.delete()
        except:
            pass

# -------------------
# File handler for /streamable
# -------------------
@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def streamable_file_handler(bot: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in active_uploads:
        return

    active_uploads[user_id]["file_sent"] = True
    status_msg = await message.reply_text("**⬇️ Downloading your file...**")
    file_path = await message.download()

    # File size check
    if os.path.getsize(file_path) > MAX_SIZE:
        await status_msg.edit_text(f"**❌ File too large (>{MAX_SIZE/1024/1024} MB). Upload canceled.**")
        os.remove(file_path)
        active_uploads.pop(user_id)
        return

    await status_msg.edit_text("**⬆️ Uploading to Streamable...**")

    try:
        auth = aiohttp.BasicAuth(STREAMABLE_USER, STREAMABLE_PASS)
        async with aiohttp.ClientSession(auth=auth, timeout=aiohttp.ClientTimeout(total=60)) as session:
            with open(file_path, "rb") as f:
                data = aiohttp.FormData()
                data.add_field("file", f, filename=os.path.basename(file_path))
                async with session.post(STREAMABLE_API, data=data) as resp:
                    json_resp = await resp.json()
                    if resp.status == 200 and json_resp.get("shortcode"):
                        link = f"https://streamable.com/{json_resp['shortcode']}"
                    else:
                        link = None

        if not link:
            await status_msg.edit_text("**❌ Upload failed. Try again.**")
            return

        # Send link to user
        await status_msg.edit_text(
            f"**✅ Upload Completed!**\n\nYour Link:\n{link}",
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("Oᴘᴇɴ 👀", url=link),
                        InlineKeyboardButton("Cʟᴏsᴇ ❌", callback_data="close_streamable")
                    ]
                ]
            )
        )

    except Exception as e:
        await status_msg.edit_text(f"**❌ Upload Failed:\n{e}**")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        active_uploads.pop(user_id, None)

# -------------------
# Close button handler
# -------------------
@Client.on_callback_query(filters.regex(r"^close_streamable$"))
async def close_streamable_callback(bot: Client, query: CallbackQuery):
    try:
        await query.message.delete()
        await query.answer("Message closed ❌")
    except Exception as e:
        await query.answer(f"Failed to close: {e}", show_alert=True)

# -------------------
# /scancel command
# -------------------
@Client.on_message(filters.command("scancel") & filters.private)
async def streamable_cancel(bot: Client, message: Message):
    user_id = message.from_user.id
    if user_id in active_uploads:
        active_uploads.pop(user_id)
        await message.reply_text("**❌ Upload canceled successfully.**")
    else:
        await message.reply_text("**🤷 You have no active uploads. Use /streamable to start one.**")
      
