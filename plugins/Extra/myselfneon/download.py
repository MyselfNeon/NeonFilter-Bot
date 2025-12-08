import os
import time
import uuid
import asyncio
import json
import shutil
from pyrogram import Client, filters

# Try to import yt_dlp
try:
    import yt_dlp
except ImportError:
    print("CRITICAL: yt-dlp is not installed. Run 'pip install yt-dlp'")

# ================= CONFIGURATION =================
DOWNLOAD_DIR = "downloads"
MAX_CONCURRENT_TASKS = 5
EDIT_SLEEP = 4

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

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

# ================= METADATA ENGINE (THE FIX) =================

async def get_video_attributes(file_path):
    """
    Uses FFprobe to get the EXACT width, height, and duration.
    This fixes the 'random ratio' issue in Telegram.
    """
    width = 1280
    height = 720
    duration = 0
    
    try:
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
        duration = int(float(data['streams'][0]['duration']))
    except Exception as e:
        print(f"Metadata Error: {e}")
        
    return width, height, duration

async def generate_thumbnail(video_path, duration):
    """Generates a thumbnail from the middle of the video."""
    thumb_path = f"{video_path}.jpg"
    timestamp = duration // 2 if duration > 0 else 2
    try:
        cmd = [
            "ffmpeg", "-i", video_path, "-ss", str(timestamp), 
            "-vframes", "1", thumb_path, "-y"
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
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
            "cancel_event": False, # yt-dlp uses a boolean flag usually
            "message": None,
            "start_time": 0,
            "filename": "Unknown",
            "last_edit": 0
        }

        msg = await message.reply(f"**⚡ Initializing...**\n`{url}`", quote=True)
        self.active_tasks[task_id]["message"] = msg
        asyncio.create_task(self.execute_task(client, task_id))

    async def execute_task(self, client, task_id):
        task = self.active_tasks.get(task_id)
        if not task: return

        url = task["url"]
        msg = task["message"]
        semaphore = self.get_semaphore(task["user_id"])
        
        async with semaphore:
            if task["cancel_event"]: return
            
            task["start_time"] = time.time()
            task["status"] = "downloading"
            
            file_path = None
            
            try:
                # --- 1. DOWNLOAD WITH YT-DLP ---
                # This automatically handles generic links, Youtube, Insta, M3U8
                # and selects BEST quality.
                file_path = await self.download_ytdlp(task, url)

                if not file_path:
                    raise Exception("Download failed or cancelled.")

                # --- 2. EXTRACT PRECISE METADATA ---
                task["status"] = "probing"
                await msg.edit("**📏 Checking Dimensions...**")
                width, height, duration = await get_video_attributes(file_path)

                # --- 3. UPLOAD ---
                await self.upload_file(client, task, file_path, width, height, duration)

            except Exception as e:
                await msg.edit(f"**❌ Error:** `{str(e)}`")
            finally:
                if file_path and os.path.exists(file_path): os.remove(file_path)
                # Cleanup thumb if exists
                if file_path:
                    t = f"{file_path}.jpg"
                    if os.path.exists(t): os.remove(t)
                self.active_tasks.pop(task_id, None)

    async def download_ytdlp(self, task, url):
        msg = task["message"]
        loop = asyncio.get_event_loop()
        
        # Unique temp filename
        out_tmpl = f"{DOWNLOAD_DIR}/{task['id']}_%(title)s.%(ext)s"

        def progress_hook(d):
            if d['status'] == 'downloading':
                # Map yt-dlp progress to our bot
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                downloaded = d.get('downloaded_bytes', 0)
                
                # Check cancellation
                if task["cancel_event"]:
                    raise Exception("Cancelled")

                # Update UI
                asyncio.run_coroutine_threadsafe(
                    self.update_progress(msg, task, downloaded, total, "📥 Downloading (yt-dlp)"),
                    loop
                )
            elif d['status'] == 'finished':
                task["filename"] = os.path.basename(d['filename'])

        ydl_opts = {
            'outtmpl': out_tmpl,
            'format': 'bestvideo+bestaudio/best', # <--- ENSURES MAX QUALITY
            'merge_output_format': 'mp4',        # <--- ENSURES COMPATIBILITY
            'noplaylist': True,
            'progress_hooks': [progress_hook],
            'quiet': True,
            'no_warnings': True,
            'geo_bypass': True,
            # Instagram/Cookies support can be added here
        }

        # Run yt-dlp in a separate thread to not block async loop
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
                # If extract_info returns info dict, getting filename is safer:
                if 'requested_downloads' in info:
                    return info['requested_downloads'][0]['filepath']
                else:
                    return ydl.prepare_filename(info)
        except Exception as e:
            if "Cancelled" in str(e): return None
            raise e

    async def upload_file(self, client, task, file_path, width, height, duration):
        msg = task["message"]
        task["status"] = "uploading"
        
        await msg.edit("**🖼️ Generating Thumbnail...**")
        thumb = await generate_thumbnail(file_path, duration)

        async def upload_progress(current, total):
            if task["cancel_event"]: client.stop_transmission()
            await self.update_progress(msg, task, current, total, "🚀 Uploading")

        await msg.edit(f"**📤 Uploading...**\n`{width}x{height}`")
        
        file_size = os.path.getsize(file_path)
        caption = (
            f"**🎬 Name:** `{task['filename']}`\n"
            f"**📏 Res:** `{width}x{height}`\n"
            f"**📦 Size:** `{human_readable(file_size)}`"
        )
        
        try:
            # SEND VIDEO with EXPLICIT WIDTH/HEIGHT
            # This fixes the ratio/aspect issue in Telegram
            await client.send_video(
                task["chat_id"],
                video=file_path,
                caption=caption,
                duration=duration,
                width=width,     # <--- KEY FIX
                height=height,   # <--- KEY FIX
                thumb=thumb,
                supports_streaming=True,
                progress=upload_progress
            )
            await msg.edit(f"**✅ Completed!**\n`{task['filename']}`")
        except Exception as e:
            # Fallback
            await client.send_document(
                task["chat_id"],
                document=file_path,
                caption=caption,
                thumb=thumb,
                progress=upload_progress
            )
            await msg.edit("**✅ Completed (as File)!**")

    async def update_progress(self, message, task, current, total, stage):
        now = time.time()
        if (now - task["last_edit"] < EDIT_SLEEP) and (current < total if total else True): return
        
        task["last_edit"] = now
        elapsed = now - task["start_time"]
        speed = current / elapsed if elapsed > 0 else 0
        percent = (current / total * 100) if total else 0
        
        # Safe ETA calculation
        if speed > 0 and total > 0:
            eta = (total - current) / speed
        else:
            eta = 0

        text = (
            f"**{stage}**\n"
            f"**File:** `{task.get('filename', 'Processing...')}`\n"
            f"**{get_progressbar(current, total)}** `{percent:.1f}%`\n\n"
            f"**💾 Size:** `{human_readable(current)} / {human_readable(total)}`\n"
            f"**⚡ Speed:** `{human_readable(speed)}/s`\n"
            f"**⏳ ETA:** `{time_formatter(eta)}`\n\n"
            f"**🚫 Cancel:** `/cancel_{task['id']}`"
        )
        try: await message.edit(text)
        except: pass

    async def cancel_task(self, task_id):
        if task_id in self.active_tasks:
            self.active_tasks[task_id]["cancel_event"] = True
            return True
        return False

manager = TaskManager()

# ================= COMMANDS =================

@Client.on_message(filters.command(["dl", "leech"]) & filters.private)
async def dl_handler(client, message):
    if len(message.command) < 2:
        return await message.reply("**⚠️ Usage:** `/dl url`")
    
    url = message.command[1]
    await manager.add_task(client, message, url)

@Client.on_message(filters.regex(r"^/cancel_") & filters.private)
async def cancel_handler(client, message):
    task_id = message.text.split("_")[1]
    if await manager.cancel_task(task_id):
        await message.reply(f"**🛑 Task Cancelled.**")
    else:
        await message.reply("**❌ Task not active.**")
