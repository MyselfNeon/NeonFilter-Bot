# plugins/download_single.py
import os
import aiohttp
import asyncio
import math
import time
import shutil
import subprocess
import cv2
import uuid
import traceback

from pyrogram import Client, filters
from pyrogram.types import Message

# Try to use imageio-ffmpeg if available for a bundled ffmpeg binary.
try:
    import imageio_ffmpeg as iio_ffmpeg
    _FFMPEG_BIN = iio_ffmpeg.get_ffmpeg_exe()
except Exception:
    _FFMPEG_BIN = "ffmpeg"  # rely on system ffmpeg if present

# ---------- CONFIG ----------
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

MAX_PARALLEL_NORMAL = 5
MAX_PARALLEL_ADMIN = 10
ADMINS = {123456789}  # <-- put admin user IDs here (ints)

MAX_RETRY = 3
DELETE_AFTER = 600  # seconds after sending file to delete it
CLEANUP_INTERVAL = 1800  # remove leftover files every 30 minutes

MAX_TITLE_LEN = 80
PROGRESS_LEN = 13  # 13-block progress bar

# ---------- GLOBAL STATE ----------
USER_SEMAPHORES = {}   # user_id -> asyncio.Semaphore
TASKS = {}             # task_id -> task dict
CANCEL_FLAGS = {}      # task_id -> bool

# ---------- HELP TEXT ----------
HELP_TEXT = (
    "📌 **Downloader Help**\n\n"
    "➡️ /dl <link>  → Start download for the link (supports multiple links).\n"
    "➡️ Each link will get its own progress message.\n"
    "➡️ To cancel a task, type the cancel command shown below the progress message (e.g. /cancel_<id>).\n"
    "❌ M3U/M3U8 links are not supported."
)

# ---------- UTIL HELPERS ----------
def human_readable(size: int) -> str:
    if size is None:
        return "0 B"
    units = ["B","KB","MB","GB","TB"]
    i = 0
    s = float(size)
    while s >= 1024 and i < len(units)-1:
        s /= 1024
        i += 1
    return f"{s:.2f} {units[i]}"

def clean_title(name: str) -> str:
    name = name.replace('_',' ').replace('-',' ').replace('%20',' ')
    name = ' '.join(word.capitalize() for word in name.split())
    if len(name) > MAX_TITLE_LEN:
        name = name[:MAX_TITLE_LEN].rstrip() + "..."
    return name

def progress_bar_13(done: int, total: int) -> str:
    length = PROGRESS_LEN
    if total is None or total == 0:
        blocks = "□" * length
        return f"[{blocks}] 0.0%"
    fraction = float(done) / float(max(total,1))
    blocks = ""
    per_block = 1.0 / length
    for i in range(length):
        start = i * per_block
        end = (i + 1) * per_block
        if fraction >= end:
            blocks += "■"
        elif fraction >= start:
            blocks += "▧"
        else:
            blocks += "□"
    percent = fraction * 100
    return f"[{blocks}] {percent:.1f}%"

def get_ffmpeg_bin() -> str:
    return _FFMPEG_BIN

def get_video_resolution(file_path: str):
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

def generate_thumbnail(file_path: str):
    thumb_path = os.path.join(DOWNLOAD_DIR, f"thumb_{int(time.time())}.jpg")
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

# ---------- CLEANUP LOOP ----------
async def cleanup_loop():
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL)
        try:
            for f in os.listdir(DOWNLOAD_DIR):
                path = os.path.join(DOWNLOAD_DIR, f)
                try:
                    os.remove(path)
                except:
                    pass
        except:
            pass

# ---------- CORE DOWNLOAD ----------
async def stream_download(url: str, dest: str, task_id: str, progress_cb):
    for attempt in range(1, MAX_RETRY + 1):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=None)) as resp:
                    if resp.status != 200:
                        raise Exception(f"HTTP {resp.status}")
                    total = int(resp.headers.get("Content-Length", 0) or 0)
                    done = 0
                    start = time.time()
                    with open(dest, "wb") as f:
                        async for chunk in resp.content.iter_chunked(64 * 1024):
                            if CANCEL_FLAGS.get(task_id):
                                try:
                                    f.close()
                                except: pass
                                raise asyncio.CancelledError("Cancelled by user")
                            f.write(chunk)
                            done += len(chunk)
                            elapsed = time.time() - start
                            speed = done / (elapsed + 1e-6)
                            eta = int((total - done) / (speed + 1e-6)) if total and speed > 0 else -1
                            try:
                                await progress_cb(done, total, speed, eta)
                            except Exception:
                                pass
                    return dest, total
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            if attempt == MAX_RETRY:
                raise
            await asyncio.sleep(1)
    raise Exception("Failed to download")

