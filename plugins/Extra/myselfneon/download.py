import os
import aiohttp
import asyncio
import math
import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import subprocess
import cv2  # For video metadata

# ---------- CONFIG ----------
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

ACTIVE_DOWNLOADS = {}
PROGRESS_BAR_LENGTH = 16
MAX_PARALLEL_CHUNKS = 3
MAX_ACTIVE_DOWNLOADS = 10

VIDEO_EXTENSIONS = {
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/ogg": ".ogv",
    "application/vnd.apple.mpegurl": ".m3u8",
    "vnd.apple.mpegurl": ".m3u8"
}

# ---------- Helpers ----------
def human_readable(size):
    power = 2**10
    n = 0
    Dic_powerN = {0: "B",1:"KB",2:"MB",3:"GB",4:"TB"}
    while size > power:
        size /= power
        n +=1
    return f"{round(size,2)} {Dic_powerN[n]}"

def progress_bar(done, total, length=16):
    filled = int(length * done / total) if total else 0
    return "▰" * filled + "▱" * (length - filled)

async def update_progress(current, total, message: Message, start, action="Downloading"):
    now = time.time()
    elapsed = now - start
    speed = current / (elapsed+1e-6)
    eta = (total-current)/(speed+1e-6)
    bar = progress_bar(current, total, length=PROGRESS_BAR_LENGTH)
    text = (
        f"📤 **{action}...**\n\n"
        f"{bar}\n"
        f"**{human_readable(current)}** / **{human_readable(total)}**\n"
        f"⚡ {human_readable(speed)}/s | ⏳ {int(eta)}s"
    )
    try:
        await message.edit(text)
    except: pass

# ---------- Fast download ----------
async def download_range(session, url, start, end, temp_file, idx, progress, chat_id):
    headers = {"Range": f"bytes={start}-{end}"}
    async with session.get(url, headers=headers) as resp:
        async for chunk in resp.content.iter_chunked(1024*512):
            if not ACTIVE_DOWNLOADS.get(chat_id, True):
                return
            temp_file[idx].write(chunk)
            progress[idx] += len(chunk)

async def download_file(url: str, temp_path: str, status_msg: Message, chat_id: int):
    if ACTIVE_DOWNLOADS.get(chat_id,0) >= MAX_ACTIVE_DOWNLOADS:
        await status_msg.edit("⚠ You reached the maximum 10 simultaneous downloads.")
        return None
    ACTIVE_DOWNLOADS[chat_id] = ACTIVE_DOWNLOADS.get(chat_id,0)+1

    async with aiohttp.ClientSession() as session:
        async with session.head(url) as resp_head:
            if resp_head.status != 200:
                ACTIVE_DOWNLOADS[chat_id]-=1
                return None
            total_size = int(resp_head.headers.get("Content-Length", 0))
            content_type = resp_head.headers.get("Content-Type","").lower()
            if not ACTIVE_DOWNLOADS.get(chat_id, True):
                ACTIVE_DOWNLOADS[chat_id]-=1
                return None

            if "mpegurl" in content_type:  # M3U8 playlist
                ACTIVE_DOWNLOADS[chat_id]-=1
                return await download_m3u8(url,temp_path,status_msg,chat_id)

            ext = VIDEO_EXTENSIONS.get(content_type,".mp4")
            file_path = temp_path+ext

            chunk_size = math.ceil(total_size / MAX_PARALLEL_CHUNKS)
            temp_files = [open(f"{file_path}.part{i}","wb") for i in range(MAX_PARALLEL_CHUNKS)]
            progress = [0]*MAX_PARALLEL_CHUNKS
            start_time = time.time()

            tasks = []
            for i in range(MAX_PARALLEL_CHUNKS):
                start = i*chunk_size
                end = min((i+1)*chunk_size-1, total_size-1)
                tasks.append(download_range(session,url,start,end,temp_files,i,progress,chat_id))

            async def monitor():
                while not all(t.done() for t in asyncio.all_tasks() if t in tasks):
                    if not ACTIVE_DOWNLOADS.get(chat_id, True):
                        break
                    await update_progress(sum(progress), total_size, status_msg, start_time,"Downloading")
                    await asyncio.sleep(0.5)

            await asyncio.gather(asyncio.gather(*tasks), monitor())

            for f in temp_files:
                f.close()

            merged_size = 0
            with open(file_path,"wb") as f:
                for i in range(MAX_PARALLEL_CHUNKS):
                    part_path = f"{file_path}.part{i}"
                    with open(part_path,"rb") as pf:
                        while True:
                            chunk = pf.read(1024*1024)
                            if not chunk: break
                            f.write(chunk)
                            merged_size += len(chunk)
                            await update_progress(merged_size, total_size, status_msg, start_time,"Merging")
                    os.remove(part_path)

            ACTIVE_DOWNLOADS[chat_id]-=1
            return file_path, total_size

