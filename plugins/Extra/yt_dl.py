import os
import asyncio
from pyrogram import filters, Client
from yt_dlp import YoutubeDL
from info import CHNL_LNK 

def run_sync_download(query, type="audio"):
    # ... (Same options as before) ...
    common_opts = {
        "quiet": True,
        "noplaylist": True,
        # REMOVED source_address just in case your server uses IPv6
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios"]
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
    else: 
        opts = {
            **common_opts,
            "format": "bestvideo+bestaudio/best",
            "outtmpl": "%(id)s.%(ext)s",
        }

    with YoutubeDL(opts) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)
            if 'entries' in info:
                info = info['entries'][0]
            
            original_filename = ydl.prepare_filename(info)
            ydl.download([info['webpage_url']])
            
            final_filename = original_filename
            if type == "audio":
                base = os.path.splitext(original_filename)[0]
                possible_mp3 = f"{base}.mp3"
                if os.path.exists(possible_mp3):
                    final_filename = possible_mp3
            
            return final_filename, info, None # Success
            
        except Exception as e:
            # RETURN THE ERROR MESSAGE
            return None, None, str(e)


@Client.on_message(filters.command(['song', 'mp3']) & filters.private)
async def song(client, message):
    query = " ".join(message.command[1:])
    m = await message.reply(f"**__Searching:__** `{query}`...")
    
    try:
        loop = asyncio.get_event_loop()
        # Unpack 3 values now (file, info, error)
        file_path, info, error_msg = await loop.run_in_executor(None, run_sync_download, query, "audio")

        if error_msg:
            return await m.edit(f"**Download Failed ❌**\n\n`{error_msg}`")

        if not file_path or not os.path.exists(file_path):
            return await m.edit("__Unknown Error: File not found.__")

        await m.edit("**__Uploading...__ 📤**")
        
        await message.reply_audio(
            audio=file_path,
            caption=f"**Title:** {info.get('title')}",
            title=info.get('title'),
            performer=info.get('uploader'),
            duration=int(info.get('duration', 0))
        )
        await m.delete()
        if os.path.exists(file_path): os.remove(file_path)
            
    except Exception as e:
        await m.edit(f"**Bot Error:** `{e}`")


@Client.on_message(filters.command(["video", "mp4"]))
async def vsong(client, message):
    query = " ".join(message.command[1:])
    m = await message.reply(f"**__Searching:__** `{query}`...")

    try:
        loop = asyncio.get_event_loop()
        file_path, info, error_msg = await loop.run_in_executor(None, run_sync_download, query, "video")

        if error_msg:
            return await m.edit(f"**Download Failed ❌**\n\n`{error_msg}`")

        if not file_path or not os.path.exists(file_path):
            return await m.edit("__Unknown Error: File not found.__")

        await m.edit("**__Uploading...__ 📤**")
        
        await message.reply_video(
            video=file_path,
            caption=f"**Title:** {info.get('title')}",
            duration=int(info.get('duration', 0)),
            supports_streaming=True
        )
        await m.delete()
        if os.path.exists(file_path): os.remove(file_path)

    except Exception as e:
        await m.edit(f"**Bot Error:** `{e}`")
