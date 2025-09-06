import os import aiohttp import asyncio import math import time import shutil import subprocess from urllib.parse import urlparse, parse_qs from pyrogram import Client, filters from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton import cv2  # For video metadata

---------------- CONFIG -----------------

DOWNLOAD_DIR = "downloads" os.makedirs(DOWNLOAD_DIR, exist_ok=True)

ACTIVE_DOWNLOADS = {}            # {chat_id: count} USER_QUEUE = {}                 # {chat_id: asyncio.Queue} PROGRESS_BAR_LENGTH = 16 MAX_PARALLEL_CHUNKS = 3 MAX_ACTIVE_DOWNLOADS = 10 RETRY_LIMIT = 3 TG_MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB TEMP_SUFFIX = ".part"

VIDEO_EXTENSIONS = { "video/mp4": ".mp4", "video/webm": ".webm", "video/ogg": ".ogv" }

MIME_DEFAULTS = { "application/octet-stream": ".bin", "text/html": ".html", }

-------------- Helpers ------------------

def human_readable(size): power = 2**10 n = 0 Dic_powerN = {0: "B",1:"KB",2:"MB",3:"GB",4:"TB"} while size > power and n < 4: size /= power n +=1 return f"{round(size,2)} {Dic_powerN[n]}"

def progress_bar(done, total, length=16): filled = int(length * done / total) if total else 0 bar = "▰" * filled + "▱" * (length - filled) pct = f"{int(done/total*100) if total else 0}%" return f"{bar} {pct}"

async def update_progress(current, total, message: Message, start, action="Downloading"): now = time.time() elapsed = now - start speed = current / (elapsed+1e-6) eta = int((total-current)/(speed+1e-6)) if total and speed>0 else 0 bar = progress_bar(current, total, length=PROGRESS_BAR_LENGTH) text = ( f"📤 {action}...\n\n" f"{bar}\n" f"{human_readable(current)} / {human_readable(total)}\n" f"⚡ {human_readable(speed)}/s | ⏳ {eta}s" ) try: await message.edit(text) except Exception: pass

def parse_link_options(url: str): """Allow passing options as query params, e.g. ?title=MyVideo&thumb=https://...""" parsed = urlparse(url) qs = parse_qs(parsed.query) opts = {k: v[0] for k, v in qs.items()} # return cleaned url without query clean = parsed._replace(query="").geturl() return clean, opts

--------- Resumable ranged downloader ---------

async def download_range(session, url, start, end, temp_path, idx, progress, chat_id, part_exist_len=0): headers = {"Range": f"bytes={start+part_exist_len}-{end}"} if part_exist_len>0 else {"Range": f"bytes={start}-{end}"} async with session.get(url, headers=headers) as resp: if resp.status not in (200, 206): return False mode = "ab" if part_exist_len>0 else "wb" with open(temp_path, mode) as f: async for chunk in resp.content.iter_chunked(1024*512): if not ACTIVE_DOWNLOADS.get(chat_id, True): return False f.write(chunk) progress[idx] += len(chunk) return True

async def download_file(url: str, temp_base: str, status_msg: Message, chat_id: int): # Queue guard if ACTIVE_DOWNLOADS.get(chat_id,0) >= MAX_ACTIVE_DOWNLOADS: await status_msg.edit("⚠ You reached the maximum 10 simultaneous downloads.") return None ACTIVE_DOWNLOADS[chat_id] = ACTIVE_DOWNLOADS.get(chat_id,0)+1

# parse inline options
url, opts = parse_link_options(url)

