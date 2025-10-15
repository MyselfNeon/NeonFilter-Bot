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
import ssl
import traceback

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

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
ADMINS = {841851780}  # <-- put admin user IDs here (ints)

MAX_RETRY = 3
DELETE_AFTER = 600  # seconds after sending file to delete it
CLEANUP_INTERVAL = 1800  # remove leftover files every 30 minutes

MAX_TITLE_LEN = 80
PROGRESS_LEN = 13  # 13-block progress bar
CHUNK_SIZE = 64 * 1024  # 64 KB

# ---------- GLOBAL STATE ----------
USER_SEMAPHORES = {}
TASKS = {}
CANCEL_FLAGS = {}
UPLOAD_CHOICES = {}

# ---------- HELP TEXT ----------
HELP_TEXT = (
    "<blockquote>**⁉️ __Downloader Help__**</blockquote>\n\n"
    "**🛜** __/dl yourlink - **Start Download For the Link (Supports Multiple Links)__**\n\n"
    "**- __Each Link Shows A Progress Bar__**\n"
    "**- __To Cancel A Task, Type The Cancel Command Shown Below The Progress Message (e.g. /cancel_id)__**\n\n"
    "**❌ __M3U/M3U8 Links Not Suppored.__"
)

# ---------- UTIL HELPERS ----------
def human_readable(size: int) -> str:
    if size is None:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    s = float(size)
    while s >= 1024 and i < len(units) - 1:
        s /= 1024
        i += 1
    return f"{s:.2f} {units[i]}"

def clean_title(name: str) -> str:
    name = name.replace('_', ' ').replace('-', ' ').replace('%20', ' ')
    name = ' '.join(word.capitalize() for word in name.split())
    if len(name) > MAX_TITLE_LEN:
        name = name[:MAX_TITLE_LEN].rstrip() + "..."
    return name

def safe_filename(fname: str) -> str:
    if not fname or fname.strip() == "" or any(c in fname for c in ["\n", "\r", "/", "\\"]):
        return "Default_MyselfNeon"
    return fname

def progress_bar_13(done: int, total: int) -> str:
    length = PROGRESS_LEN
    if total is None or total == 0:
        return f"[{'□' * length}] 0.0%"
    fraction = float(done) / float(max(total, 1))
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

# ---------- CORE DOWNLOAD WITH RESUME & SSL FALLBACK ----------
async def stream_download(url: str, dest: str, task_id: str, progress_cb):
    """
    Downloads to `dest`. Supports resuming via Range if server allows it.
    Automatically retries; on SSL cert verification errors it will retry without verification.
    """
    ssl_verify = True
    headers_base = {
        "User-Agent": "Mozilla/5.0 (compatible; NeonDownloader/1.0)",
        "Accept": "*/*",
        "Accept-Encoding": "identity"  # avoid gzip altering content-length calculations
    }

    for attempt in range(1, MAX_RETRY + 1):
        if CANCEL_FLAGS.get(task_id):
            raise asyncio.CancelledError("Cancelled before start")

        try:
            # Prepare resume info
            existing = 0
            if os.path.exists(dest):
                try:
                    existing = os.path.getsize(dest)
                except:
                    existing = 0

            headers = dict(headers_base)
            if existing > 0:
                headers["Range"] = f"bytes={existing}-"

            connector = aiohttp.TCPConnector(ssl=ssl.create_default_context() if ssl_verify else False)
            timeout = aiohttp.ClientTimeout(total=None)
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                async with session.get(url, headers=headers) as resp:
                    # HTTP status handling:
                    # - 200: full content from start
                    # - 206: partial content (resume)
                    # - others: treat as errors
                    status = resp.status
                    if status not in (200, 206):
                        raise Exception(f"HTTP {status}")

                    # Determine total size
                    total = None
                    if 'Content-Range' in resp.headers:
                        # Content-Range: bytes start-end/total
                        cr = resp.headers.get('Content-Range')
                        try:
                            total = int(cr.split("/")[-1])
                        except Exception:
                            total = None
                    else:
                        # Content-Length may be remaining length for Range or total for full 200
                        cl = resp.headers.get("Content-Length")
                        try:
                            cl = int(cl) if cl is not None else None
                        except:
                            cl = None
                        if status == 200:
                            total = cl
                            existing = 0  # server ignored our range header -> we must start from 0
                        elif status == 206:
                            # Content-Length here is the remaining bytes
                            if cl is not None:
                                total = existing + cl

                    # Open file in appropriate mode
                    mode = "ab" if (status == 206 and existing > 0) else "wb"
                    written = existing if mode == "ab" else 0

                    start = time.time()
                    async for chunk in resp.content.iter_chunked(CHUNK_SIZE):
                        if CANCEL_FLAGS.get(task_id):
                            raise asyncio.CancelledError("Cancelled by user")
                        if not chunk:
                            continue
                        # write
                        with open(dest, mode) as f:
                            f.write(chunk)
                        mode = "ab"  # after first write, ensure we append
                        written += len(chunk)
                        elapsed = time.time() - start
                        speed = written / (elapsed + 1e-6)
                        eta = int((total - written) / (speed + 1e-6)) if total and speed > 0 else -1
                        await progress_cb(written, total, speed, eta)
                    # finished
                    final_total = total or written
                    return dest, final_total
        except asyncio.CancelledError:
            # bubble up cancellation so the task runner can handle it
            raise
        except (aiohttp.ClientConnectorCertificateError, aiohttp.ClientSSLError, ssl.SSLCertVerificationError) as sslerr:
            # SSL verification failed: retry without verification once
            if ssl_verify:
                ssl_verify = False
                task = TASKS.get(task_id)
                if task:
                    task["status"] = "⚠️ SSL cert issue, retrying without verification..."
                    try:
                        await task["message"].edit_text(make_task_text(task))
                    except:
                        pass
                # small backoff before retrying
                await asyncio.sleep(1)
                continue
            else:
                # already tried without verification; escalate
                raise
        except Exception as exc:
            # other errors: retry up to MAX_RETRY
            if attempt == MAX_RETRY:
                raise
            # update status if task exists
            task = TASKS.get(task_id)
            if task:
                task["status"] = f"⚠️ Error, retrying ({attempt}/{MAX_RETRY})..."
                try:
                    await task["message"].edit_text(make_task_text(task))
                except:
                    pass
            await asyncio.sleep(1)
            continue

    raise Exception("Failed to download after retries")

