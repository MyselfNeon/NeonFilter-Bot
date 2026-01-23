from plugins.Extra.utils import progress_for_pyrogram, convert, humanbytes
from pyrogram import Client, filters
from plugins.Extra.rename.filedetect import refunc
from pyrogram.types import (InlineKeyboardButton, InlineKeyboardMarkup, ForceReply)
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from database.users_chats_db import db
import os 
import humanize
import shutil
import asyncio
from PIL import Image
import time
import logging

logger = logging.getLogger(__name__)
logging.getLogger("pyrogram").setLevel(logging.WARNING)

# --- UPDATED METADATA FUNCTION START ---
async def add_metadata(input_path, output_path, user_id):
    # 1. Check if user has turned Metadata ON
    if not await db.get_metadata_mode(user_id):
        # If OFF, just simple rename and return
        os.rename(input_path, output_path)
        return

    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        os.rename(input_path, output_path)
        return

    # 2. Fetch the Tag
    tag = await db.get_metadata_tag(user_id)
    if not tag:
        tag = "TG: @NeonFiles" # Default fallback
    
    # 3. Apply Metadata
    cmd = [
        ffmpeg,
        '-i', input_path,
        '-metadata', f'title={tag}',
        '-metadata', f'artist={tag}',
        '-metadata', f'author={tag}',
        '-metadata:s:v', f'title={tag}',
        '-metadata:s:a', f'title={tag}',
        '-metadata:s:s', f'title={tag}',
        '-map', '0',
        '-c', 'copy',
        '-loglevel', 'error',
        output_path
    ]
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await process.communicate()
    
    if process.returncode != 0:
        if os.path.exists(output_path):
            os.remove(output_path)
        os.rename(input_path, output_path)
# --- UPDATED METADATA FUNCTION END ---

@Client.on_callback_query(filters.regex('cancel'))
async def cancel(bot, update):
    try:
        await update.message.delete()
    except:
        return

@Client.on_callback_query(filters.regex("upload"))
async def doc(bot, update):
    try:
        type = update.data.split("_")[1]
        new_name = update.message.text
        if ":-" in new_name:
             new_filename = new_name.split(":-")[1].strip()
        else:
             new_filename = new_name.strip()

        file = update.message.reply_to_message
        download_path = f"downloads/{file.file_id}"
        final_path = f"downloads/{new_filename}"
        
        ms = await update.message.edit("__**Please Wait...__ 😇😍**\n\n__**Downloading File to my Servers__  📥**")
        c_time = time.time()
        
        try:
            path = await bot.download_media(
                    message=file,
                    file_name=download_path,
                    progress=progress_for_pyrogram,
                    progress_args=("**__Please Wait... 😇😍 \n\nServers are Renaming the Files you've provided | by @NeonFiles__ 🔥✨**", ms, c_time))
        except Exception as e:
            await ms.edit(e)
            return 

        # Apply Metadata (Logic inside checks for ON/OFF)
        await ms.edit("__**Please Wait...__ 😇😍**\n\n__**Adding Metadata...__  ⚙️**")
        await add_metadata(path, final_path, update.message.chat.id)
        
        if path != final_path and os.path.exists(path):
            os.remove(path)

        file_path = final_path

        duration = 0
        try:
            metadata = extractMetadata(createParser(file_path))
            if metadata.has("duration"):
               duration = metadata.get('duration').seconds
        except:
            pass
            
        user_id = int(update.message.chat.id) 
        ph_path = None 
        media = getattr(file, file.media.value)
        filesize = humanize.naturalsize(media.file_size) 
        c_caption = await db.get_caption(update.message.chat.id)
        c_thumb = await db.get_thumbnail(update.message.chat.id)
        
        if c_caption:
             try:
                 caption = c_caption.format(filename=new_filename, filesize=humanize.naturalsize(media.file_size), duration=convert(duration))
             except Exception as e:
                 await ms.edit(text=f"**__Your caption Error unexpected keyword ●> ({e})__**")
                 return 
        else:
            caption = f"**{new_filename}**"
            
        if (media.thumbs or c_thumb):
            if c_thumb:
               ph_path = await bot.download_media(c_thumb) 
            else:
               ph_path = await bot.download_media(media.thumbs[0].file_id)
            Image.open(ph_path).convert("RGB").save(ph_path)
            img = Image.open(ph_path)
            img.resize((320, 320))
            img.save(ph_path, "JPEG")
            
        await ms.edit("__**Please Wait...__ 😇😍**\n\n**__Processing File Upload__  📤**")
        c_time = time.time() 
        
        try:
           if type == "document":
              await bot.send_document(
                update.message.chat.id,
                    document=file_path,
                    thumb=ph_path, 
                    caption=caption, 
                    progress=progress_for_pyrogram,
                    progress_args=( "__**Please Wait...__ 😇😍**\n\n__**Processing File Upload...__  📤**",  ms, c_time)) 
           elif type == "video": 
               await bot.send_video(
                update.message.chat.id,
                video=file_path,
                caption=caption,
                thumb=ph_path,
                duration=duration,
                progress=progress_for_pyrogram,
                progress_args=( "__**Please Wait...__ 😇😍**\n\n__**Processing File Upload...__  📤**",  ms, c_time)) 
           elif type == "audio": 
               await bot.send_audio(
                update.message.chat.id,
                audio=file_path,
                caption=caption,
                thumb=ph_path,
                duration=duration,
                progress=progress_for_pyrogram,
                progress_args=( "__**Please Wait...__ 😇😍**\n\n__**Processing File Upload...__  📤**",  ms, c_time)) 
        except Exception as e: 
            await ms.edit(f" Error {e}") 
            if os.path.exists(file_path):
                os.remove(file_path)
            if ph_path:
              os.remove(ph_path)
            return 
            
        await ms.delete() 
        if os.path.exists(file_path):
            os.remove(file_path) 
        if ph_path:
           os.remove(ph_path) 
    except Exception as e:
        logger.error(f"error : {e}")