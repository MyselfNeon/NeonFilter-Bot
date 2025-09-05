import os
import aiohttp
import asyncio
import time
import random
import subprocess
from PIL import Image
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# ---------- CONFIG ----------
GENERATE_THUMBNAILS = True  # True to generate collage
NUM_SCREENSHOTS = 10         # Number of random screenshots
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

ACTIVE_DOWNLOADS = {}

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

# ---------- Download ----------
async def download_file(url: str, temp_path: str, chat_id: int):
    async with aiohttp.ClientSession() as session:
        async with session.head(url) as resp_head:
            if resp_head.status != 200: return None
            total_size = int(resp_head.headers.get("Content-Length", 0))
            content_type = resp_head.headers.get("Content-Type","").lower()
            if not ACTIVE_DOWNLOADS.get(chat_id, True): return None

            if any(x in content_type for x in ["application/vnd.apple.mpegurl","vnd.apple.mpegurl"]):
                return await download_m3u8(url,temp_path,chat_id)

            ext = VIDEO_EXTENSIONS.get(content_type,".mp4")
            file_path = temp_path+ext

            async with session.get(url) as resp:
                with open(file_path,"wb") as f:
                    async for chunk in resp.content.iter_chunked(1024*1024*2):
                        if not ACTIVE_DOWNLOADS.get(chat_id, True): return None
                        f.write(chunk)
            return file_path, total_size

async def download_m3u8(url: str, path: str, chat_id: int):
    if not ACTIVE_DOWNLOADS.get(chat_id, True): return None
    cmd = ["ffmpeg","-y","-i",url,"-c","copy","-threads","4","-bsf:a","aac_adtstoasc",path+".mp4"]
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    await proc.communicate()
    size = os.path.getsize(path+".mp4") if os.path.exists(path+".mp4") else 0
    return path+".mp4", size if os.path.exists(path+".mp4") else None

# ---------- Thumbnails ----------
def generate_thumbnail_collage(video_path, num_shots):
    thumbs=[]
    result = subprocess.run(
        ["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",video_path],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    duration = float(result.stdout)
    times = sorted(random.sample(range(int(duration)-1), min(num_shots,int(duration))))

    for i,t in enumerate(times):
        thumb_path=f"{video_path}_thumb{i}.jpg"
        subprocess.run(["ffmpeg","-ss",str(t),"-i",video_path,"-frames:v","1","-q:v","2",thumb_path])
        if os.path.exists(thumb_path): thumbs.append(thumb_path)

    if not thumbs: return None

    imgs = [Image.open(t) for t in thumbs]
    widths, heights = zip(*(i.size for i in imgs))
    total_width = sum(widths)
    max_height = max(heights)
    collage = Image.new("RGB",(total_width,max_height),color=(0,0,0))
    x_offset=0
    for img in imgs:
        collage.paste(img,(x_offset,0))
        x_offset += img.width
        img.close()
    for t in thumbs: os.remove(t)
    collage_path=f"{video_path}_collage.jpg"
    collage.save(collage_path)
    return collage_path

# ---------- Cancel ----------
@Client.on_callback_query(filters.regex("dlcancel"))
async def cancel_callback(client: Client, query: CallbackQuery):
    ACTIVE_DOWNLOADS[query.message.chat.id] = False
    await query.message.edit("❌ Download/upload cancelled.")
    await query.answer("Cancelled!")

# ---------- Main ----------
@Client.on_message(filters.command(["neodl"]) & filters.private)
async def neodl_handler(client: Client, message: Message):
    if len(message.command)<2: 
        return await message.reply_text("⚡ Usage:\n`/neodl <link>`")
    links = message.command[1:]
    ACTIVE_DOWNLOADS[message.chat.id]=True

    for idx,url in enumerate(links,1):
        temp_path = os.path.join(DOWNLOAD_DIR,f"{message.chat.id}_{int(time.time())}_{idx}")
        status = await message.reply_text(
            f"📥 Downloading {idx}/{len(links)}...",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("❌ Cancel",callback_data="dlcancel")]]
            )
        )

        result = await download_file(url,temp_path,message.chat.id)
        if not result:
            await status.edit(f"❌ Failed to download link {idx}")
            continue

        file_path, file_size = result
        caption_text = f"🎬 **{os.path.basename(file_path)}**\n📦 Size: {human_readable(file_size)}"

        try:
            await message.reply_video(file_path, caption=caption_text)
        except:
            await message.reply_document(file_path, caption=caption_text)

        # Thumbnails
        if GENERATE_THUMBNAILS:
            collage=generate_thumbnail_collage(file_path,NUM_SCREENSHOTS)
            if collage and os.path.exists(collage):
                await message.reply_photo(collage, caption="📸 Video preview")
                os.remove(collage)

        os.remove(file_path)
        await status.delete()

    ACTIVE_DOWNLOADS[message.chat.id]=False
    