# ---------- TASK RUNNER ----------
async def run_task(client: Client, task_id: str):
    task = TASKS.get(task_id)
    if not task:
        return

    chat_id = task["chat_id"]
    url = task["url"]

    if url.lower().endswith(".m3u") or "m3u8" in url.lower():
        task["status"] = "**__M3U/M3U8 Not Supported__ ❌**"
        try:
            await task["message"].edit_text(make_task_text(task))
        except:
            pass
        return

    raw_name = url.split("/")[-1].split("?")[0] or ""
    ext = os.path.splitext(raw_name)[1] or ".mp4"
    base = safe_filename(os.path.splitext(raw_name)[0])
    fname = f"{base}{ext}"

    dest = os.path.join(DOWNLOAD_DIR, fname)
    task["fname"] = fname
    task["status"] = "Queued"
    try:
        await task["message"].edit_text(make_task_text(task))
    except:
        pass

    try:
        async def progress_cb(done, total, speed, eta):
            task["done"] = done
            task["total"] = total or task.get("total", 0)
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

        task["status"] = "Downloading"
        await task["message"].edit_text(make_task_text(task))

        path, total = await stream_download(url, dest, task_id, progress_cb)
        task["done"] = os.path.getsize(path)
        task["total"] = total or task["done"]
        task["elapsed"] = int(time.time() - task["start_time"])
        task["status"] = "Downloaded"
        try:
            await task["message"].edit_text(make_task_text(task))
        except:
            pass

        # Compress if > 2GB (same as before)
        if task["total"] and task["total"] > 2 * 1024 * 1024 * 1024:
            task["status"] = "Compressing 📦"
            try:
                await task["message"].edit_text(make_task_text(task))
            except:
                pass
            comp = dest.replace(ext, f"_compressed{ext}")
            ff = get_ffmpeg_bin()
            try:
                subprocess.run([ff, "-i", dest, "-b:v", "1M", comp], check=False)
                if os.path.exists(comp):
                    try:
                        os.remove(dest)
                    except:
                        pass
                    dest = comp
            except Exception:
                pass

        task["status"] = "Uploading 🚀"
        try:
            await task["message"].edit_text(make_task_text(task))
        except:
            pass

        thumb = generate_thumbnail(dest)
        upload_mode = UPLOAD_CHOICES.get(task_id, "video")

        sent_ok = False
        try:
            if upload_mode == "video":
                await client.send_video(
                    chat_id, video=dest,
                    caption=f"**🎬 __Nᴀᴍᴇ:** {fname}\n**📦 Sɪᴢᴇ:** {human_readable(os.path.getsize(dest))}__",
                    thumb=thumb, supports_streaming=True
                )
            else:
                await client.send_document(
                    chat_id, document=dest,
                    caption=f"**🎬 __Nᴀᴍᴇ:** {fname}\n**📦 Sɪᴢᴇ:** {human_readable(os.path.getsize(dest))}__"
                )
            sent_ok = True
        except Exception:
            try:
                await client.send_document(chat_id, document=dest, caption=f"**📦 __Sɪᴢᴇ:** {human_readable(os.path.getsize(dest))}__")
                sent_ok = True
            except Exception:
                sent_ok = False

        # best-effort cleanup
        try:
            if os.path.exists(dest):
                os.remove(dest)
        except:
            pass
        if thumb and os.path.exists(thumb):
            try:
                os.remove(thumb)
            except:
                pass

        task["status"] = "Completed ✅" if sent_ok else "Completed (but send failed) ❌"
        try:
            await task["message"].edit_text(make_task_text(task))
        except:
            pass

        # let user see result then delete message
        await asyncio.sleep(10)
        try:
            await task["message"].delete()
        except:
            pass
        await asyncio.sleep(DELETE_AFTER)
    except asyncio.CancelledError:
        task["status"] = "Cancelled ❌"
        try:
            await task["message"].edit_text(make_task_text(task))
        except:
            pass
    except Exception as exc:
        task["status"] = f"❌ Failed: {exc}"
        try:
            await task["message"].edit_text(make_task_text(task))
        except:
            pass
    finally:
        sem = USER_SEMAPHORES.get(task["user_id"])
        if sem:
            try:
                sem.release()
            except:
                pass
        TASKS.pop(task_id, None)
        CANCEL_FLAGS.pop(task_id, None)
        UPLOAD_CHOICES.pop(task_id, None)

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
        f"**{bar}**\n"
        f"**⚡ __Sᴛᴀᴛᴜs: {status}__**\n"
        f"**🎬 __Fɪʟᴇ: {fname}__**\n"
        f"**📦 __Pʀᴏᴄᴇssᴇᴅ: {human_readable(done)} / {human_readable(total)}__**\n"
        f"**🚀 __Sᴘᴇᴇᴅ: {speed_str} | ETA: {sec_to_hms(eta)} | Elapsed: {sec_to_hms(elapsed)}__**\n\n"
        f"**❌ __Cᴀɴᴄᴇʟ:** /cancel_{task['id']}__\n"
    )
    return text

