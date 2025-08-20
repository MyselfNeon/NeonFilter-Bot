from pyrogram import Client, filters, types
import yt_dlp
import os, json

# Path to cache file
CACHE_FILE = "song_cache.json"

# Load cache if exists
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r") as f:
        song_cache = json.load(f)
else:
    song_cache = {}

# --- SONG SEARCH ---
@Client.on_message(filters.command("song"))
async def song_search(client, message):
    query = " ".join(message.command[1:])
    if not query:
        return await message.reply("❌ Usage: /song <song name>")

    # Check if cached
    if query.lower() in song_cache:
        song_path = song_cache[query.lower()]
        if os.path.exists(song_path):
            return await message.reply_audio(audio=song_path)
        else:
            del song_cache[query.lower()]  # remove broken entry

    await message.reply("🔎 Searching...")

    try:
        opts = {"quiet": True, "skip_download": True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"ytsearch5:{query}", download=False)["entries"]

        # Build buttons for top 5 results
        buttons = []
        for i, entry in enumerate(info, start=1):
            buttons.append([types.InlineKeyboardButton(
                f"{i}. {entry['title']} ({entry['duration']}s)",
                callback_data=f"download|{entry['id']}|{query.lower()}"
            )])

        await message.reply_text(
            f"🎶 Results for **{query}**:",
            reply_markup=types.InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        await message.reply(f"⚠️ Error: {e}")


# --- SONG DOWNLOAD ---
@Client.on_callback_query(filters.regex(r"download\|(.*)\|(.*)"))
async def song_download(client, callback_query):
    video_id, query = callback_query.data.split("|")[1:3]
    url = f"https://youtube.com/watch?v={video_id}"

    await callback_query.message.edit_text("⏳ Downloading...")

    try:
        opts = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "outtmpl": "%(title)s.%(ext)s",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            }],
        }

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            song_path = ydl.prepare_filename(info).rsplit(".", 1)[0] + ".mp3"

        # Save in cache
        song_cache[query] = song_path
        with open(CACHE_FILE, "w") as f:
            json.dump(song_cache, f)

        await callback_query.message.reply_audio(
            audio=song_path,
            title=info.get("title"),
            performer=info.get("uploader"),
            duration=int(info.get("duration", 0))
        )

        await callback_query.message.delete()

    except Exception as e:
        await callback_query.message.edit_text(f"⚠️ Error: {e}")


# --- CLEAR CACHE ---
@Client.on_message(filters.command("clearcache") & filters.user([123456789]))  # Replace with your Telegram ID
async def clear_cache(client, message):
    global song_cache
    song_cache = {}
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
    await message.reply("🗑 Cache cleared successfully!")
