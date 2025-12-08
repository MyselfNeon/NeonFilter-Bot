import os
import time
import uuid
import asyncio
import aiohttp
import ssl
import re
import mimetypes
import filetype
import shutil
from urllib.parse import unquote

from pyrogram import Client, filters
from pyrogram.types import Message

# ================= CONFIGURATION =================
DOWNLOAD_DIR = "downloads"
MAX_CONCURRENT_TASKS = 5
CHUNK_SIZE = 1024 * 1024  # 1MB
EDIT_SLEEP = 4
ADMINS = {841851780} 

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
mimetypes.init()

# ================= UTILITIES =================

def human_readable(size: int) -> str:
    if not size: return "0 B"
    power = 2**10
    n = 0
    units = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while size > power:
        size /= power
        n += 1
    return f"{size:.2f} {units.get(n, 'TB')}"

def time_formatter(seconds: int) -> str:
    if not seconds or seconds < 0: return "0s"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}h {m}m {s}s" if h else f"{m}m {s}s"

def get_progressbar(current, total):
    if not total: return "▱" * 10
    percentage = current / total
    finished_len = int(percentage * 10)
    return f"{'▰' * finished_len}{'▱' * (10 - finished_len)}"

def get_seconds(time_str):
    """Converts HH:MM:SS.ms to total seconds"""
    try:
        h, m, s = time_str.split(':')
        return int(h) * 3600 + int(m) * 60 + float(s)
    except:
        return 0

# ================= CORE ENGINES =================

async def get_filename_from_headers(response, url):
    try:
        content_disposition = response.headers.get("Content-Disposition")
        if content_disposition:
            fname = re.findall("filename=(.+)", content_disposition)
            if fname: return unquote(fname[0].strip('";'))
    except: pass
    try:
        path = unquote(url.split("?")[0])
        name = path.split("/")[-1]
        if name: return name
    except: pass
    return f"QuantumDL_{int(time.time())}"

async def generate_thumbnail(video_path: str):
    thumb_path = f"{video_path}.jpg"
    try:
        process = await asyncio.create_subprocess_exec(
            "ffmpeg", "-i", video_path, "-ss", "00:00:02", "-vframes", "1", thumb_path, "-y",
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
        )
        await process.wait()
        if os.path.exists(thumb_path): return thumb_path
    except: pass
    return None

# ================= TASK MANAGER =================

