import os
import aiohttp
import asyncio
import math
import time
import shutil
import subprocess
import cv2
import uuid
import imageio_ffmpeg as iio_ffmpeg
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ---------- CONFIG ----------
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

MAX_CHUNKS = 3
MAX_RETRY = 3
MAX_TITLE_LEN = 50
DELETE_AFTER = 600  # 10 minutes
CLEANUP_INTERVAL = 1800  # 30 minutes
TASKS_PER_PAGE = 10

ADMINS = [123456789]  # Set admin user IDs here
DASHBOARD_CHAT_ID = None  # Set bot chat ID where dashboard is posted

# ---------- GLOBALS ----------
TASKS = {}       # task_id -> task dict
USER_QUEUES = {} # user_id -> asyncio.Queue
CANCEL_FLAGS = {}# task_id -> bool

DASHBOARD_MSG = None
CURRENT_PAGE = 0

# ---------- HELP ----------
HELP_TEXT = (
    "📌 **Downloader Help**\n\n"
    "➡️ /dl <link>  → Download file/video.\n"
    "➡️ Multiple links supported.\n"
    "❌ M3U/M3U8 links are not supported.\n"
    "❌ /cancel2_<task_id> → Cancel specific task.\n"
)

# ---------- HELPERS ----------
def human_readable(size):
    units = ["B","KB","MB","GB","TB"]
    i = 0
    while size > 1024 and i < len(units)-1:
        size /= 1024
        i += 1
    return f"{size:.2f} {units[i]}"

def clean_title(name):
    name = name.replace('_',' ').replace('-',' ').replace('%20',' ')
    name = ' '.join(word.capitalize() for word in name.split())
    if len(name) > MAX_TITLE_LEN: name = name[:MAX_TITLE_LEN].rstrip()+"..."
    return name

def get_video_resolution(file_path):
    try:
        cap = cv2.VideoCapture(file_path)
        if cap.isOpened():
            w=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
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
            if ret: cv2.imwrite(thumb_path, frame)
        cap.release()
        if os.path.exists(thumb_path): return thumb_path
    except:
        pass
    return None

# ---------- CLEANUP ----------
async def cleanup_downloads():
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL)
        for f in os.listdir(DOWNLOAD_DIR):
            path = os.path.join(DOWNLOAD_DIR,f)
            try: os.remove(path)
            except: pass

# ---------- PROGRESS BAR ----------
def progress_bar_13(done, total):
    length = 13
    if total == 0: return "[□□□□□□□□□□□□□] 0.0%"
    blocks = ""
    fraction = done / max(total,1)
    per_block = 1/length
    for i in range(length):
        block_start = i * per_block
        block_end = (i+1) * per_block
        if fraction >= block_end:
            blocks += "■"
        elif fraction >= block_start:
            blocks += "▧"
        else:
            blocks += "□"
    percent = fraction * 100
    return f"[{blocks}] {percent:.1f}%"

# ---------- DASHBOARD ----------
def format_task(task):
    bar = progress_bar_13(task.get("done",0), task.get("total",0))
    status = task.get("status","Queued")
    processed = human_readable(task.get("done",0))
    total_str = human_readable(task.get("total",0))
    speed = human_readable(task.get("speed",0))

    # ETA
    if speed>0 and status.lower()=="downloading":
        eta_sec = int((task.get("total",0) - task.get("done",0))/speed)
        mins, secs = divmod(eta_sec, 60)
        hours, mins = divmod(mins, 60)
        eta_str = f"{hours}h{mins}m{secs}s" if hours else f"{mins}m{secs}s"
    else:
        eta_str = "-"

    elapsed_sec = int(task.get("elapsed",0))
    mins, secs = divmod(elapsed_sec,60)
    hours, mins = divmod(mins,60)
    elapsed_str = f"{hours}h{mins}m{secs}s" if hours else f"{mins}m{secs}s"

    user = task.get("user_name","Unknown")
    uid = task.get("user_id","-")
    tid = task["id"][:8]
    engine = task.get("engine","Pyrogram")

    text = (
        f"Processing Task {tid}\n"
        f"┃ {bar}\n"
        f"┠ Processed: {processed} / {total_str}\n"
        f"┠ Status: {status} | ETA: {eta_str}\n"
        f"┠ Speed: {speed}/s | Elapsed: {elapsed_str}\n"
        f"┠ Engine: {engine}\n"
        f"┠ User: {user} | ID: {uid}\n"
        f"┖ /cancel2_{tid}"
    )
    return text

async def update_dashboard(client):
    global DASHBOARD_MSG, CURRENT_PAGE
    while True:
        await asyncio.sleep(1)
        if DASHBOARD_MSG is None: continue
        tasks_sorted = list(TASKS.values())
        total_pages = max(1, math.ceil(len(tasks_sorted)/TASKS_PER_PAGE))
        CURRENT_PAGE = min(CURRENT_PAGE,total_pages-1)
        start = CURRENT_PAGE*TASKS_PER_PAGE
        end = start+TASKS_PER_PAGE
        msg_text = "\n\n".join(format_task(t) for t in tasks_sorted[start:end]) or "No tasks running."
        buttons = []
        if total_pages>1:
            row = []
            if CURRENT_PAGE>0: row.append(InlineKeyboardButton("⬅️ Prev",callback_data="dash_prev"))
            if CURRENT_PAGE<total_pages-1: row.append(InlineKeyboardButton("Next ➡️",callback_data="dash_next"))
            buttons.append(row)
        try: await DASHBOARD_MSG.edit(msg_text, reply_markup=InlineKeyboardMarkup(buttons) if buttons else None)
        except: pass

