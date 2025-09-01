import os
import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from youtubesearchpython import VideosSearch

# -------------------
# Command: /song <query>
# -------------------
@Client.on_message(filters.private & filters.command("song"))
async def song_search(client, message):
    if len(message.command) < 2:
        return await message.reply("⚠️ Usage: `/song <song name>`", quote=True)

    query = " ".join(message.command[1:])
    m = await message.reply_text(f"🔎 Searching for **{query}** ...", quote=True)

    try:
        search = VideosSearch(query, limit=5)
        results = search.result()["result"]
    except Exception as e:
        return await m.edit(f"❌ Search failed: {e}")

    if not results:
        return await m.edit("❌ No results found.")

    buttons = []
    text = f"🎶 Results for **{query}**:\n\n"

    for i, v in enumerate(results, start=1):
        title = v["title"]
        duration = v.get("duration", "N/A")
        link = v["link"]
        text += f"{i}. {title} ({duration})\n"
        buttons.append(
            [InlineKeyboardButton(f"{i}. {title[:25]}", callback_data=f"songdl|{link}")]
        )

    await m.edit(text, reply_markup=InlineKeyboardMarkup(buttons))


# -------------------
# Callback: Download song
# -------------------
@Client.on_callback_query(filters.regex(r"^songdl\|"))
async def song_download(client, callback_query: CallbackQuery):
    link = callback_query.data.split("|", 1)[1]

    # delete search results to keep chat clean
    try:
        await callback_query.message.delete()
    except:
        pass

    msg = await callback_query.message.reply_text("🎧 Downloading audio...")

    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": "%(id)s.%(ext)s",
            "quiet": True,
            "noplaylist": True,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            file_name = ydl.prepare_filename(info).rsplit(".", 1)[0] + ".mp3"

        title = info.get("title", "Song")
        await client.send_audio(
            chat_id=callback_query.message.chat.id,
            audio=file_name,
            title=title,
            performer=info.get("uploader", "Unknown"),
            duration=info.get("duration"),
        )

        os.remove(file_name)
        await msg.delete()

    except Exception as e:
        await msg.edit(f"❌ Failed to download: {e}")
