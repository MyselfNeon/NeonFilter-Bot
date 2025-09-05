import os
import aiohttp
import asyncio
import time
import random
import subprocess
from PIL import Image
from pyrofork import Client, filters
from pyrofork.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from typing import Dict

# ---------- CONFIG ----------
GENERATE_THUMBNAILS = True  # True to generate collage, False to skip
NUM_SCREENSHOTS = 6         # Number of random screenshots in collage
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Active downloads dict to allow cancellation
ACTIVE_DOWNLOADS: Dict[int, bool] = {}

# ---------- Helpers ----------
def human_readable(size):
    power = 2**10
    n = 0
    Dic_powerN = {0: "B", 1: "KB", 2: "MB", 3: "GB", 4: "TB"}
    while size > power:
        size /= power
        n += 1
    return f"{round(size, 2)} {Dic_powerN[n]}"

def progress_bar(done, total, length=16):
    filled = int(length * done / total) if total else 0
    return "▰" * filled + "▱" * (length - filled)

async def progress_for_pyrofork(current, total, message: Message, start, action="Uploading"):
    now = time.time()
    elapsed = now - start
    speed = current / (elapsed + 1e-6)
    eta = (total - current) / (speed + 1e-6)
    bar = progress_bar(current, total, length=16)
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

VIDEO_EXTENSIONS = {
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/ogg": ".ogv",
    "application/vnd.apple.mpegurl": ".m3u8",
    "vnd.apple.mpegurl": ".m3u8"
}

# ---------- Downloaders ----------
async def download_chunk(session, url, start, end, fpath, index, chat_id):
    headers = {"Range": f"bytes={start}-{end}"}
    async with session.get(url, headers=headers) as resp:
        chunk_path = f"{fpath}.part{index}"
        with open(chunk_path, "wb") as f:
            async for data in resp.content.iter_chunked(1024*512):
                if not ACTIVE_DOWNLOADS.get(chat_id, True):
                    return None
                f.write(data)
    return chunk_path

async def download_file(url: str, temp_path: str, status_msg: Message, chat_id: int, max_workers=8):
    async with aiohttp.ClientSession() as session:
        async with session.head(url) as resp_head:
            if resp_head.status != 200:
                return None
            total_size = int(resp_head.headers.get("Content-Length", 0))
            content_type = resp_head.headers.get("Content-Type", "").lower()

            if not ACTIVE_DOWNLOADS.get(chat_id, True):
                return None

            # m3u8 detection
            if any(x in content_type for x in ["application/vnd.apple.mpegurl", "vnd.apple.mpegurl"]):
                return await download_m3u8(url, temp_path, status_msg, chat_id)

            ext = VIDEO_EXTENSIONS.get(content_type, ".mp4")
            file_path = temp_path + ext

            # Dynamic chunk count
            if total_size < 5*1024*1024:
                workers = 1
            elif total_size < 50*1024*1024:
                workers = min(4, max_workers)
            else:
                workers = max_workers

            chunk_size = total_size // workers
            tasks = []
            for i in range(workers):
                start = i * chunk_size
                end = total_size-1 if i == workers-1 else (i+1)*chunk_size - 1
                tasks.append(download_chunk(session, url, start, end, temp_path, i, chat_id))

            downloaded_chunks = await asyncio.gather(*tasks)
            if not ACTIVE_DOWNLOADS.get(chat_id, True):
                return None

            with open(file_path, "wb") as outfile:
                for chunk_file in downloaded_chunks:
                    if chunk_file is None:
                        return None
                    with open(chunk_file, "rb") as infile:
                        outfile.write(infile.read())
                    os.remove(chunk_file)
            return file_path

async def download_m3u8(url: str, path: str, status_msg: Message, chat_id: int):
    if not ACTIVE_DOWNLOADS.get(chat_id, True):
        return None
    cmd = ["ffmpeg", "-y", "-i", url, "-c", "copy", "-threads", "4", "-bsf:a", "aac_adtstoasc", path + ".mp4"]
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    await proc.communicate()
    return path + ".mp4" if os.path.exists(path + ".mp4") else None

# ---------- Thumbnail Collage (preserve source ratio) ----------
def generate_thumbnail_collage(video_path, num_shots):
    thumbnails = []
    # Get video duration
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", video_path],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    duration = float(result.stdout)
    times = sorted(random.sample(range(int(duration)-1), min(num_shots, int(duration))))

    # Take screenshots at random times
    for i, t in enumerate(times):
        thumb_path = f"{video_path}_thumb{i}.jpg"
        subprocess.run(
            ["ffmpeg", "-ss", str(t), "-i", video_path, "-frames:v", "1", "-q:v", "2", thumb_path]
        )
        if os.path.exists(thumb_path):
            thumbnails.append(thumb_path)

    if not thumbnails:
        return None

    # Open images and get source sizes
    imgs = [Image.open(t) for t in thumbnails]

    # Use source size (no resizing) to preserve ratio
    widths, heights = zip(*(i.size for i in imgs))
    total_width = sum(widths)
    max_height = max(heights)
    collage = Image.new("RGB", (total_width, max_height), color=(0,0,0))

    x_offset = 0
    for img in imgs:
        collage.paste(img, (x_offset, 0))
        x_offset += img.width
        img.close()

    for t in thumbnails:
        os.remove(t)

    collage_path = f"{video_path}_collage.jpg"
    collage.save(collage_path)
    return collage_path

# ---------- Inline Cancel ----------
@Client.on_callback_query(filters.regex("dlcancel"))
async def cancel_callback(client: Client, query: CallbackQuery):
    ACTIVE_DOWNLOADS[query.message.chat.id] = False
    await query.message.edit("❌ Download/upload cancelled.")
    await query.answer("Cancelled!")

# ---------- Main Command ----------
@Client.on_message(filters.command(["neodl"]) & filters.private)
async def neodl_handler(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("⚡ Usage:\n`/neodl <link1> [link2] ...`")

    links = message.command[1:]
    ACTIVE_DOWNLOADS[message.chat.id] = True

    for idx, url in enumerate(links, 1):
        temp_path = os.path.join(DOWNLOAD_DIR, f"{message.chat.id}_{int(time.time())}_{idx}")
        status = await message.reply_text(
            f"📥 Starting download {idx}/{len(links)}...",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("❌ Cancel", callback_data="dlcancel")]]
            )
        )

        file_path = await download_file(url, temp_path, status, message.chat.id)
        if not file_path or not os.path.exists(file_path):
            await status.edit(f"❌ Failed to download link {idx}")
            continue

        await status.edit("✅ Starting upload...")
        start_time = time.time()
        try:
            await message.reply_video(
                file_path,
                caption=f"🎬 Video {idx}/{len(links)}",
                progress=progress_for_pyrofork,
                progress_args=(status, start_time, "Uploading")
            )
        except:
            await message.reply_document(
                file_path,
                caption=f"📂 Video {idx}/{len(links)}",
                progress=progress_for_pyrofork,
                progress_args=(status, start_time, "Uploading")
            )

        # Generate thumbnail collage (source ratio)
        if GENERATE_THUMBNAILS:
            collage = generate_thumbnail_collage(file_path, NUM_SCREENSHOTS)
            if collage and os.path.exists(collage):
                await message.reply_photo(collage, caption="📸 Video preview")
                os.remove(collage)

        os.remove(file_path)
        await status.delete()

    ACTIVE_DOWNLOADS[message.chat.id] = False
    