# ---------- DOWNLOAD ----------
async def fetch_chunk(session,url,start,end,part,task_id):
    headers = {"Range": f"bytes={start}-{end}"}
    async with session.get(url, headers=headers) as resp:
        with open(part,"ab") as f:
            async for chunk in resp.content.iter_chunked(1024*64):
                if CANCEL_FLAGS.get(task_id): return
                f.write(chunk)

async def download_file(url,dest,task_id):
    for attempt in range(MAX_RETRY):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url) as resp:
                    if resp.status not in (200,206): raise Exception("Invalid URL")
                    total = int(resp.headers.get("Content-Length",0))
                size = math.ceil(total/MAX_CHUNKS)
                parts = [f"{dest}.part{i}" for i in range(MAX_CHUNKS)]
                tasks = [asyncio.create_task(fetch_chunk(session,url,i*size,min((i+1)*size-1,total-1),parts[i],task_id)) for i in range(MAX_CHUNKS)]
                start_time = time.time()
                async def progress():
                    while any(not t.done() for t in tasks):
                        if CANCEL_FLAGS.get(task_id):
                            for t in tasks: t.cancel()
                            return
                        done = sum(os.path.getsize(p) for p in parts if os.path.exists(p))
                        TASKS[task_id]["done"] = done
                        TASKS[task_id]["total"] = total
                        elapsed = time.time()-start_time
                        TASKS[task_id]["elapsed"] = elapsed
                        TASKS[task_id]["speed"] = done/(elapsed+1e-6)
                        await asyncio.sleep(1)
                await asyncio.gather(*tasks, progress())
                if CANCEL_FLAGS.get(task_id): raise Exception("Cancelled")
                with open(dest,"wb") as f:
                    for p in parts:
                        if os.path.exists(p):
                            with open(p,"rb") as pf: shutil.copyfileobj(pf,f)
                            os.remove(p)
                return dest
        except Exception as e:
            if attempt+1==MAX_RETRY: raise
            await asyncio.sleep(2)

async def process_download(client, task_id):
    task = TASKS[task_id]
    url = task["url"]
    if url.endswith(".m3u") or "m3u8" in url:
        task["status"] = "M3U/M3U8 not supported ❌"
        return
    fname = clean_title(url.split("/")[-1].split("?")[0] or f"video_{int(time.time())}.mp4")
    dest = os.path.join(DOWNLOAD_DIR,fname)
    task["fname"] = fname
    task["status"] = "Downloading"
    try:
        await download_file(url,dest,task_id)
        size = os.path.getsize(dest)
        task["total"] = size
        resolution = get_video_resolution(dest)
        # Compression
        if size>2*1024*1024*1024:
            ffmpeg_path = iio_ffmpeg.get_ffmpeg_exe()
            comp = dest.replace(".mp4","_compressed.mp4")
            subprocess.run([ffmpeg_path,"-i",dest,"-b:v","1M",comp],check=False)
            if os.path.exists(comp): dest=comp
        # Upload
        task["status"]="Uploading"
        thumb = generate_thumbnail(dest)
        await client.send_video(task["chat_id"],video=dest,caption=f"🎬 {fname}",thumb=thumb,supports_streaming=True)
        os.remove(dest)
        if thumb and os.path.exists(thumb): os.remove(thumb)
        task["status"]="Completed ✅"
        await asyncio.sleep(DELETE_AFTER)
        TASKS.pop(task_id,None)
    except Exception as e:
        task["status"]=f"❌ Failed: {e}"

# ---------- WORKER ----------
async def worker(client,user_id):
    q = USER_QUEUES[user_id]
    max_parallel = 10 if user_id in ADMINS else 5
    for _ in range(max_parallel):
        asyncio.create_task(worker_loop(client,q))

async def worker_loop(client,q):
    while True:
        task_id = await q.get()
        CANCEL_FLAGS[task_id] = False
        await process_download(client, task_id)
        q.task_done()

# ---------- COMMANDS ----------
@Client.on_message(filters.command(["dl"]) & filters.private)
async def dl_cmd(client,msg):
    user_id = msg.chat.id
    urls = msg.text.split()[1:]
    if not urls: return await msg.reply("⚠️ Provide at least one URL.")
    if user_id not in USER_QUEUES:
        USER_QUEUES[user_id]=asyncio.Queue()
        await worker(client,user_id)
    for u in urls:
        tid = str(uuid.uuid4())
        TASKS[tid] = {
            "id":tid,"url":u,"chat_id":user_id,"user_id":user_id,
            "user_name":msg.from_user.first_name,"done":0,"total":0,
            "speed":0,"elapsed":0,"status":"Queued","engine":"Pyrogram"
        }
        await USER_QUEUES[user_id].put(tid)
    await msg.reply(f"✅ Added {len(urls)} task(s) to global dashboard.")
    global DASHBOARD_MSG
    if DASHBOARD_MSG is None:
        DASHBOARD_MSG = await msg.reply("Initializing dashboard...")

@Client.on_message(filters.command(["dlhelp"]) & filters.private)
async def dl_help(client,msg):
    await msg.reply(HELP_TEXT)

@Client.on_message(filters.regex(r"^/cancel2_([a-f0-9]+)"))
async def cancel_task(client,msg):
    tid = msg.text.split("_")[-1]
    if tid in TASKS:
        CANCEL_FLAGS[tid] = True
        TASKS[tid]["status"]="Cancelled ❌"

# ---------- CALLBACKS ----------
@Client.on_callback_query()
async def dash_callback(client,query):
    global CURRENT_PAGE
    if query.data=="dash_next":
        CURRENT_PAGE+=1
    elif query.data=="dash_prev":
        CURRENT_PAGE-=1
    await query.answer()

# ---------- START ----------
asyncio.create_task(cleanup_downloads())
asyncio.create_task(update_dashboard(Client))
