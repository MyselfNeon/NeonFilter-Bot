import os
import time
import uuid
import asyncio
import aiohttp
import ssl
import re
import json
import filetype
from urllib.parse import unquote

# --- Render / Vps Support ---
try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
except ImportError:
    print("Static FFmpeg not found, relying on system PATH.")

from pyrogram import Client, filters

# --- Configuration ---
DOWNLOAD_DIR = "downloads"
MAX_CONCURRENT_TASKS = 5
CHUNK_SIZE = 1024 * 1024  # 1MB Chunks
EDIT_SLEEP = 4            # Anti-Flood (Update progress every 4s)
ADMINS = {841851780}      # Replace with your ID

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# --- Utilities ---
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
    if not total: return "□" * 10
    percentage = current / total
    finished_len = int(percentage * 10)
    return f"{'■' * finished_len}{'□' * (10 - finished_len)}"

async def get_filename_from_headers(response, url):
    """Smart Filename Detection."""
    try:
        cd = response.headers.get("Content-Disposition")
        if cd:
            fname = re.findall("filename=(.+)", cd)
            if fname: return unquote(fname[0].strip('";'))
    except: pass
    try:
        path = unquote(url.split("?")[0])
        name = path.split("/")[-1]
        if name: return name
    except: pass
    return f"QuantumDL_{int(time.time())}"

# --- Metadata & Ffmpeg Engines ---
async def get_video_attributes(file_path):
    """
    Scans video to get exact Width/Height/Duration.
    Essential for fixing Telegram 'Square Video' bug.
    """
    width, height, duration = 1280, 720, 0
    try:
        # Uses ffprobe (provided by static-ffmpeg)
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration",
            "-of", "json",
            file_path
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()
        data = json.loads(stdout)
        
        width = int(data['streams'][0]['width'])
        height = int(data['streams'][0]['height'])
        try:
            duration = int(float(data['streams'][0]['duration']))
        except: duration = 0
    except Exception as e:
        print(f"Metadata Error: {e}")
    return width, height, duration

async def generate_thumbnail(video_path):
    thumb_path = f"{video_path}.jpg"
    try:
        # Extract frame at 00:00:02
        cmd = ["ffmpeg", "-i", video_path, "-ss", "00:00:02", "-vframes", "1", thumb_path, "-y"]
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
        )
        await process.wait()
        if os.path.exists(thumb_path): return thumb_path
    except: pass
    return None