class TaskManager:
    def __init__(self):
        self.active_tasks = {}
        self.user_semaphores = {}

    def get_semaphore(self, user_id):
        if user_id not in self.user_semaphores:
            self.user_semaphores[user_id] = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
        return self.user_semaphores[user_id]

    async def add_task(self, client, message, url):
        task_id = uuid.uuid4().hex[:8]
        user_id = message.from_user.id
        
        self.active_tasks[task_id] = {
            "id": task_id,
            "url": url,
            "user_id": user_id,
            "chat_id": message.chat.id,
            "status": "queued",
            "cancel_event": asyncio.Event(),
            "message": None,
            "start_time": 0,
            "filename": "Unknown",
            "last_edit": 0,
            "process": None # For FFmpeg process
        }

        msg = await message.reply(f"**⚡ Added to Queue...**\n`{url}`", quote=True)
        self.active_tasks[task_id]["message"] = msg
        asyncio.create_task(self.execute_task(client, task_id))

    async def execute_task(self, client, task_id):
        task = self.active_tasks.get(task_id)
        if not task: return

        url = task["url"]
        msg = task["message"]
        semaphore = self.get_semaphore(task["user_id"])
        
        async with semaphore:
            if task["cancel_event"].is_set(): return
            
            # --- 1. DETECT TYPE ---
            is_m3u8 = any(x in url.lower() for x in [".m3u8", ".m3u", ".mpd"])
            
            # --- 2. EXECUTE ENGINE ---
            file_path = None
            try:
                if is_m3u8:
                    file_path = await self.download_stream(task, url)
                else:
                    file_path = await self.download_direct(task, url)

                if not file_path or task["cancel_event"].is_set():
                    return # Cancelled or failed

                # --- 3. UPLOAD ---
                await self.upload_file(client, task, file_path)

            except Exception as e:
                await msg.edit(f"**❌ Error:** `{str(e)}`")
            finally:
                if file_path and os.path.exists(file_path): os.remove(file_path)
                self.active_tasks.pop(task_id, None)

    # --- ENGINE A: DIRECT DOWNLOADER (aiohttp) ---
    async def download_direct(self, task, url):
        task["start_time"] = time.time()
        task["status"] = "downloading"
        msg = task["message"]
        
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        async with aiohttp.ClientSession() as session:
            async with session.get(url, ssl=ssl_ctx) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}")

                fname = await get_filename_from_headers(response, url)
                
                # Correction for files with no extension
                if "." not in fname:
                    fname += ".dat"
                
                task["filename"] = fname
                file_path = os.path.join(DOWNLOAD_DIR, fname)
                total_size = int(response.headers.get("Content-Length", 0))
                downloaded = 0
                
                with open(file_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(CHUNK_SIZE):
                        if task["cancel_event"].is_set():
                            await msg.edit("**🚫 Cancelled.**")
                            return None
                        f.write(chunk)
                        downloaded += len(chunk)
                        await self.update_progress(msg, task, downloaded, total_size, "📥 Downloading")

        # Magic Number Check for Rename
        kind = filetype.guess(file_path)
        if kind:
            current_ext = os.path.splitext(file_path)[1]
            if not current_ext or current_ext.lower() != f".{kind.extension}":
                new_fname = f"{os.path.splitext(task['filename'])[0]}.{kind.extension}"
                new_path = os.path.join(DOWNLOAD_DIR, new_fname)
                os.rename(file_path, new_path)
                file_path = new_path
                task["filename"] = new_fname

        return file_path

    # --- ENGINE B: STREAM DOWNLOADER (FFmpeg) ---
    async def download_stream(self, task, url):
        task["start_time"] = time.time()
        task["status"] = "recording"
        msg = task["message"]
        
        # Name defaults to MP4 for streams
        fname = f"Stream_{int(time.time())}.mp4"
        task["filename"] = fname
        file_path = os.path.join(DOWNLOAD_DIR, fname)
        
        await msg.edit("**🔄 Starting Stream Recording (FFmpeg)...**")

        # 1. Get Total Duration first (optional, helps progress)
        total_duration = 0
        try:
            cmd_probe = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", url]
            proc_probe = await asyncio.create_subprocess_exec(*cmd_probe, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, _ = await proc_probe.communicate()
            total_duration = float(stdout.decode().strip())
        except:
            total_duration = 0 # Live stream or fail to probe

        # 2. Start Download
        # -bsf:a aac_adtstoasc fixes audio issues in m3u8 to mp4 conversion
        cmd = [
            "ffmpeg", "-i", url, "-c", "copy", "-bsf:a", "aac_adtstoasc", "-y", file_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        task["process"] = process

        # Monitor Progress from stderr
        while True:
            if task["cancel_event"].is_set():
                process.kill()
                await msg.edit("**🚫 Cancelled.**")
                return None
            
            line = await process.stderr.readline()
            if not line:
                break
            
            line_str = line.decode('utf-8', errors='ignore')
            
            # Parse "time=00:00:15.40"
            if "time=" in line_str:
                try:
                    time_match = re.search(r"time=(\d{2}:\d{2}:\d{2}\.\d{2})", line_str)
                    if time_match:
                        current_time = get_seconds(time_match.group(1))
                        # For streams, we pass Time (seconds) instead of Bytes
                        await self.update_progress(msg, task, current_time, total_duration, "🔴 Recording Stream", is_time=True)
                except: pass

        await process.wait()
        
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            return file_path
        raise Exception("Stream download failed or empty.")

    # --- COMMON UPLOAD HANDLER ---
    async def upload_file(self, client, task, file_path):
        msg = task["message"]
        task["status"] = "uploading"
        
        # Detect video
        is_video = False
        kind = filetype.guess(file_path)
        if kind and kind.mime.startswith("video"): is_video = True
        else:
            mime = mimetypes.guess_type(file_path)[0]
            if mime and mime.startswith("video"): is_video = True
            elif file_path.endswith(".mp4") or file_path.endswith(".mkv"): is_video = True

        thumb = None
        if is_video:
            await msg.edit(f"**🖼️ Generating Thumbnail...**")
            thumb = await generate_thumbnail(file_path)

        async def upload_progress(current, total):
            if task["cancel_event"].is_set(): client.stop_transmission()
            await self.update_progress(msg, task, current, total, "🚀 Uploading")

        await msg.edit(f"**📤 Uploading...**")
        
        caption = f"**🎬 {task['filename']}**\n**📦 Size:** `{human_readable(os.path.getsize(file_path))}`"
        
        try:
            if is_video:
                await client.send_video(
                    task["chat_id"], video=file_path, caption=caption,
                    thumb=thumb, supports_streaming=True, progress=upload_progress
                )
            else:
                await client.send_document(
                    task["chat_id"], document=file_path, caption=caption,
                    thumb=thumb, progress=upload_progress
                )
            await msg.edit(f"**✅ Completed!**\n`{task['filename']}`")
        except Exception as e:
            # Fallback for weird files
            await client.send_document(
                task["chat_id"], document=file_path, caption=caption, progress=upload_progress
            )
            await msg.edit(f"**✅ Completed!**")
            
        if thumb and os.path.exists(thumb): os.remove(thumb)

    async def update_progress(self, message, task, current, total, stage, is_time=False):
        now = time.time()
        if (now - task["last_edit"] < EDIT_SLEEP) and (current < total if total else True): return
        
        task["last_edit"] = now
        elapsed = now - task["start_time"]
        
        if is_time:
            # Time Based Progress (For Streams)
            percent = (current / total * 100) if total else 0
            prog_bar = get_progressbar(current, total)
            status_str = f"**⏱ Duration:** `{time_formatter(current)}` / `{time_formatter(total)}`"
            eta_str = "Live Stream" if not total else time_formatter(total - current)
        else:
            # Size Based Progress (For Direct DL / Upload)
            speed = current / elapsed if elapsed > 0 else 0
            percent = (current / total * 100) if total else 0
            prog_bar = get_progressbar(current, total)
            status_str = f"**💾 Size:** `{human_readable(current)} / {human_readable(total)}`"
            eta_str = time_formatter((total - current) / speed) if speed > 0 and total else "0s"
            status_str += f"\n**⚡ Speed:** `{human_readable(speed)}/s`"

        text = (
            f"**{stage}**\n"
            f"**File:** `{task['filename']}`\n"
            f"**{prog_bar}** `{percent:.1f}%`\n\n"
            f"{status_str}\n"
            f"**⏳ ETA:** `{eta_str}`\n\n"
            f"**🚫 Cancel:** `/cancel_{task['id']}`"
        )
        try: await message.edit(text)
        except: pass

    async def cancel_task(self, task_id):
        if task_id in self.active_tasks:
            self.active_tasks[task_id]["cancel_event"].set()
            # If FFmpeg is running, kill it
            proc = self.active_tasks[task_id].get("process")
            if proc:
                try: proc.kill()
                except: pass
            return True
        return False

manager = TaskManager()

# ================= COMMANDS =================

@Client.on_message(filters.command(["dl", "leech"]) & filters.private)
async def dl_handler(client, message):
    if len(message.command) < 2:
        return await message.reply("**⚠️ Usage:** `/dl url`")
    
    url = message.command[1]
    if not url.startswith("http"):
        return await message.reply("**❌ Invalid URL.**")

    await manager.add_task(client, message, url)

@Client.on_message(filters.regex(r"^/cancel_") & filters.private)
async def cancel_handler(client, message):
    task_id = message.text.split("_")[1]
    if await manager.cancel_task(task_id):
        await message.reply(f"**🛑 Task Cancelled.**")
    else:
        await message.reply("**❌ Task not active.**")
