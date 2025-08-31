import os
import requests
import aiohttp
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

CATBOX_API = "https://catbox.moe/user/api.php"
MAX_SIZE = 200 * 1024 * 1024  # 200 MB
ENVS_UPLOAD_URL = "https://envs.sh"  # Replace with your envs.sh upload URL

# Track active uploads per user
active_uploads = set()

# -------------------
# Helper functions
# -------------------

def upload_to_envs(file_path: str):
    try:
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(ENVS_UPLOAD_URL, files=files)
            if response.status_code == 200:
                return response.text.strip()
            return None
    except Exception as e:
        print(f"Error uploading to envs: {e}")
        return None

async def upload_to_catbox(file_path: str):
    async with aiohttp.ClientSession() as session:
        with open(file_path, "rb") as f:
            data = aiohttp.FormData()
            data.add_field("reqtype", "fileupload")
            data.add_field("fileToUpload", f, filename=os.path.basename(file_path))
            async with session.post(CATBOX_API, data=data) as resp:
                return await resp.text()

# -------------------
# /telegraph command
# -------------------

@Client.on_message(filters.command("telegraph") & filters.private)
async def telegraph_start(bot: Client, message: Message):
    user_id = message.from_user.id

    if user_id in active_uploads:
        return await message.reply_text("⚠️ You already have an active upload. Please finish it first.")

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("envs.sh 🌐", callback_data="upload_envs")],
            [InlineKeyboardButton("Catbox 📦", callback_data="upload_catbox")],
        ]
    )
    await message.reply_text(
        "**Choose the site to upload your file:**",
        reply_markup=keyboard
    )

# -------------------
# Callback handler for site selection
# -------------------

@Client.on_callback_query()
async def telegraph_callback(bot: Client, query: CallbackQuery):
    user_id = query.from_user.id

    if query.data == "close":
        await query.message.delete()
        return await query.answer()

    if user_id in active_uploads:
        return await query.answer("⚠️ Finish your current upload first.", show_alert=True)

    active_uploads.add(user_id)
    site = query.data
    await query.answer()

    await query.message.edit_text("📤 Now send me your file (photo, video, document, audio):")

    try:
        file_msg: Message = await bot.listen(
            filters.chat(user_id) &
            (filters.document | filters.photo | filters.video | filters.audio),
            timeout=300
        )
    except TimeoutError:
        active_uploads.remove(user_id)
        return await query.message.edit_text("⌛ You took too long. Please try /telegraph again.")

    status_msg = await query.message.reply_text("⬇️ Downloading your file...")
    file_path = await file_msg.download()

    # Check Catbox file size
    if site == "upload_catbox" and os.path.getsize(file_path) > MAX_SIZE:
        await status_msg.edit_text(f"❌ File too large (>{MAX_SIZE/1024/1024} MB). Upload canceled.")
        os.remove(file_path)
        active_uploads.remove(user_id)
        return

    await status_msg.edit_text("⬆️ Uploading now...")

    try:
        if site == "upload_envs":
            link = upload_to_envs(file_path)
        else:
            link = await upload_to_catbox(file_path)

        if not link:
            await status_msg.edit_text("❌ Upload failed.")
            return

        await status_msg.edit_text(
            text=f"✅ Upload complete!\n\n🔗 {link}",
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("Open Link 🔓", url=link),
                        InlineKeyboardButton("Share Link 🖇️", url=f"https://telegram.me/share/url?url={link}")
                    ],
                    [InlineKeyboardButton("❌ Close ❌", callback_data="close")]
                ]
            )
        )
    except Exception as e:
        await status_msg.edit_text(f"❌ Upload failed:\n`{e}`")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        active_uploads.discard(user_id)
        
