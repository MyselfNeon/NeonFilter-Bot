import os
import aiohttp
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from youtubesearchpython import VideosSearch
import yt_dlp

# -------------------
# Helper Functions
# -------------------
async def search_saavn(query):
    url = f"https://www.saavn.com/api.php?__call=autocomplete.get&_format=json&p=1&q={query}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                data = await resp.json(content_type=None)
                songs = data.get("songs", {}).get("data", [])
                result = []
                for s in songs[:5]:
                    result.append({
                        "id": s.get("id"),
                        "title": s.get("title"),
                        "singer": s.get("more_info", {}).get("singers", "Unknown")
                    })
                return result
        except:
            return []

async def get_saavn_mp3(song_id):
    url = f"https://www.saavn.com/api.php?_format=json&__call=song.getDetails&p=1&id={song_id}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                data = await resp.json(content_type=None)
                media_url = data.get("song", {}).get("media_url")
                title = data.get("song", {}).get("song", "Unknown")
                artist = data.get("song", {}).get("singers", "Unknown")
                duration = data.get("song", {}).get("duration")
                return media_url, title, artist, duration
        except:
            return None, None, None, None

async def search_piped(query):
    search = VideosSearch(query, limit=5)
    results = search.result().get("result", [])
    return [{"title": v["title"], "link": v["link"]} for v in results[:5]]


# -------------------
# Command: /song <query>
# -------------------
@Client.on_message(filters.private & filters.command("song"))
async def song_search(client, message):
    if len(message.command) < 2:
        return await message.reply("⚠️ Usage: `/song <song name>`", quote=True)

    query = " ".join(message.command[1:])
    m = await message.reply_text(f"🔎 Searching for **{query}** ...", quote=True)

    # Try Saavn first
    saavn_results = await search_saavn(query)
    buttons = []
    text = f"🎶 Results for **{query}**:\n\n"

    if saavn_results:
        for i, s in enumerate(saavn_results, start=1):
            text += f"{i}. {s['title']} - {s['singer']}\n"
            buttons.append([InlineKeyboardButton(f"{i}. {s['title'][:25]}", callback_data=f"saavn|{s['id']}")])
    else:
        # Fallback to Piped (YouTube frontend)
        yt_results = await search_piped(query)
        if not yt_results:
            return await m.edit("❌ No results found on Saavn or YouTube.")

        for i, s in enumerate(yt_results, start=1):
            text += f"{i}. {s['title']}\n"
            buttons.append([InlineKeyboardButton(f"{i}. {s['title'][:25]}", callback_data=f"yt|{s['link']}")])

    await m.edit(text, reply_markup=InlineKeyboardMarkup(buttons))


# -------------------
# Callback: Download song
# -------------------
@Client.on_callback_query(filters.regex(r"^(saavn|yt)\|"))
async def download_song(client, callback_query: CallbackQuery):
    source, data = callback_query.data.split("|", 1)
    try:
        await callback_query.message.delete()
    except:
        pass

    msg = await callback_query.message.reply_text("🎧 Downloading...")

    if source == "saavn":
        media_url, title, artist, duration = await get_saavn_mp3(data)
        if not media_url:
            return await msg.edit("❌ Failed to fetch Saavn song.")

        file_name = f"{data}.mp3"
        async with aiohttp.ClientSession() as session:
            async with session.get(media_url) as r:
                with open(file_name, "wb") as f:
                    f.write(await r.read())

    else:  # YouTube fallback via Piped
        file_name = f"{data.split('=')[-1]}.mp3"
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": file_name,
            "quiet": True,
            "noplaylist": True,
            "postprocessors": [{"key": "FFmpegExtractAudio","preferredcodec": "mp3","preferredquality": "192"}],
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(data, download=True)
            title = file_name
            artist = "YouTube"
            duration = None
        except Exception as e:
            return await msg.edit(f"❌ Failed to download YouTube: {e}")

    await client.send_audio(
        chat_id=callback_query.message.chat.id,
        audio=file_name,
        title=title,
        performer=artist,
        duration=duration
    )
    os.remove(file_name)
    await msg.delete()