# ---------- COMMANDS ----------
@Client.on_message(filters.command(["dl"]) & filters.private)
async def cmd_dl(client: Client, msg: Message):
    text = msg.text or ""
    parts = text.split()
    urls = parts[1:]
    if not urls:
        await msg.reply("**⚠️ __Provide At Least One URL.\n\nUsage: /dl url1 url2 ...__**")
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
        m = await msg.reply(
            "**Choose Upload Type:**",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🎥 Video", callback_data=f"video_{tid}"),
                InlineKeyboardButton("📂 Document", callback_data=f"document_{tid}")
            ]])
        )
        TASKS[tid]["message"] = m
        CANCEL_FLAGS[tid] = False
        created += 1

    await msg.reply(f"**✅ __Added {created} Task(s). Please choose format for each.__**")

@Client.on_callback_query(filters.regex(r"^(video|document)_[0-9a-fA-F]+$"))
async def cb_upload_type(client: Client, query):
    choice, tid = query.data.split("_", 1)
    if tid not in TASKS:
        await query.answer("Task not found or already finished.", show_alert=True)
        return
    UPLOAD_CHOICES[tid] = choice
    try:
        await query.message.edit("**Starting Task...**")
    except:
        pass
    asyncio.create_task(schedule_task(client, tid))

async def schedule_task(client, tid):
    task = TASKS.get(tid)
    if not task:
        return
    sem = USER_SEMAPHORES.get(task["user_id"])
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

@Client.on_message(filters.regex(r"^/cancel_([0-9a-fA-F]+)") & filters.private)
async def cmd_cancel(client: Client, msg: Message):
    tid = msg.text.split("_", 1)[1].strip()
    task = TASKS.get(tid)
    if not task:
        await msg.reply("**❌ __Task Not Found Or Finished.__**")
        return
    CANCEL_FLAGS[tid] = True
    task["status"] = "Cancelling... 🥹"
    try:
        await task["message"].edit_text(make_task_text(task))
    except:
        pass
    await msg.reply(f"**__Requested Cancel For Task {tid[:8]}.__**")

    async def delayed_delete():
        await asyncio.sleep(3)
        try:
            await task["message"].delete()
        except:
            pass
    asyncio.create_task(delayed_delete())

# ---------- COMMAND /dlhelp ----------
@Client.on_message(filters.command(["dlhelp"]) & filters.private)
async def cmd_help(client: Client, msg: Message):
    await msg.reply(HELP_TEXT)

# ---------- START CLEANUP ----------
try:
    asyncio.get_event_loop().create_task(cleanup_loop())
except RuntimeError:
    # In case event loop isn't running yet (pyrogram loads), we'll ignore here.
    pass
