import os
import aiohttp
import asyncio
import math
import time
import shutil
import subprocess
import cv2
import m3u8
import ffmpeg
from pyrogram import Client, filters
from pyrogram.types import Message

# ---------- CONFIG ----------
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

PROGRESS_BAR_LEN = 16
MAX_CHUNKS = 3
MAX_RETRY = 3
MAX_TITLE_LEN = 50
DELETE_AFTER = 600  # 10 minutes
CLEANUP_INTERVAL = 1800  # 30 minutes
MAX_PARALLEL = 5  # m3u8 parallel segment downloads

USER_QUEUES = {}   # chat_id -> asyncio.Queue
USER_ACTIVE = {}   # chat_id -> bool
USER_VIDEO_COUNT = {}  # chat_id -> incremental counter for m3u8 filenames

HELP_TEXT = (
    "📌 **Downloader Help**\n\n"
    "➡️ /dl <link>  → Download file/video.\n"
    "➡️ Multiple links supported.\n"
    "➡️ /dlcancel   → Cancel your current download.\n\n"
    "⚡ Files >2GB auto-compress.\n"
    f"⚠ All uploaded videos are deleted after {DELETE_AFTER//60} minutes."
)

# ---------- HELPERS ----------
def human_readable(size):
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size > 1024 and i < len(units)-1:
        size /= 1024
        i += 1
    return f"{size:.2f} {units[i]}"

def progress_bar(done, total):
    if total == 0:
        return "[????????????]"
    filled = int(PROGRESS_BAR_LEN * done / total)
    bar = "▰"*filled + "▱"*(PROGRESS_BAR_LEN-filled)
    percent = (done/total)*100
    return f"[{bar}] {percent:.1f}%"

def clean_title(name):
    name = name.replace('_',' ').replace('-',' ').replace('%20',' ')
    name = ' '.join(word.capitalize() for word in name.split())
    if len(name) > MAX_TITLE_LEN:
        name = name[:MAX_TITLE_LEN].rstrip() + "..."
    return name

def get_video_resolution(file_path):
    try:
        cap = cv2.VideoCapture(file_path)
        if cap.isOpened():
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            return f"{w}x{h}"
    except:
        pass
    return None

def generate_thumbnail(file_path):
    thumb_path = f"thumb_{int(time.time())}.jpg"
    try:
        cap = cv2.VideoCapture(file_path)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                cv2.imwrite(thumb_path, frame)
        cap.release()
        if os.path.exists(thumb_path):
            return thumb_path
    except:
        pass
    return None

async def cleanup_downloads():
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL)
        for f in os.listdir(DOWNLOAD_DIR):
            path = os.path.join(DOWNLOAD_DIR,f)
            try:
                os.remove(path)
            except: pass

# ---------- NORMAL FILE DOWNLOAD ----------
async def fetch_chunk(session, url, start, end, part):
    headers = {"Range": f"bytes={start}-{end}"}
    async with session.get(url, headers=headers) as resp:
        with open(part, "ab") as f:
            async for chunk in resp.content.iter_chunked(1024*64):
                f.write(chunk)

async def download_file(url, dest, cb):
    for attempt in range(MAX_RETRY):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url) as resp:
                    if resp.status not in (200,206):
                        raise Exception("❌ Invalid URL")
                    total = int(resp.headers.get("Content-Length",0))
                size = math.ceil(total/MAX_CHUNKS)
                parts = [f"{dest}.part{i}" for i in range(MAX_CHUNKS)]
                tasks = [asyncio.create_task(fetch_chunk(session,url,i*size,min((i+1)*size-1,total-1),parts[i])) for i in range(MAX_CHUNKS)]
                start_time = time.time()
                async def progress():
                    while any(not t.done() for t in tasks):
                        done = sum(os.path.getsize(p) for p in parts if os.path.exists(p))
                        elapsed = time.time()-start_time
                        speed = done/(elapsed+1e-6)
                        eta = (total-done)/(speed+1e-6)
                        await cb(done,total,speed,eta)
                        await asyncio.sleep(1)
                await asyncio.gather(*tasks, progress())
                with open(dest,"wb") as f:
                    for p in parts:
                        if os.path.exists(p):
                            with open(p,"rb") as pf:
                                shutil.copyfileobj(pf,f)
                            os.remove(p)
                return dest
        except Exception as e:
            if attempt+1==MAX_RETRY:
                raise
            await asyncio.sleep(2)

# ---------- M3U8 DOWNLOAD ----------
def make_progress_bar(done, total):
    filled = int(PROGRESS_BAR_LEN * done / total)
    bar = "█" * filled + "░" * (PROGRESS_BAR_LEN - filled)
    percent = (done / total) * 100
    return f"[{bar}] {percent:.1f}%"

async def fetch_segment(session, url, path):
    async with session.get(url) as resp:
        if resp.status != 200:
            raise Exception(f"Failed segment {url}")
        with open(path, "wb") as f:
            f.write(await resp.read())

async def download_m3u8(url, output_path, status_msg: Message):
    playlist = m3u8.load(url)
    if not playlist.segments:
        raise Exception("No video segments in M3U8")

    total = len(playlist.segments)
    completed = 0
    semaphore = asyncio.Semaphore(MAX_PARALLEL)

    async with aiohttp.ClientSession() as session:
        async def fetch_and_track(idx, seg_url):
            nonlocal completed
            seg_path = os.path.join(DOWNLOAD_DIR, f"seg_{idx}.ts")
            async with semaphore:
                await fetch_segment(session, seg_url, seg_path)
            completed += 1
            if completed % 5 == 0 or completed == total:
                bar = make_progress_bar(completed, total)
                await status_msg.edit_text(f"📥 Downloading m3u8...\n{bar}")

        tasks = []
        for idx, segment in enumerate(playlist.segments, start=1):
            tasks.append(fetch_and_track(idx, segment.absolute_uri))

        await asyncio.gather(*tasks)

    # Merge segments
    segments_file = os.path.join(DOWNLOAD_DIR, "segments.txt")
    with open(segments_file, "w") as f:
        for idx in range(1, total + 1):
            f.write(f"file 'seg_{idx}.ts'\n")

    ffmpeg.input(segments_file, format="concat", safe=0).output(
        output_path, c="copy"
    ).run(overwrite_output=True)