async with aiohttp.ClientSession() as session:
    for attempt in range(RETRY_LIMIT):
        try:
            async with session.head(url, allow_redirects=True) as resp_head:
                if resp_head.status not in (200, 206):
                    await status_msg.edit(f"❌ Link returned status {resp_head.status}")
                    ACTIVE_DOWNLOADS[chat_id]-=1
                    return None

                total_size = int(resp_head.headers.get("Content-Length", 0))
                content_type = resp_head.headers.get("Content-Type","").split(';')[0].lower()

                if "mpegurl" in content_type or url.lower().endswith('.m3u'):
                    await status_msg.edit("⚠ M3U/playlist links are not supported! Please send a direct video/file link.")
                    ACTIVE_DOWNLOADS[chat_id]-=1
                    return None

                ext = VIDEO_EXTENSIONS.get(content_type) or MIME_DEFAULTS.get(content_type) or ".mp4"
                file_path = temp_base + ext

                # Prepare part files (support resume)
                chunk_size = max(1, math.ceil(total_size / MAX_PARALLEL_CHUNKS))
                part_paths = [f"{file_path}{TEMP_SUFFIX}{i}" for i in range(MAX_PARALLEL_CHUNKS)]
                progress = [0]*MAX_PARALLEL_CHUNKS

                # If parts exist, read their sizes to resume
                part_exist_lens = []
                for p in part_paths:
                    if os.path.exists(p):
                        part_exist_lens.append(os.path.getsize(p))
                    else:
                        part_exist_lens.append(0)

                start_time = time.time()

                tasks = []
                for i in range(MAX_PARALLEL_CHUNKS):
                    start = i*chunk_size
                    end = min((i+1)*chunk_size-1, total_size-1)
                    tasks.append(download_range(session,url,start,end,part_paths[i],i,progress,chat_id,part_exist_lens[i]))

                async def monitor(task_futures):
                    while True:
                        if not ACTIVE_DOWNLOADS.get(chat_id, True):
                            break
                        done_size = sum(progress) + sum(part_exist_lens)
                        await update_progress(done_size, total_size, status_msg, start_time, "Downloading")
                        if all(t.done() for t in task_futures):
                            break
                        await asyncio.sleep(0.7)

                # Run download
                task_futures = [asyncio.create_task(t) for t in tasks]
                monitor_task = asyncio.create_task(monitor(task_futures))
                await asyncio.gather(*task_futures)
                await monitor_task

                # Merge parts
                merged_size = 0
                with open(file_path, 'ab') as outfile:
                    for i in range(MAX_PARALLEL_CHUNKS):
                        p = part_paths[i]
                        if not os.path.exists(p):
                            # missing part => fail
                            await status_msg.edit("❌ Missing part files, download incomplete. Retry later.")
                            ACTIVE_DOWNLOADS[chat_id]-=1
                            return None
                        with open(p,'rb') as pf:
                            while True:
                                chunk = pf.read(1024*1024)
                                if not chunk: break
                                outfile.write(chunk)
                                merged_size += len(chunk)
                        os.remove(p)
                        await update_progress(merged_size, total_size, status_msg, start_time, "Merging")

                ACTIVE_DOWNLOADS[chat_id]-=1

                # return path and meta
                return file_path, total_size, content_type, opts

        except Exception as e:
            if attempt+1 >= RETRY_LIMIT:
                await status_msg.edit(f"❌ Failed after {RETRY_LIMIT} attempts: {e}")
                ACTIVE_DOWNLOADS[chat_id]-=1
                return None
            await asyncio.sleep(1 + attempt*2)
ACTIVE_DOWNLOADS[chat_id]-=1
return None

---------- Compression if > 2GB (TG limit) ----------

def compress_if_needed(file_path: str): size = os.path.getsize(file_path) if size <= TG_MAX_FILE_SIZE: return file_path

# try to compress with ffmpeg (re-encode to lower bitrate)
base, ext = os.path.splitext(file_path)
compressed = f"{base}_compressed.mp4"
cmd = [
    "ffmpeg", "-y", "-i", file_path,
    "-vcodec", "libx264", "-preset", "fast",
    "-crf", "28", "-acodec", "aac", "-b:a", "128k",
    compressed
]
try:
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(compressed) and os.path.getsize(compressed) < size:
        os.remove(file_path)
        return compressed
except Exception:
    pass
return file_path

---------- Per-user queue worker ----------

async def ensure_user_queue(chat_id: int): if chat_id not in USER_QUEUE: USER_QUEUE[chat_id] = asyncio.Queue() asyncio.create_task(user_queue_worker(chat_id))

