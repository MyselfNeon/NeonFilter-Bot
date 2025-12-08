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
EDIT_SLEEP = 4            # Dashboard Refresh Rate (4s)
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
    width, height, duration = 1280, 720, 0
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
        try:
            duration = int(float(data['streams'][0]['duration']))
        except: duration = 0
    except Exception as e:
        print(f"Metadata Error: {e}")
    return width, height, duration

async def generate_thumbnail(video_path):
    thumb_path = f"{video_path}.jpg"
    try:
        cmd = ["ffmpeg", "-i", video_path, "-ss", "00:00:02", "-vframes", "1", thumb_path, "-y"]
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
        )
        await process.wait()
        if os.path.exists(thumb_path): return thumb_path
    except: pass
    return None

# --- Task Manager (Single Dashboard + New Design) ---
class TaskManager:
    def __init__(self):
        self.active_tasks = {}
        self.user_semaphores = {}
        self.user_sessions = {} 

    def get_semaphore(self, user_id):
        if user_id not in self.user_semaphores:
            self.user_semaphores[user_id] = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
        return self.user_semaphores[user_id]

    async def add_task(self, client, message, url):
        task_id = uuid.uuid4().hex[:8]
        user_id = message.from_user.id
        
        # 1. Initialize Task Data
        self.active_tasks[task_id] = {
            "id": task_id,
            "url": url,
            "user_id": user_id,
            "chat_id": message.chat.id,
            "status": "queued",
            "cancel_event": asyncio.Event(),
            "start_time": 0,
            "filename": "Pending...",
            "process": None, 
            "progress_text": "⏳ __Queued...__",
            "finished": False
        }

        # 2. Manage Dashboard Message
        if user_id not in self.user_sessions:
            msg = await message.reply(f"**__🚀 Starting Manager...__**\n🖇️ __{url}__", quote=True)
            self.user_sessions[user_id] = {
                "message": msg,
                "task_ids": [],
                "updater_running": False
            }
        
        self.user_sessions[user_id]["task_ids"].append(task_id)

        # 3. Start Execution
        asyncio.create_task(self.execute_task(client, task_id))
        
        # 4. Start the Dashboard Loop
        if not self.user_sessions[user_id]["updater_running"]:
            asyncio.create_task(self.dashboard_loop(user_id))

    async def dashboard_loop(self, user_id):
        """Refreshes the message with the specific requested design."""
        if user_id not in self.user_sessions: return
        
        self.user_sessions[user_id]["updater_running"] = True
        session = self.user_sessions[user_id]
        message = session["message"]

        while session["task_ids"]:
            text_lines = []
            active_ids = []
            
            # Index counter for "Task : 01", "Task : 02"
            i = 1 
            
            for tid in session["task_ids"]:
                task = self.active_tasks.get(tid)
                if task:
                    # Header: 👀 Task : 01
                    header = f"👀 Task : {i:02d}" 
                    
                    # Combine Header + Body (Body is generated in update_task_status)
                    text_lines.append(f"{header}\n{task['progress_text']}")
                    
                    if not task["finished"]:
                        active_ids.append(tid)
                    
                    i += 1
                else:
                    pass 
            
            session["task_ids"] = active_ids 
            
            # Join tasks with a double newline
            final_text = "\n\n".join(text_lines)
            
            if not active_ids:
                final_text += "\n\n**__✅ All Tasks Completed.__**"
            
            try:
                if final_text != message.text:
                    await message.edit(final_text)
            except Exception as e:
                if "Message to edit not found" in str(e) or "empty" in str(e): break

            if not active_ids: break 
            await asyncio.sleep(EDIT_SLEEP)

        # Cleanup
        self.user_sessions.pop(user_id, None)

    async def execute_task(self, client, task_id):
        task = self.active_tasks.get(task_id)
        if not task: return

        url = task["url"]
        semaphore = self.get_semaphore(task["user_id"])
        
        async with semaphore:
            if task["cancel_event"].is_set(): return
            
            task["start_time"] = time.time()
            file_path = None
            
            try:
                # --- 1. Download ---
                is_stream = any(x in url.lower() for x in [".m3u8", ".m3u", ".mpd"])
                
                if is_stream:
                    file_path = await self.download_stream(task, url)
                else:
                    file_path = await self.download_direct(task, url)

                if not file_path: raise Exception("Download failed.")

                # --- 2. Metadata ---
                task["status"] = "checking"
                # Simple update for status change
                task["progress_text"] = f"📏 Checking Dimensions...\n🛂 File : {task['filename']}"
                
                w, h, dur = 0, 0, 0
                is_video = False
                
                kind = filetype.guess(file_path)
                if kind and kind.mime.startswith("video"): is_video = True
                elif file_path.endswith(".mp4") or file_path.endswith(".mkv"): is_video = True
                
                if is_video:
                    w, h, dur = await get_video_attributes(file_path)

                # --- 3. Upload ---
                await self.upload_file(client, task, file_path, w, h, dur, is_video)
                
                task["progress_text"] = f"✅ Done\n🛂 File : {task['filename']}"

            except Exception as e:
                task["progress_text"] = f"❌ Error\n`{str(e)}`"
            finally:
                task["finished"] = True 
                if file_path and os.path.exists(file_path): os.remove(file_path)
                if file_path:
                    t = f"{file_path}.jpg"
                    if os.path.exists(t): os.remove(t)
                
                await asyncio.sleep(5) 
                self.active_tasks.pop(task_id, None)

    # --- Engine A: Direct ---
    async def download_direct(self, task, url):
        task["status"] = "downloading"
        
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
                        self.update_task_status(task, downloaded, total_size, "📥 Downloading")

        # Smart Extension Renaming
        kind = filetype.guess(file_path)
        if kind:
            curr_ext = os.path.splitext(file_path)[1].lower()
            detected_ext = f".{kind.extension}"
            valid_zips = [".apk", ".docx", ".jar", ".xlsx", ".pptx", ".odt"]
            
            if detected_ext == ".zip" and curr_ext in valid_zips: pass 
            elif curr_ext != detected_ext:
                new_fname = f"{os.path.splitext(task['filename'])[0]}{detected_ext}"
                new_path = os.path.join(DOWNLOAD_DIR, new_fname)
                os.rename(file_path, new_path)
                file_path = new_path
                task["filename"] = new_fname
                
        return file_path

    # --- Engine B: Stream ---
    async def download_stream(self, task, url):
        task["status"] = "recording"
        fname = f"Stream_{int(time.time())}.mp4"
        task["filename"] = fname
        file_path = os.path.join(DOWNLOAD_DIR, fname)
        
        self.update_task_status(task, 0, 0, "🔄 Starting Stream")
        
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
            
            if os.path.exists(file_path):
                current_size = os.path.getsize(file_path)
                self.update_task_status(task, current_size, 0, "🔴 Recording")

        await process.wait()
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0: return file_path
        raise Exception("Stream download failed.")

    async def upload_file(self, client, task, file_path, width, height, duration, is_video):
        task["status"] = "uploading"
        
        thumb = None
        if is_video:
            task["progress_text"] = f"🖼️ Generating Thumbnail...\n🛂 File : {task['filename']}"
            thumb = await generate_thumbnail(file_path)

        async def upload_progress(current, total):
            if task["cancel_event"].is_set(): client.stop_transmission()
            self.update_task_status(task, current, total, "🚀 Uploading")

        # Initial Upload Status
        task["progress_text"] = f"📤 Initializing Upload...\n🛂 File : {task['filename']}"
        
        caption = f"**__🛃 {task['filename']}__**\n**__📦 Size :** {human_readable(os.path.getsize(file_path))}__"
        
        try:
            if is_video and width and height:
                await client.send_video(
                    task["chat_id"], video=file_path, caption=caption, thumb=thumb, 
                    duration=duration, width=width, height=height, supports_streaming=True, 
                    progress=upload_progress
                )
            else:
                await client.send_document(
                    task["chat_id"], document=file_path, caption=caption, thumb=thumb, 
                    progress=upload_progress
                )
        except Exception:
            try:
                await client.send_document(
                    task["chat_id"], document=file_path, caption=caption, progress=upload_progress
                )
            except: pass

    def update_task_status(self, task, current, total, stage):
        """Generates the body text for the dashboard."""
        now = time.time()
        elapsed = now - task["start_time"]
        speed = current / elapsed if elapsed > 0 else 0
        percent = (current / total * 100) if total else 0
        eta = (total - current) / speed if speed > 0 and total else 0
        
        prog_bar = get_progressbar(current, total)
        
        if total == 0:
            # Stream Mode (Undefined Total)
            prog_str = (
                f"{stage}\n"
                f"🛂 File : {task['filename']}\n"
                f"📦 Recorded : {human_readable(current)}\n"
                f"⚡ Speed : {human_readable(speed)}/s\n\n"
                f"❌ Cancel : /cancel_{task['id']}"
            )
        else:
            # Direct Mode (Requested Format)
            prog_str = (
                f"{stage}\n"
                f"🛂 File : {task['filename']}\n"
                f"[{prog_bar}] {percent:.1f}%\n\n"
                f"📦 Size : {human_readable(current)} / {human_readable(total)}\n"
                f"⚡ Speed : {human_readable(speed)}/s\n"
                f"⏳ ETA : {time_formatter(eta)}\n\n"
                f"❌ Cancel : /cancel_{task['id']}"
            )
        
        task["progress_text"] = prog_str

    async def cancel_task(self, task_id):
        if task_id in self.active_tasks:
            self.active_tasks[task_id]["cancel_event"].set()
            self.active_tasks[task_id]["progress_text"] = "❌ Cancelling..."
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
    try:
        task_id = message.text.split("_")[1]
        if await manager.cancel_task(task_id):
            pass 
        else:
            await message.reply("**💢 __Task Not Found or Finished.__**", quote=True)
    except: pass
