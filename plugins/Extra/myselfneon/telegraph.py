import os
import requests
import aiohttp
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from info import LOG_CHANNEL, STREAMABLE_USER, STREAMABLE_PASS  # import Streamable creds

# -------------------
# Constants
# -------------------
MAX_SIZE = 200 * 1024 * 1024  # Local max file size 200 MB
CATBOX_API = "https://catbox.moe/user/api.php"
ENVS_UPLOAD_URL = "https://envs.sh"
STREAMABLE_API = "https://api.streamable.com/upload"

# Track active uploads per user
active_uploads = {}

# -------------------
# Helper functions
# -------------------
def upload_to_envs(file_path: str):
    try:
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(ENVS_UPLOAD_URL, files=files, timeout=60)
            if response.status_code == 200:
                return response.text.strip()
            return None
    except Exception as e:
        print(f"**__Error Uploading to Envs :\n{e}__**")
        return None

async def upload_to_catbox(file_path: str):
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
            with open(file_path, "rb") as f:
                data = aiohttp.FormData()
                data.add_field("reqtype", "fileupload")
                data.add_field("fileToUpload", f, filename=os.path.basename(file_path))
                async with session.post(CATBOX_API, data=data) as resp:
                    return await resp.text()
    except Exception as e:
        print(f"**__Error Uploading to Catbox :\n{e}__**")
        return None

async def upload_to_streamable(file_path: str):
    if not STREAMABLE_USER or not STREAMABLE_PASS:
        return None
    try:
        auth = aiohttp.BasicAuth(STREAMABLE_USER, STREAMABLE_PASS)
        async with aiohttp.ClientSession(auth=auth, timeout=aiohttp.ClientTimeout(total=60)) as session:
            with open(file_path, "rb") as f:
                data = aiohttp.FormData()
                data.add_field("file", f, filename=os.path.basename(file_path))
                async with session.post(STREAMABLE_API, data=data) as resp:
                    json_resp = await resp.json()
                    if resp.status == 200 and json_resp.get("shortcode"):
                        return f"https://streamable.com/{json_resp['shortcode']}"
                    return None
    except Exception as e:
        print(f"**__Error Uploading to Streamable :\n{e}__**")
        return None

# -------------------
# /telegraph command
# -------------------
@Client.on_message(filters.command("telegraph") & filters.private)
async def telegraph_start(bot: Client, message: Message):
    user_id = message.from_user.id

    if user_id in active_uploads:
        return await message.reply_text(
            "**__You Already have an Active Upload.\nFinish or Cancel it with /tcancel__**"
        )

    buttons = [
        [InlineKeyboardButton("Eɴᴠs.sʜ 🌐", callback_data="telegraph_envs"),
         InlineKeyboardButton("Cᴀᴛʙᴏx 📦", callback_data="telegraph_catbox")]
    ]

    # Add Streamable if credentials exist
    if STREAMABLE_USER and STREAMABLE_PASS:
        buttons[0].append(InlineKeyboardButton("Sᴛʀᴇᴀᴍᴀʙʟᴇ 🎬", callback_data="telegraph_streamable"))

    keyboard = InlineKeyboardMarkup(buttons)

    await message.reply_text(
        "**__Choose The Site To Upload Your File__**",
        reply_markup=keyboard
    )

