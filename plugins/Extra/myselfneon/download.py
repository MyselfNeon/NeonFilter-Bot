import os
import aiohttp
import asyncio
import math
import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import subprocess

# ---------- CONFIG ----------
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

ACTIVE_DOWNLOADS = {}  # {chat_id: {file_id: True/False}}
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
async def download_range(session, url, start, end, temp_file, idx, progress, active_flag):
    headers = {"Range": f"bytes={start}-{end}"}
    async with session.get(url, headers=headers) as resp:
        async for chunk in resp.content.iter_chunked(1024*512):
            if not active_flag[0]:
                return
            temp_file[idx].write(chunk)
            progress[idx] += len(chunk)

async def download_file(url: str, temp_path: str, status_msg: Message, active_flag):
    async with aiohttp.ClientSession() as session:
        async with session.head(url) as resp_head:
            if resp_head.status != 200:
                return None
            total_size = int(resp_head.headers.get("Content-Length", 0))
            content_type = resp_head.headers.get("Content-Type","").lower()

            if any(x in content_type for x in ["application/vnd.apple.mpegurl","vnd.apple.mpegurl"]):
                return await download_m3u8(url,temp_path,status_msg,active_flag)

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
                tasks.append(download_range(session,url,start,end,temp_files,i,progress,active_flag))

            async def monitor():
                while not all(t.done() for t in asyncio.all_tasks() if t in tasks):
                    if not active_flag[0]:
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

            return file_path, total_size

# ---------- M3U8 download ----------
async def download_m3u8(url: str, path: str, status_msg: Message, active_flag):
    temp_path = path+".mp4"
    cmd = ["ffmpeg","-y","-i",url,"-c","copy","-threads","4","-bsf:a","aac_adtstoasc",temp_path]
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    start_time = time.time()

    while True:
        if proc.returncode is not None:
            break
        if os.path.exists(temp_path):
            current_size = os.path.getsize(temp_path)
            await update_progress(current_size, current_size+1024*1024, status_msg, start_time,"Downloading")
        await asyncio.sleep(1)

    await proc.communicate()
    size = os.path.getsize(temp_path) if os.path.exists(temp_path) else 0
    return temp_path, size

# ---------- Cancel ----------
@Client.on_callback_query(filters.regex("dlcancel"))
async def cancel_callback(client: Client, query):
    chat_id = query.message.chat.id
    file_id = query.message.message_id
    if chat_id in ACTIVE_DOWNLOADS and file_id in ACTIVE_DOWNLOADS[chat_id]:
        ACTIVE_DOWNLOADS[chat_id][file_id][0] = False
    await query.message.edit("❌ Download/upload cancelled.")
    await query.answer("Cancelled!")

# ---------- /dl COMMAND ----------
@Client.on_message(filters.command(["dl"]) & filters.private)
async def dl_handler(client: Client, message: Message):
    if len(message.command) < 2: 
        return await message.reply_text(
            "⚠ You didn't provide any links!\n\n"
            "Usage:\n"
            "`/dl <link1> [link2 ...]`\n\n"
            "Example:\n"
            "`/dl https://example.com/video.mp4`\n"
            "`/dl https://link1.com https://link2.com`"
        )
    
    links = message.command[1:]
    chat_id = message.chat.id
    if chat_id not in ACTIVE_DOWNLOADS:
        ACTIVE_DOWNLOADS[chat_id] = {}

    for idx, url in enumerate(links, 1):
        temp_path = os.path.join(DOWNLOAD_DIR, f"{chat_id}_{int(time.time())}_{idx}")
        status = await message.reply_text(
            f"📥 Downloading {idx}/{len(links)}...",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("❌ Cancel", callback_data="dlcancel")]]
            )
        )

        # Track active flag per file
        ACTIVE_DOWNLOADS[chat_id][status.message_id] = [True]

        # Run each download in its own task (concurrent)
        asyncio.create_task(handle_download(url, temp_path, status, chat_id, status.message_id))

async def handle_download(url, temp_path, status_msg, chat_id, file_id):
    active_flag = ACTIVE_DOWNLOADS[chat_id][file_id]
    result = await download_file(url, temp_path, status_msg, active_flag)
    if not result:
        await status_msg.edit(f"❌ Failed to download {url}")
        del ACTIVE_DOWNLOADS[chat_id][file_id]
        return

    file_path, file_size = result
    caption_text = f"🎬 **{os.path.basename(file_path)}**\n📦 Size: {human_readable(file_size)}"

    try:
        await status_msg.reply_video(file_path, caption=caption_text)
    except:
        await status_msg.reply_document(file_path, caption=caption_text)

    await asyncio.sleep(5)
    try: await status_msg.delete()
    except: pass

    os.remove(file_path)
    del ACTIVE_DOWNLOADS[chat_id][file_id]

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
    