# ---------- PROCESS ----------
async def process_download(client,msg,url):
    chat_id = msg.chat.id
    raw_name = url.split("/")[-1].split("?")[0]

    # Handle m3u8 separately
    if raw_name.endswith(".m3u") or raw_name.endswith(".m3u8") or "m3u8" in raw_name:
        USER_VIDEO_COUNT[chat_id] = USER_VIDEO_COUNT.get(chat_id, 0) + 1
        fname = f"Video_{USER_VIDEO_COUNT[chat_id]}.mp4"
        dest = os.path.join(DOWNLOAD_DIR, fname)
        status = await msg.reply("⏳ Starting m3u8 download...")
        try:
            await download_m3u8(url, dest, status)
            size = os.path.getsize(dest)
            resolution = get_video_resolution(dest)
            thumb = generate_thumbnail(dest)
            caption = f"🎬 **{fname}**\n📦 {human_readable(size)}"
            if resolution:
                caption+=f"\n📺 {resolution}"
            sent_msg = await client.send_video(chat_id,video=dest,caption=caption,thumb=thumb,supports_streaming=True)
            await status.delete()
            os.remove(dest)
            if thumb and os.path.exists(thumb):
                os.remove(thumb)
            await asyncio.sleep(DELETE_AFTER)
            try:
                await client.delete_messages(chat_id,sent_msg.message_id)
            except: pass
        except Exception as e:
            await status.edit(f"❌ Failed: {e}")
        finally:
            # cleanup ts files
            for f in os.listdir(DOWNLOAD_DIR):
                if f.endswith(".ts") or f=="segments.txt":
                    try: os.remove(os.path.join(DOWNLOAD_DIR,f))
                    except: pass
        return

    # Normal direct download
    fname = raw_name or f"video_{int(time.time())}.mp4"
    fname = clean_title(fname)
    dest = os.path.join(DOWNLOAD_DIR,fname)
    status = await msg.reply("⏳ Starting download...")
    async def cb(done,total,speed,eta):
        bar = progress_bar(done,total)
        text = f"📥 **Downloading** {fname}\n\n{bar}\n📦 {human_readable(done)}/{human_readable(total)}\n⚡ {human_readable(speed)}/s\n⏳ {int(eta)}s left"
        await status.edit(text)
    try:
        await download_file(url,dest,cb)
        size = os.path.getsize(dest)
        resolution = get_video_resolution(dest)
        if size>2*1024*1024*1024:
            comp = dest.replace(".mp4","_compressed.mp4")
            cmd = ["ffmpeg","-i",dest,"-b:v","1M",comp]
            subprocess.run(cmd,check=False)
            if os.path.exists(comp):
                dest=comp
        thumb = generate_thumbnail(dest)
        caption = f"🎬 **{fname}**\n📦 {human_readable(size)}"
        if resolution:
            caption+=f"\n📺 {resolution}"
        sent_msg = await client.send_video(chat_id,video=dest,caption=caption,thumb=thumb,supports_streaming=True)
        await status.delete()
        os.remove(dest)
        if thumb and os.path.exists(thumb):
            os.remove(thumb)
        await asyncio.sleep(DELETE_AFTER)
        try:
            await client.delete_messages(chat_id,sent_msg.message_id)
        except: pass
    except Exception as e:
        await status.edit(f"❌ Failed: {e}")

# ---------- QUEUE ----------
async def worker(client,chat_id):
    q = USER_QUEUES[chat_id]
    while True:
        url,msg = await q.get()
        if not USER_ACTIVE.get(chat_id,True):
            q.task_done()
            continue
        await process_download(client,msg,url)
        q.task_done()

# ---------- COMMANDS ----------
@Client.on_message(filters.command(["dl"]) & filters.private)
async def dl_cmd(client,msg):
    chat_id = msg.chat.id
    urls = msg.text.split()[1:]
    if not urls:
        return await msg.reply("⚠️ Provide at least one URL.")
    if chat_id not in USER_QUEUES:
        USER_QUEUES[chat_id]=asyncio.Queue()
        USER_ACTIVE[chat_id]=True
        asyncio.create_task(worker(client,chat_id))
    for u in urls:
        await USER_QUEUES[chat_id].put((u,msg))
    await msg.reply("✅ Added to queue ⏳")

@Client.on_message(filters.command(["dlhelp"]) & filters.private)
async def dl_help(client,msg):
    await msg.reply(HELP_TEXT)

@Client.on_message(filters.command(["dlcancel"]) & filters.private)
async def dl_cancel(client,msg):
    chat_id = msg.chat.id
    if chat_id not in USER_ACTIVE or not USER_ACTIVE[chat_id]:
        return await msg.reply("⚠️ No active download to cancel.")
    USER_ACTIVE[chat_id] = False
    if chat_id in USER_QUEUES:
        while not USER_QUEUES[chat_id].empty():
            try: USER_QUEUES[chat_id].get_nowait()
            except: pass
    await msg.reply("🛑 Download canceled.")

# ---------- AUTO CLEANUP ----------
async def start_cleanup():
    asyncio.create_task(cleanup_downloads())
    
