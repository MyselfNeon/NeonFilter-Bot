from pyrogram import Client, filters, types
import requests
import os

# --- SONG SEARCH ---
@Client.on_message(filters.command("songsp"))
async def songsp_search(client, message):
    query = " ".join(message.command[1:])
    if not query:
        return await message.reply("❌ Usage: /songsp <song name>")

    await message.reply("🔎 Searching JioSaavn...")

    try:
        # call JioSaavn open API
        url = f"https://jiosaavn-api.vercel.app/search/songs?query={query}"
        data = requests.get(url).json()

        if not data or not data.get("data"):
            return await message.reply("🙅 No results found!")

        # take top 5 results
        songs = data["data"][:5]
        buttons = []
        for i, song in enumerate(songs, start=1):
            buttons.append([types.InlineKeyboardButton(
                f"{i}. {song['name']} - {song['primaryArtists']}",
                callback_data=f"jdownload|{song['id']}"
            )])

        await message.reply_text(
            f"🎶 Results for **{query}**:",
            reply_markup=types.InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        await message.reply(f"⚠️ Error: {e}")


# --- SONG DOWNLOAD ---
@Client.on_callback_query(filters.regex(r"jdownload\|(.*)"))
async def songsp_download(client, callback_query):
    song_id = callback_query.data.split("|")[1]
    await callback_query.message.edit_text("⏳ Fetching from JioSaavn...")

    try:
        # fetch song details
        url = f"https://jiosaavn-api.vercel.app/songs?id={song_id}"
        song = requests.get(url).json()

        if not song or not song.get("data"):
            return await callback_query.message.edit_text("❌ Failed to fetch song")

        song = song["data"][0]
        download_url = song["downloadUrl"][-1]["link"]  # highest quality MP3
        title = song["name"]
        artists = song["primaryArtists"]
        duration = int(song.get("duration", 0))

        # download the MP3 file
        file_name = f"{title}.mp3"
        r = requests.get(download_url, stream=True)
        with open(file_name, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)

        # send audio
        await callback_query.message.reply_audio(
            audio=file_name,
            title=title,
            performer=artists,
            duration=duration
        )

        os.remove(file_name)
        await callback_query.message.delete()

    except Exception as e:
        await callback_query.message.edit_text(f"⚠️ Error: {e}")