# ---------- TASK RUNNER ----------
async def run_task(client: Client, task_id: str):
    task = TASKS.get(task_id)
    if not task:
        return

    chat_id = task["chat_id"]
    url = task["url"]

    if url.lower().endswith(".m3u") or "m3u8" in url.lower():
        task["status"] = "M3U/M3U8 not supported ❌"
        try:
            await task["message"].edit_text(make_task_text(task))
        except: pass
        return

    raw_name = url.split("/")[-1].split("?")[0] or f"video_{int(time.time())}.mp4"
    fname = clean_title(raw_name)
    dest = os.path.join(DOWNLOAD_DIR, fname)
    task["fname"] = fname
    task["status"] = "Downloading"
    try:
        await task["message"].edit_text(make_task_text(task))
    except: pass

    try:
        async def progress_cb(done, total, speed, eta):
            task["done"] = done
            task["total"] = total
            task["speed"] = speed
            task["eta"] = eta
            task["elapsed"] = int(time.time() - task["start_time"])
            now = time.time()
            if now - task.get("_last_update", 0) >= 1:
                task["_last_update"] = now
                try:
                    await task["message"].edit_text(make_task_text(task))
                except:
                    pass

        path, total = await stream_download(url, dest, task_id, progress_cb)
        task["done"] = os.path.getsize(path)
        task["total"] = total or task["done"]
        task["elapsed"] = int(time.time() - task["start_time"])
        try:
            await task["message"].edit_text(make_task_text(task))
        except: pass

        if task["total"] > 2 * 1024 * 1024 * 1024:
            task["status"] = "Compressing"
            try:
                await task["message"].edit_text(make_task_text(task))
            except: pass
            comp = dest.replace(".mp4", "_compressed.mp4")
            ff = get_ffmpeg_bin()
            try:
                subprocess.run([ff, "-i", dest, "-b:v", "1M", comp], check=False)
                if os.path.exists(comp):
                    os.remove(dest)
                    dest = comp
            except Exception:
                pass

        task["status"] = "Uploading"
        try:
            await task["message"].edit_text(make_task_text(task))
        except: pass

        thumb = None
        try:
            thumb = generate_thumbnail(dest)
        except:
            thumb = None

        try:
            await client.send_video(chat_id, video=dest, caption=f"🎬 {fname}\n📦 {human_readable(os.path.getsize(dest))}", thumb=thumb, supports_streaming=True)
        except Exception:
            try:
                await client.send_document(chat_id, document=dest, caption=f"📦 {human_readable(os.path.getsize(dest))}")
            except:
                pass

        try:
            if os.path.exists(dest):
                os.remove(dest)
        except: pass
        if thumb and os.path.exists(thumb):
            try: os.remove(thumb)
            except: pass

        task["status"] = "Completed ✅"
        try:
            await task["message"].edit_text(make_task_text(task))
        except: pass

        # 🆕 delete progress/queued message after 10 sec
        try:
            await asyncio.sleep(10)
            await task["message"].delete()
        except:
            pass

        await asyncio.sleep(DELETE_AFTER)
    except asyncio.CancelledError:
        task["status"] = "Cancelled ❌"
        try:
            await task["message"].edit_text(make_task_text(task))
        except: pass
    except Exception as exc:
        task["status"] = f"❌ Failed: {exc}"
        try:
            await task["message"].edit_text(make_task_text(task))
        except: pass
    finally:
        sem = USER_SEMAPHORES.get(task["user_id"])
        if sem:
            try:
                sem.release()
            except: pass
        TASKS.pop(task_id, None)
        CANCEL_FLAGS.pop(task_id, None)

