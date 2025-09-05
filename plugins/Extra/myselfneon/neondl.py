#Neondl.py
import os
import aiohttp
import asyncio
import time
import subprocess
from pyrogram import Client, filters
from pyrogram.types import Message

# Temp folder
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# -------- Helpers --------
def human_readable(size):
    power = 2**10
    n = 0
    Dic_powerN = {0: "B", 1: "KB", 2: "MB", 3: "GB", 4: "TB"}
    while size > power:
        size /= power
        n += 1
    return f"{round(size, 2)} {Dic_powerN[n]}"


def progress_bar(done, total):
    filled = int(20 * done / total) if total else 0
    return "▰" * filled + "▱" * (20 - filled)


async def progress_for_pyrogram(current, total, message: Message, start, action="Uploading"):
    now = time.time()
    elapsed = now - start
    speed = current / (elapsed + 1e-6)
    eta = (total - current) / (speed + 1e-6)

    bar = progress_bar(current, total)
    text = (
        f"📤 **{action}...**\n\n"
        f"{bar}\n"
        f"**{human_readable(current)}** / **{human_readable(total)}**\n"
        f"⚡ {human_readable(speed)}/s | ⏳ {int(eta)}s"
    )
    try:
        await message.edit(text)
    except:
        pass


# Map content types to extensions
VIDEO_EXTENSIONS = {
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/ogg": ".ogv",
    "application/vnd.apple.mpegurl": ".m3u8",
    "vnd.apple.mpegurl": ".m3u8"
}


# -------- Downloaders --------
async def download_file(url: str, temp_path: str, status_msg: Message):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            content_type = resp.headers.get("Content-Type", "").lower()

            # Detect m3u8 automatically
            if any(x in content_type for x in ["application/vnd.apple.mpegurl", "vnd.apple.mpegurl"]):
                return await download_m3u8(url, temp_path, status_msg)

            # Determine extension from content type
            ext = VIDEO_EXTENSIONS.get(content_type, ".mp4")
            file_path = temp_path + ext

            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            start_time = time.time()

            with open(file_path, "wb") as f:
                async for chunk in resp.content.iter_chunked(1024 * 512):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        bar = progress_bar(downloaded, total)
                        speed = downloaded / (time.time() - start_time + 1e-6)
                        eta = (total - downloaded) / (speed + 1e-6)
                        msg = (
                            f"📥 **Downloading...**\n\n"
                            f"{bar}\n"
                            f"**{human_readable(downloaded)}** / **{human_readable(total)}**\n"
                            f"⚡ {human_readable(speed)}/s | ⏳ {int(eta)}s"
                        )
                        try:
                            await status_msg.edit(msg)
                        except:
                            pass
            return file_path


async def download_m3u8(url: str, path: str, status_msg: Message):
    # Use ffmpeg to save as mp4
    cmd = ["ffmpeg", "-y", "-i", url, "-c", "copy", "-bsf:a", "aac_adtstoasc", path + ".mp4"]
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    await proc.communicate()
    return path + ".mp4" if os.path.exists(path + ".mp4") else None


# -------- Telegram Command --------
@Client.on_message(filters.command(["neodl"]) & filters.private)
async def neodl_handler(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "⚡ Usage:\n`/neodl <direct-link or m3u8>`"
        )

    url = message.command[1]
    temp_path = os.path.join(DOWNLOAD_DIR, f"{message.chat.id}_{int(time.time())}")

    status = await message.reply_text("📥 Starting download...")

    # Auto-detect type and download
    file_path = None
    if url.endswith(".m3u8"):
        file_path = await download_m3u8(url, temp_path, status)
    else:
        file_path = await download_file(url, temp_path, status)

    if not file_path or not os.path.exists(file_path):
        return await status.edit("❌ Failed to download video.")

    await status.edit("✅ Starting upload...")

    start_time = time.time()
    try:
        await message.reply_video(
            file_path,
            caption="🎬 Here’s your video",
            progress=progress_for_pyrogram,
            progress_args=(status, start_time, "Uploading")
        )
    except:
        await message.reply_document(
            file_path,
            caption="📂 Video sent as file",
            progress=progress_for_pyrogram,
            progress_args=(status, start_time, "Uploading")
        )

    os.remove(file_path)
    await status.delete()
  