# --- Task Manager ---
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
            "process": None, 
            "last_edit": 0
        }

        msg = await message.reply(f"**__😎 Task Added to Queue...__**\n🖇️ __{url}__", quote=True)
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
            
            task["start_time"] = time.time()
            file_path = None
            
            try:
                # --- 1. Download Phase ---
                is_stream = any(x in url.lower() for x in [".m3u8", ".m3u", ".mpd"])
                
                if is_stream:
                    file_path = await self.download_stream(task, url)
                else:
                    file_path = await self.download_direct(task, url)

                if not file_path: raise Exception("Download failed.")

                # --- 2. Metadata Phase (Ratio) ---
                task["status"] = "checking"
                await msg.edit("**__📏 Checking Dimensions...__**")
                
                w, h, dur = 0, 0, 0
                is_video = False
                
                # Check Magic Numbers (Real File Type)
                kind = filetype.guess(file_path)
                if kind and kind.mime.startswith("video"): is_video = True
                elif file_path.endswith(".mp4") or file_path.endswith(".mkv"): is_video = True
                
                if is_video:
                    w, h, dur = await get_video_attributes(file_path)

                # --- 3. Upload Phase ---
                await self.upload_file(client, task, file_path, w, h, dur, is_video)

            except Exception as e:
                await msg.edit(f"**__❌ Error:__** `{str(e)}`")
            finally:
                # Cleanup
                if file_path and os.path.exists(file_path): os.remove(file_path)
                if file_path:
                    t = f"{file_path}.jpg"
                    if os.path.exists(t): os.remove(t)
                self.active_tasks.pop(task_id, None)

    # --- Engine A: Direct (Aiohttp) ---
    async def download_direct(self, task, url):
        task["status"] = "downloading"
        msg = task["message"]
        
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        async with aiohttp.ClientSession() as session:
            async with session.get(url, ssl=ssl_ctx) as response:
                if response.status != 200: raise Exception(f"HTTP {response.status}")

                fname = await get_filename_from_headers(response, url)
                if "." not in fname: fname += ".dat"
                task["filename"] = fname
                
                file_path = os.path.join(DOWNLOAD_DIR, fname)
                total_size = int(response.headers.get("Content-Length", 0))
                downloaded = 0
                
                with open(file_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(CHUNK_SIZE):
                        if task["cancel_event"].is_set(): raise Exception("Cancelled")
                        f.write(chunk)
                        downloaded += len(chunk)
                        await self.update_progress(msg, task, downloaded, total_size, "📥 Downloading")

        # --- Smart Extension Renaming ---
        kind = filetype.guess(file_path)
        if kind:
            curr_ext = os.path.splitext(file_path)[1].lower()
            detected_ext = f".{kind.extension}"

            # If detected is .zip but file is .apk, .docx, or .jar -> Trust the original
            valid_zips = [".apk", ".docx", ".jar", ".xlsx", ".pptx", ".odt"]
            
            if detected_ext == ".zip" and curr_ext in valid_zips:
                pass 
            # If extensions don't match, rename it
            elif curr_ext != detected_ext:
                new_fname = f"{os.path.splitext(task['filename'])[0]}{detected_ext}"
                new_path = os.path.join(DOWNLOAD_DIR, new_fname)
                os.rename(file_path, new_path)
                file_path = new_path
                task["filename"] = new_fname
                
        return file_path

    # --- Engine B: Stream (Ffmpeg) ---
    async def download_stream(self, task, url):
        task["status"] = "recording"
        msg = task["message"]
        
        fname = f"Stream_{int(time.time())}.mp4"
        task["filename"] = fname
        file_path = os.path.join(DOWNLOAD_DIR, fname)
        
        await msg.edit("**__🔄 Recording Stream...__**")
        
        # -c copy = Lossless Download (No Re-encoding)
        cmd = ["ffmpeg", "-i", url, "-c", "copy", "-bsf:a", "aac_adtstoasc", "-y", file_path]
        
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        task["process"] = process

        while True:
            if task["cancel_event"].is_set():
                process.kill()
                raise Exception("Cancelled")
            
            line = await process.stderr.readline()
            if not line: break
            
            # --- "Recorded Size" ---
            if os.path.exists(file_path):
                current_size = os.path.getsize(file_path)
                await self.update_progress(msg, task, current_size, 0, "🔴 Recording Stream")

        await process.wait()
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0: return file_path
        raise Exception("Stream download failed or empty.")

    async def upload_file(self, client, task, file_path, width, height, duration, is_video):
        msg = task["message"]
        task["status"] = "uploading"
        
        thumb = None
        if is_video:
            await msg.edit("**__🖼️ Generating Thumbnail...__**")
            thumb = await generate_thumbnail(file_path)

        async def upload_progress(current, total):
            if task["cancel_event"].is_set(): client.stop_transmission()
            await self.update_progress(msg, task, current, total, "🚀 Uploading")

        await msg.edit(f"**__📤 Uploading...__**\n**{width}x{height}**")
        
        caption = f"**__🛃 {task['filename']}__**\n**__📦 Size :** {human_readable(os.path.getsize(file_path))}__"
        
        try:
            if is_video and width and height:
                # Send Video With Explicit Dimensions
                await client.send_video(
                    task["chat_id"], 
                    video=file_path, 
                    caption=caption,
                    thumb=thumb, 
                    duration=duration,
                    width=width,
                    height=height,
                    supports_streaming=True, 
                    progress=upload_progress
                )
            else:
                # Fallback / Non-Video
                await client.send_document(
                    task["chat_id"], 
                    document=file_path, 
                    caption=caption,
                    thumb=thumb, 
                    progress=upload_progress
                )
            await msg.edit(f"**__✅ Completed !__**\n🛂 __{task['filename']}__")
        except Exception:
            # Fallback if send_video crashes
            try:
                await client.send_document(
                    task["chat_id"], document=file_path, caption=caption, progress=upload_progress
                )
                await msg.edit("**__✅ Completed (Fallback) !__**")
            except:
                await msg.edit("**__❌ Upload Failed.__**")

    async def update_progress(self, message, task, current, total, stage):
        now = time.time()
        # --- FloodWait Logic ---
        if (now - task["last_edit"] < EDIT_SLEEP) and (current < total if total else True): return
        
        task["last_edit"] = now
        elapsed = now - task["start_time"]
        speed = current / elapsed if elapsed > 0 else 0
        percent = (current / total * 100) if total else 0
        eta = (total - current) / speed if speed > 0 and total else 0
        
        if total == 0:
            prog_bar = " __Recording Live...__ "
            size_str = f"**__📦 Recorded : {human_readable(current)}__**"
            eta_str = "**__Live__**"
        else:
            prog_bar = f"[{get_progressbar(current, total)}] __{percent:.1f}%__"
            size_str = f"**__📦 Size : {human_readable(current)} / {human_readable(total)}__**"
            eta_str = time_formatter(eta)

        text = (
            f"**__{stage}__**\n"
            f"**__🛂 File :__** __{task.get('filename', 'Unknown')}__\n"
            f"**{prog_bar}**\n\n"
            f"{size_str}\n"
            f"**__⚡ Speed : {human_readable(speed)}/s__**\n"
            f"**__⏳ ETA : {eta_str}__**\n\n"
            f"**__❌ Cancel :** /cancel_{task['id']}__"
        )
        try: await message.edit(text)
        except: pass

    async def cancel_task(self, task_id):
        if task_id in self.active_tasks:
            self.active_tasks[task_id]["cancel_event"].set()
            proc = self.active_tasks[task_id].get("process")
            if proc:
                try: proc.kill()
                except: pass
            return True
        return False

manager = TaskManager()

# --- Commands ---
@Client.on_message(filters.command(["dl", "leech"]) & filters.private)
async def dl_handler(client, message):
    if len(message.command) < 2:
        return await message.reply("**⁉️ __Usage :__** /dl url")
    url = message.command[1]
    await manager.add_task(client, message, url)

@Client.on_message(filters.regex(r"^/cancel_") & filters.private)
async def cancel_handler(client, message):
    task_id = message.text.split("_")[1]
    if await manager.cancel_task(task_id):
        await message.reply(f"**__🥲 Task Cancelled.__**")
    else:
        await message.reply("**💢 __Task Not Active.__**")