async def user_queue_worker(chat_id: int): q = USER_QUEUE[chat_id] while True: item = await q.get() if item is None: break client, url, message = item await process_single_download(client, url, message) q.task_done()

---------- Core processing of a single link ----------

async def process_single_download(client: Client, url: str, message: Message): status = await message.reply_text( "📥 Queued...", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="dlcancel")]]) ) result = await download_file(url, os.path.join(DOWNLOAD_DIR, f"{message.chat.id}_{int(time.time())}"), status, message.chat.id) if not result: try: await status.edit("❌ Failed to download.") except: pass return

file_path, file_size, content_type, opts = result
caption_text = opts.get('title') or f"🎬 **{os.path.basename(file_path)}**\n📦 Size: {human_readable(file_size)}"

# Detect video metadata
width = None
height = None
try:
    cap = cv2.VideoCapture(file_path)
    if cap.isOpened():
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
except:
    pass

if not width or not height:
    width = 1200
    height = 800

# Compress if too big
send_path = compress_if_needed(file_path)

# Send with thumbnail if provided
thumb = opts.get('thumb')
try:
    if content_type.startswith('video'):
        if thumb:
            await message.reply_video(send_path, caption=caption_text, width=width, height=height, thumb=thumb)
        else:
            await message.reply_video(send_path, caption=caption_text, width=width, height=height)
    else:
        await message.reply_document(send_path, caption=caption_text)
except Exception as e:
    # fallback to document
    try:
        await message.reply_document(send_path, caption=caption_text)
    except Exception:
        await status.edit(f"❌ Upload failed: {e}")

# cleanup
try:
    await asyncio.sleep(5)
    await status.delete()
except:
    pass

try:
    os.remove(send_path)
except:
    pass

---------- Cancel ----------

@Client.on_callback_query(filters.regex("dlcancel")) async def cancel_callback(client: Client, query): ACTIVE_DOWNLOADS[query.message.chat.id] = False # clear queue q = USER_QUEUE.get(query.message.chat.id) if q: # remove all queued items while not q.empty(): try: q.get_nowait(); q.task_done() except: break await query.message.edit("❌ Download/upload cancelled.") await query.answer("Cancelled!")

---------- /dl COMMAND (supports multiple links and inline opts) ---------

@Client.on_message(filters.command(["dl", "download"]) & filters.private) async def dl_handler(client: Client, message: Message): if len(message.command) < 2: return await message.reply_text( "⚠ You need to provide one or more links to download!\n\n" "Usage:\n/dl <direct link> [<link2> ...]\n\n" "You can add options to the link as query params, e.g.:\n" "/dl https://example.com/video.mp4?title=MyTitle&thumb=https://i.imgur.com/thumb.jpg" )

links = message.command[1:]
await ensure_user_queue(message.chat.id)
q = USER_QUEUE[message.chat.id]

for url in links:
    # enqueue the job
    await q.put((client, url, message))

await message.reply_text(f"✅ Added {len(links)} link(s) to your queue. Use /dlhelp for options.")

---------- /dlhelp COMMAND ----------

@Client.on_message(filters.command(["dlhelp"]) & filters.private) async def dlhelp_handler(client: Client, message: Message): help_text = ( "📌 DL Bot Commands:\n\n" "1️⃣ /dl <link> - Download a direct video/file link.\n" "   - Supports multiple links: /dl link1 link2 ...\n" "   - Inline options: add ?title=...&thumb=... to the link.\n" "   - Max 3 parallel connections per file.\n" "   - Max 10 active downloads per user.\n\n" "2️⃣ ❌ Cancel Button - Tap the button during download to cancel.\n\n" "⚡ Features added:\n" "- Resume support for interrupted downloads.\n" "- Per-user queueing (one worker per user).\n" "- Auto-compression if file > 2GB (requires ffmpeg).\n" "- Accepts thumbnail & title via query params on the link.\n" "- More robust retry logic and nicer progress bar.\n" "- Fallback to document if video send fails.\n" ) await message.reply_text(help_text)
