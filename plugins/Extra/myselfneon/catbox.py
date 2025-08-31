import aiohttp
import os
from pyrogram import Client, filters
from pyrogram.types import Message

CATBOX_API = "https://catbox.moe/user/api.php"
MAX_SIZE = 200 * 1024 * 1024  # 200 MB

# --- Upload helper ---
async def upload_to_catbox(file_path: str):
    async with aiohttp.ClientSession() as session:
        with open(file_path, "rb") as f:
            data = aiohttp.FormData()
            data.add_field("reqtype", "fileupload")
            data.add_field("fileToUpload", f, filename=os.path.basename(file_path))
            async with session.post(CATBOX_API, data=data) as resp:
                return await resp.text()

# --- Main command ---
@Client.on_message(filters.command("catbox"))
async def catbox_interactive(_, message: Message):
    # Ask user for file
    await message.reply_text("📤 Please send the file you want to upload to Catbox (photo, document, video, audio):")

    # Wait for next message from same user in the same chat
    try:
        file_message: Message = await _.listen(
            filters.chat(message.chat.id) &
            (filters.document | filters.photo | filters.video | filters.audio),
            timeout=300  # 5 minutes timeout
        )
    except TimeoutError:
        return await message.reply_text("⌛ You took too long. Please try /catbox again.")

    # Download the file
    status = await message.reply_text("⬇️ Downloading your file...")
    file_path = await file_message.download(progress=lambda c, t: None)

    # Check file size
    if os.path.getsize(file_path) > MAX_SIZE:
        await status.edit_text(f"❌ File too large (>{MAX_SIZE/1024/1024} MB). Upload canceled.")
        os.remove(file_path)
        return

    # Upload to Catbox
    await status.edit_text("⬆️ Uploading to Catbox...")
    try:
        link = await upload_to_catbox(file_path)
        await status.edit_text(f"✅ Upload complete!\n\n🔗 {link}")
    except Exception as e:
        await status.edit_text(f"❌ Upload failed:\n`{e}`")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
