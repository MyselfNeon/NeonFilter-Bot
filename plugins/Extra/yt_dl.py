import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
from youtubesearchpython import VideosSearch

# -----------------------------
# YT-DLP OPTIONS
# -----------------------------
def audio_opts_factory(bitrate="192"):
    return {
        "format": "bestaudio/best",
        "outtmpl": "%(title)s.%(ext)s",
        "noplaylist": True,
        "quiet": True,
        "geo_bypass": True,
        "nocheckcertificate": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": bitrate,
        }]
    }

def video_opts_factory(resolution="best"):
    return {
        "format": f"bestvideo[height<={resolution}]+bestaudio/best" if resolution != "best" else "bestvideo+bestaudio/best",
        "outtmpl": "%(title)s.%(ext)s",
        "noplaylist": True,
        "quiet": True,
        "geo_bypass": True,
        "nocheckcertificate": True,
        "merge_output_format": "mp4",
    }

# -----------------------------
# YT SEARCH
# -----------------------------
def yt_search(query: str) -> str:
    search = VideosSearch(query, limit=1)
    results = search.result().get("result")
    if not results:
        return None
    return results[0]["link"]

# -----------------------------
# DOWNLOAD WITH PROGRESS
# -----------------------------
async def yt_download(url, opts, message):
    loop = asyncio.get_running_loop()
    progress_msg = await message.reply("⏳ Starting download...")

    def progress_hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 1
            downloaded = d.get('downloaded_bytes', 0)
            percent = int(downloaded * 100 / total)
            loop.create_task(progress_msg.edit(f"⏳ Downloading... {percent}%"))
        elif d['status'] == 'finished':
            loop.create_task(progress_msg.edit("✅ Download finished, uploading..."))

    opts["progress_hooks"] = [progress_hook]

    file_path, info = await loop.run_in_executor(None, lambda: download_sync(url, opts))
    await progress_msg.delete()
    return file_path, info

def download_sync(url, opts):
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info)
        if "postprocessors" in opts and opts["postprocessors"][0]["key"] == "FFmpegExtractAudio":
            if not file_path.endswith(".mp3"):
                file_path = os.path.splitext(file_path)[0] + ".mp3"
        return file_path, info

# -----------------------------
# /song COMMAND
# -----------------------------
@Client.on_message(filters.command(["song", "mp3"]) & filters.private)
async def song_handler(client, message):
    if len(message.command) < 2:
        return await message.reply("**Usage:** `/song <link or search>` 🎵")

    query = message.text.split(maxsplit=1)[1]
    await message.reply(
        "Select audio quality:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("128 kbps", callback_data=f"audio|128|{query}")],
            [InlineKeyboardButton("192 kbps", callback_data=f"audio|192|{query}")],
            [InlineKeyboardButton("320 kbps", callback_data=f"audio|320|{query}")]
        ])
    )

# -----------------------------
# /video COMMAND
# -----------------------------
@Client.on_message(filters.command(["video", "mp4"]) & filters.private)
async def video_handler(client, message):
    if len(message.command) < 2:
        return await message.reply("**Usage:** `/video <link or search>` 🎬")

    query = message.text.split(maxsplit=1)[1]
    await message.reply(
        "Select video quality:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("360p", callback_data=f"video|360|{query}")],
            [InlineKeyboardButton("720p", callback_data=f"video|720|{query}")],
            [InlineKeyboardButton("1080p", callback_data=f"video|1080|{query}")],
            [InlineKeyboardButton("Best", callback_data=f"video|best|{query}")]
        ])
    )

# -----------------------------
# CALLBACK QUERY HANDLER
# -----------------------------
@Client.on_callback_query()
async def callback_query_handler(client: Client, cq: CallbackQuery):
    action, quality, query = cq.data.split("|")

    await cq.answer("Processing your request... ⏳")
    url = query if query.startswith(("http://", "https://")) else yt_search(query)
    if not url:
        return await cq.message.edit("❌ No results found.")

    try:
        if action == "audio":
            opts = audio_opts_factory(quality)
            file_path, info = await yt_download(url, opts, cq.message)
            await client.send_audio(
                chat_id=cq.message.chat.id,
                audio=file_path,
                title=info.get("title"),
                performer=info.get("uploader"),
                duration=int(info.get("duration", 0)),
                caption=f"🎵 **{info.get('title')}**\n👤 {info.get('uploader')}"
            )
        elif action == "video":
            opts = video_opts_factory(quality)
            file_path, info = await yt_download(url, opts, cq.message)
            await client.send_video(
                chat_id=cq.message.chat.id,
                video=file_path,
                caption=f"🎬 **{info.get('title')}**\n👤 {info.get('uploader')}",
                duration=int(info.get("duration", 0)),
                supports_streaming=True
            )
        os.remove(file_path)
        await cq.message.delete()

    except DownloadError as e:
        if "Sign in" in str(e) or "login" in str(e).lower():
            await cq.message.edit(
                "⚠️ This video is age-restricted, private, or requires sign-in and cannot be downloaded."
            )
        else:
            await cq.message.edit(f"❌ Error: `{str(e)}`")

    except Exception as e:
        await cq.message.edit(f"❌ Error: `{str(e)}`")