# ---------- M3U8 download ----------
async def download_m3u8(url: str, path: str, status_msg: Message, chat_id: int):
    if not ACTIVE_DOWNLOADS.get(chat_id, True):
        return None

    temp_path = path + ".mp4"

    headers = "User-Agent: Mozilla/5.0\r\nReferer: https://google.com\r\n"
    cmd = [
        "ffmpeg","-y",
        "-headers", headers,
        "-i", url,
        "-c","copy",
        "-threads","4",
        "-bsf:a","aac_adtstoasc",
        temp_path
    ]

    try:
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        await status_msg.edit("❌ **FFmpeg not found.** Please install ffmpeg.")
        ACTIVE_DOWNLOADS[chat_id] = 0
        return None

    last_size = 0
    start_time = time.time()

    while True:
        if proc.returncode is not None:
            break
        if os.path.exists(temp_path):
            current_size = os.path.getsize(temp_path)
            if current_size != last_size:
                last_size = current_size
                await update_progress(current_size, current_size+1024*1024, status_msg, start_time,"Downloading")
        await asyncio.sleep(1)

    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        error_text = stderr.decode(errors="ignore")[:500]
        await status_msg.edit(f"❌ **M3U8 download failed**\n\nError:\n```{error_text}```")
        ACTIVE_DOWNLOADS[chat_id] = 0
        return None

    size = os.path.getsize(temp_path) if os.path.exists(temp_path) else 0
    return temp_path, size if size > 0 else None

# ---------- Cancel ----------
@Client.on_callback_query(filters.regex("dlcancel"))
async def cancel_callback(client: Client, query):
    ACTIVE_DOWNLOADS[query.message.chat.id] = False
    await query.message.edit("❌ Download/upload cancelled.")
    await query.answer("Cancelled!")

# ---------- /dl COMMAND ---------
@Client.on_message(filters.command(["dl"]) & filters.private)
async def dl_handler(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "⚠ You need to provide a link to download!\n\n"
            "Usage:\n`/dl <direct link or m3u8>`\n\n"
            "Example:\n`/dl https://example.com/video.mp4`"
        )

    links = message.command[1:]
    ACTIVE_DOWNLOADS[message.chat.id] = ACTIVE_DOWNLOADS.get(message.chat.id, 0)

    for idx, url in enumerate(links, 1):
        temp_path = os.path.join(DOWNLOAD_DIR, f"{message.chat.id}_{int(time.time())}_{idx}")
        status = await message.reply_text(
            f"📥 Downloading {idx}/{len(links)}...",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("❌ Cancel", callback_data="dlcancel")]]
            )
        )

        result = await download_file(url, temp_path, status, message.chat.id)
        if not result:
            await status.edit(f"❌ Failed to download link {idx}")
            continue

        file_path, file_size = result
        caption_text = f"🎬 **{os.path.basename(file_path)}**\n📦 Size: {human_readable(file_size)}"

        # --- Detect video metadata ---
        width = None
        height = None
        try:
            cap = cv2.VideoCapture(file_path)
            if cap.isOpened():
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
        except:
            pass

        # Fallback to 3:2 ratio
        if not width or not height:
            width = 1200
            height = 800

        try:
            await message.reply_video(
                file_path,
                caption=caption_text,
                supports_streaming=True,
                width=width,
                height=height
            )
        except:
            await message.reply_document(file_path, caption=caption_text)

        await asyncio.sleep(5)
        try: await status.delete()
        except: pass

        os.remove(file_path)

    ACTIVE_DOWNLOADS[message.chat.id] = 0

# ---------- /dlhelp COMMAND ----------
@Client.on_message(filters.command(["dlhelp"]) & filters.private)
async def dlhelp_handler(client: Client, message: Message):
    help_text = (
        "📌 **DL Bot Commands:**\n\n"
        "1️⃣ `/dl <link>` - Download a direct video/file link or m3u8 playlist.\n"
        "   - Supports multiple links: `/dl link1 link2 ...`\n"
        "   - Max 3 parallel connections per file.\n"
        "   - Max 10 active downloads per user.\n\n"
        "2️⃣ `❌ Cancel Button` - Tap the button during download to cancel.\n\n"
        "⚡ Progress bar shows speed, ETA, and size. Disappears 5s after upload."
    )
    await message.reply_text(help_text)
    