# -------------------
# Callback handler for /telegraph buttons
# -------------------
@Client.on_callback_query(filters.regex(r"^telegraph_"))
async def telegraph_callback(bot: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if user_id in active_uploads:
        return await query.answer("Finish or Cancel your Current Upload First.", show_alert=True)

    site = query.data.split("_")[1]  # envs, catbox, or streamable
    active_uploads[user_id] = {"site": site, "message": query.message}

    await query.answer()
    await query.message.edit_text("**__Now Send me your File (Photo, Video, Document, Audio)\n\n/tcancel to Abort the Process__**")

    # 30-second timeout for user inactivity
    await asyncio.sleep(30)
    if user_id in active_uploads and "file_sent" not in active_uploads[user_id]:
        active_uploads.pop(user_id, None)
        timeout_msg = await query.message.edit_text(
            "**⏰ __Time's Up !!\nYou did not Send any File in 30 sec.__**\n"
            "**__Start a New Upload /telegraph__**"
        )
        await asyncio.sleep(20)
        try:
            await timeout_msg.delete()
        except:
            pass

# -------------------
# File handler scoped to active /telegraph users
# -------------------
@Client.on_message(filters.private & (filters.document | filters.photo | filters.video | filters.audio))
async def telegraph_file_handler(bot: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in active_uploads:
        return

    active_uploads[user_id]["file_sent"] = True
    site = active_uploads[user_id]["site"]

    status_msg = await message.reply_text("**__Downloading Your File...__ ⬇️**")
    file_path = await message.download()

    # File size check for catbox and streamable
    if site in ["catbox", "streamable"] and os.path.getsize(file_path) > MAX_SIZE:
        await status_msg.edit_text(
            f"**❌ __File Too Large (>{MAX_SIZE/1024/1024} MB).\n\nUpload Canceled__ ❌**"
        )
        os.remove(file_path)
        active_uploads.pop(user_id)
        return

    await status_msg.edit_text("**__Uploading Now...__ ⬆️**")

    try:
        # Choose correct upload function
        if site == "envs":
            link = upload_to_envs(file_path)
        elif site == "catbox":
            link = await upload_to_catbox(file_path)
        elif site == "streamable":
            link = await upload_to_streamable(file_path)
        else:
            link = None

        if not link:
            await status_msg.edit_text("**❌ __Upload Failed. Try Again.__ 🥲**")
            return

        # Log Upload to LOG_CHANNEL
        try:
            caption_text = (
                f"**🛜 __New Upload Detected__**\n\n"
                f"**👤 __User : {message.from_user.mention} (`{user_id}`)__**\n"
                f"**🆔 __Username : @{message.from_user.username if message.from_user.username else 'N/A'}__**\n"
                f"**┎ __Generated Link__ 🖇️ \n┖  __{link}__**"
            )

            if message.photo:
                await bot.send_photo(LOG_CHANNEL, file_path, caption=caption_text)
            elif message.video:
                await bot.send_video(LOG_CHANNEL, file_path, caption=caption_text)
            elif message.audio:
                await bot.send_audio(LOG_CHANNEL, file_path, caption=caption_text)
            else:
                await bot.send_document(LOG_CHANNEL, file_path, caption=caption_text)
        except Exception as e:
            print(f"**__Failed to Log Upload: {e}__**")

        # Send final link to user
        await status_msg.edit_text(
            text=f"**✅ __Upload Completed !!\n\nYour Link 🖇️\n{link}__**",
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("Oᴘᴇɴ 👀", url=link),
                        InlineKeyboardButton("Cʟᴏsᴇ ❌", callback_data="close")
                    ]
                ]
            )
        )

    except Exception as e:
        await status_msg.edit_text(f"**❌ __Upload Failed :\n`{e}`__**")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        active_uploads.pop(user_id, None)

# -------------------
# Close button handler
# -------------------
@Client.on_callback_query(filters.regex(r"^close$"))
async def close_callback(bot: Client, query: CallbackQuery):
    try:
        await query.message.delete()
        await query.answer("Message closed ❌", show_alert=False)
    except Exception as e:
        await query.answer(f"Failed to close: {e}", show_alert=True)

# -------------------
# /cancel command
# -------------------
@Client.on_message(filters.command("tcancel") & filters.private)
async def telegraph_cancel(bot: Client, message: Message):
    user_id = message.from_user.id
    if user_id in active_uploads:
        active_uploads.pop(user_id)
        await message.reply_text("**❌ __Upload Canceled Successfully__ 🤧**")
    else:
        await message.reply_text("**🤷 __There Are No Active Uploads to Cancel. Use /telegraph to Create an Upload__**")



# Dont remove Credits
# Developer Telegram @MyselfNeon
# Update channel - @NeonFiles
