import aiohttp
import os
from pyrogram import Client, filters
from pyrogram.types import Message

CATBOX_API = "https://catbox.moe/user/api.php"
MAX_SIZE = 200 * 1024 * 1024  # 200 MB

# --- Progress bar helper ---
async def progress_bar(current, total, message: Message, stage="⬆️ Uploading"):
    percent = (current / total) * 100
    filled = int(percent / 10)
    bar = "█" * filled + "░" * (10 - filled)
    try:
        await message.edit_text(f"{stage}\n\n[{bar}] {percent:.1f}%")
    except:
        pass

# --- Upload to Catbox with progress ---
async def upload_to_catbox(file_path: str, status: Message):
    file_size = os.path.getsize(file_path)

    async with aiohttp.ClientSession() as session:
        with open(file_path, "rb") as f:
            data = aiohttp.FormData()
            data.add_field("reqtype", "fileupload")

            # Stream file with progress
            class StreamReader:
                def __init__(self, file, total):
                    self.file = file
                    self.total = total
                    self.sent = 0

                async def read(self, n=-1):
                    chunk = self.file.read(n)
                    if chunk:
                        self.sent += len(chunk)
                        await progress_bar(self.sent, self.total, status, "⬆️ Uploading...")
                    return chunk

            stream = StreamReader(f, file_size)
            data.add_field("fileToUpload", stream, filename=os.path.basename(file_path))

            async with session.post(CATBOX_API, data=data) as resp:
                return await resp.text()

# --- Main handler ---
@Client.on_message(filters.command("catbox") & filters.reply)
async def catbox_upload_handler(_, message: Message):
    reply = message.reply_to_message

    # Collect all media in reply (including albums)
    medias = []
    if reply.document:
        medias.append(reply.document)
    if reply.photo:
        medias.append(reply.photo)
    if reply.video:
        medias.append(reply.video)
    if reply.audio:
        medias.append(reply.audio)
    if reply.media_group_id:  # media group / album
        async for m in message.chat.get_media_group(reply.id):
            if m.document: medias.append(m.document)
            if m.photo: medias.append(m.photo)
            if m.video: medias.append(m.video)
            if m.audio: medias.append(m.audio)

    if not medias:
        return await message.reply_text("⚠️ Reply to a file (or album) to upload to Catbox.")

    status = await message.reply_text("📤 Preparing upload...")

    links = []
    for media in medias:
        # --- Download with progress ---
        file_path = await reply.download(
            progress=lambda c, t: progress_bar(c, t, status, "⬇️ Downloading...")
        )

        # --- Check size before upload ---
        if os.path.getsize(file_path) > MAX_SIZE:
            links.append(f"❌ Skipped `{os.path.basename(file_path)}` (exceeds 200MB limit).")
            os.remove(file_path)
            continue

        try:
            link = await upload_to_catbox(file_path, status)
            links.append(link)
        except Exception as e:
            links.append(f"❌ Error: {e}")
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

    result = "\n".join([f"{i+1}. {link}" for i, link in enumerate(links)])
    await status.edit_text(f"✅ Upload complete!\n\n{result}")
