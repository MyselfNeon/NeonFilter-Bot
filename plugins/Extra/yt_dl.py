import os
import asyncio
from pyrogram import filters, Client
from pyrogram.types import Message
from yt_dlp import YoutubeDL
from info import CHNL_LNK 

def run_sync_download(query, type="audio"):
    """
    Runs the download synchronously for the executor.
    Uses 'android' client spoofing to bypass bot detection without cookies.
    """
    
    # Common options to bypass limits
    common_opts = {
        "quiet": True,
        "noplaylist": True,
        "source_address": "0.0.0.0", # Force IPv4 to avoid IPv6 blocks
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios"] # Spoof Android/iOS client
            }
        },
        "geo_bypass": True,
        "nocheckcertificate": True,
    }

    if type == "audio":
        opts = {
            **common_opts,
            "format": "bestaudio/best",
            "outtmpl": "%(id)s.%(ext)s",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        }
    else: # Video
        opts = {
            **common_opts,
            "format": "bestvideo+bestaudio/best",
            "outtmpl": "%(id)s.%(ext)s",
        }

    with YoutubeDL(opts) as ydl:
        try:
            # Search and get info for the first result
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)
            
            if 'entries' in info:
                info = info['entries'][0]
            
            # Prepare filename
            original_filename = ydl.prepare_filename(info)
            ydl.download([info['webpage_url']])
            
            final_filename = original_filename
            
            if type == "audio":
                base = os.path.splitext(original_filename)[0]
                possible_mp3 = f"{base}.mp3"
                if os.path.exists(possible_mp3):
                    final_filename = possible_mp3
            
            return final_filename, info
            
        except Exception as e:
            print(f"[Download Error] {e}")
            return None, None


@Client.on_message(filters.command(['song', 'mp3']) & filters.private)
async def song(client, message):
    query = " ".join(message.command[1:])
    
    if not query:
        return await message.reply("Please provide a song name.\n**Example:** `/song Believer`")

    m = await message.reply(f"**__Searching & Downloading:__** `{query}`...")
    
    try:
        # Run blocking download in background thread
        loop = asyncio.get_event_loop()
        file_path, info = await loop.run_in_executor(None, run_sync_download, query, "audio")

        if not file_path or not os.path.exists(file_path):
            return await m.edit("__Failed to find or download the song. Try a different name.__")

        await m.edit("**__Uploading...__ 📤**")
        
        duration = int(info.get('duration', 0))
        title = info.get('title', 'Unknown')
        performer = info.get('uploader', 'Unknown')
        link = info.get('webpage_url')
        caption = f"**Title:** [{title}]({link})\n**Duration:** {info.get('duration_string')}\n**By:** [UPDATE]({CHNL_LNK})"

        await message.reply_audio(
            audio=file_path,
            caption=caption,
            title=title,
            performer=performer,
            duration=duration
        )
        await m.delete()
        
        # Cleanup
        if os.path.exists(file_path):
            os.remove(file_path)
            
    except Exception as e:
        await m.edit(f"**Error:** `{e}`")
        if 'file_path' in locals() and file_path and os.path.exists(file_path):
            os.remove(file_path)


@Client.on_message(filters.command(["video", "mp4"]))
async def vsong(client, message):
    query = " ".join(message.command[1:])
    
    if not query:
        return await message.reply("Please provide a video name.\n**Example:** `/video Nature 4k`")

    m = await message.reply(f"**__Finding Video:__** `{query}`...")

    try:
        loop = asyncio.get_event_loop()
        file_path, info = await loop.run_in_executor(None, run_sync_download, query, "video")

        if not file_path or not os.path.exists(file_path):
            return await m.edit("__Failed to find or download the video.__")

        await m.edit("**__Uploading Video...__ 📤**")
        
        title = info.get('title', 'Unknown')
        link = info.get('webpage_url')
        caption = f"**Title:** [{title}]({link})\n**Requested By:** {message.from_user.mention}"

        await message.reply_video(
            video=file_path,
            caption=caption,
            duration=int(info.get('duration', 0)),
            supports_streaming=True
        )
        await m.delete()

        # Cleanup
        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:
        await m.edit(f"**Error:** `{e}`")
        if 'file_path' in locals() and file_path and os.path.exists(file_path):
            os.remove(file_path)
            
