from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import asyncio
import os
from info import YOUTUBE_COOKIES


# Helper: create cookies.txt from info.py
async def create_cookie_file():
    path = "cookies.txt"
    with open(path, "w") as f:
        f.write(YOUTUBE_COOKIES)
    return path


# Step 1: User sends /download <url>
@Client.on_message(filters.command("download") & filters.private)
async def choose_download_type(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("⚠️ Please provide a YouTube link.\n\nExample: `/download https://youtu.be/abc123`")

    url = message.command[1]

    # Ask user what they want
    keyboard = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("🎬 Video", callback_data=f"download_video|{url}"),
            InlineKeyboardButton("🎵 Audio", callback_data=f"download_audio|{url}")
        ]]
    )

    await message.reply_text("What do you want to download?", reply_markup=keyboard)


# Step 2: Handle button press
@Client.on_callback_query(filters.regex("^download_"))
async def handle_download_callback(client: Client, callback_query: CallbackQuery):
    action, url = callback_query.data.split("|", 1)
    m = await callback_query.message.edit_text("🔄 Processing... Please wait")

    # Always create cookies file
    cookie_file = await create_cookie_file()

    if action == "download_video":
        output = "%(title)s.%(ext)s"
        cmd = f'yt-dlp --cookies "{cookie_file}" -o "{output}" {url}'
        filetypes = (".mp4", ".mkv", ".webm")
        caption = "✅ Here’s your video!"
        send_func = callback_query.message.reply_video

    else:  # download_audio
        output = "%(title)s.%(ext)s"
        cmd = f'yt-dlp --cookies "{cookie_file}" -x --audio-format mp3 -o "{output}" {url}'
        filetypes = (".mp3", ".m4a", ".opus")
        caption = "🎵 Here’s your music!"
        send_func = callback_query.message.reply_audio

    try:
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_text = stderr.decode() or stdout.decode()
            await m.edit_text(f"❌ Download Failed!\n\n`{error_text[:3500]}`")
            return

        # Find file
        filename = None
        for file in os.listdir():
            if file.endswith(filetypes):
                filename = file
                break

        if not filename:
            await m.edit_text("❌ Couldn’t find the downloaded file.")
            return

        await m.edit_text("⬆️ Uploading to Telegram...")

        await send_func(filename, caption=caption)
        await m.delete()

        os.remove(filename)

    except Exception as e:
        await m.edit_text(f"⚠️ Error: `{e}`")