# ---------- UI ----------
def make_task_text(task: dict) -> str:
    fname = task.get("fname", task.get("url", "")).strip()
    status = task.get("status", "Queued")
    done = task.get("done", 0)
    total = task.get("total", 0)
    speed = task.get("speed", 0)
    eta = task.get("eta", -1)
    elapsed = task.get("elapsed", 0)

    bar = progress_bar_13(done, total)
    speed_str = human_readable(int(speed)) + "/s" if speed else "0 B/s"

    def sec_to_hms(s):
        if s is None or s < 0:
            return "-"
        s = int(s)
        h, r = divmod(s, 3600)
        m, s = divmod(r, 60)
        if h:
            return f"{h}h{m}m{s}s"
        if m:
            return f"{m}m{s}s"
        return f"{s}s"

    text = (
        f"{bar}\n"
        f"Status: {status}\n"
        f"File: {fname}\n"
        f"Processed: {human_readable(done)} / {human_readable(total)}\n"
        f"Speed: {speed_str} | ETA: {sec_to_hms(eta)} | Elapsed: {sec_to_hms(elapsed)}\n\n"
        f"Cancel: /cancel_{task['id']}\n"
    )
    return text

# ---------- COMMANDS ----------
@Client.on_message(filters.command(["dl"]) & filters.private)
async def cmd_dl(client: Client, msg: Message):
    text = msg.text or ""
    parts = text.split()
    urls = parts[1:]
    if not urls:
        await msg.reply("⚠️ Provide at least one URL. Usage: /dl <url1> <url2> ...")
        return

    user_id = msg.from_user.id
    max_parallel = MAX_PARALLEL_ADMIN if user_id in ADMINS else MAX_PARALLEL_NORMAL

    sem = USER_SEMAPHORES.get(user_id)
    if sem is None:
        sem = asyncio.Semaphore(max_parallel)
        USER_SEMAPHORES[user_id] = sem

    created = 0
    for url in urls:
        tid = uuid.uuid4().hex
        TASKS[tid] = {
            "id": tid,
            "url": url,
            "chat_id": msg.chat.id,
            "user_id": user_id,
            "user_name": getattr(msg.from_user, "first_name", "User"),
            "status": "Queued",
            "done": 0,
            "total": 0,
            "speed": 0,
            "eta": -1,
            "elapsed": 0,
            "fname": None,
            "_last_update": 0,
            "start_time": time.time()
        }
        try:
            m = await msg.reply(make_task_text(TASKS[tid]))
        except Exception:
            m = await msg.reply("Starting task...")
        TASKS[tid]["message"] = m
        CANCEL_FLAGS[tid] = False
        created += 1

        async def schedule_task(client, tid):
            sem = USER_SEMAPHORES.get(user_id)
            await sem.acquire()
            if CANCEL_FLAGS.get(tid):
                TASKS[tid]["status"] = "Cancelled ❌"
                try:
                    await TASKS[tid]["message"].edit_text(make_task_text(TASKS[tid]))
                except:
                    pass
                sem.release()
                return
            TASKS[tid]["start_time"] = time.time()
            await run_task(client, tid)

        asyncio.create_task(schedule_task(client, tid))

    await msg.reply(f"✅ Added {created} task(s). Each link has its own progress message.")

@Client.on_message(filters.regex(r"^/cancel_([0-9a-fA-F]+)") & filters.private)
async def cmd_cancel(client: Client, msg: Message):
    tid = msg.text.split("_", 1)[1].strip()
    task = TASKS.get(tid)
    if not task:
        await msg.reply("❌ Task not found or already finished.")
        return
    CANCEL_FLAGS[tid] = True
    task["status"] = "Cancelling..."
    try:
        await task["message"].edit_text(make_task_text(task))
    except:
        pass
    await msg.reply(f"Requested cancel for task {tid[:8]}.")

    # 🆕 Delete progress message after 3 sec when cancelled
    async def delayed_delete():
        await asyncio.sleep(3)
        try:
            await task["message"].delete()
        except:
            pass
    asyncio.create_task(delayed_delete())

# ---------- START CLEANUP ----------
asyncio.get_event_loop().create_task(cleanup_loop())
