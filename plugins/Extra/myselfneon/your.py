import os
import aiohttp
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# -------------------
# Command: /song <query>
# -------------------
@Client.on_message(filters.private & filters.command("song"))
async def song_search(client, message):
    if len(message.command) < 2:
        return await message.reply("⚠️ Usage: `/song <song name>`", quote=True)

    query = " ".join(message.command[1:])
    m = await message.reply_text(f"🔎 Searching for **{query}** ...", quote=True)

    search_url = f"https://www.jiosaavn.com/api.php?__call=autocomplete.get&_format=json&p=1&q={query}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(search_url) as resp:
                data = await resp.json(content_type=None)
        except Exception as e:
            return await m.edit(f"❌ Search failed: {e}")

    songs = data.get("songs", {}).get("data", [])
    if not songs:
        return await m.edit("❌ No results found.")

    buttons = []
    text = f"🎶 Results for **{query}**:\n\n"

    for i, song in enumerate(songs[:5], start=1):
        title = song.get("title")
        singer = song.get("more_info", {}).get("singers", "Unknown")
        song_id = song.get("id")
        text += f"{i}. {title} - {singer}\n"
        buttons.append([InlineKeyboardButton(f"{i}. {title[:25]}", callback_data=f"jiosong|{song_id}")])

    await m.edit(text, reply_markup=InlineKeyboardMarkup(buttons))


# -------------------
# Callback: Download song
# -------------------
@Client.on_callback_query(filters.regex(r"^jiosong\|"))
async def download_song(client, callback_query: CallbackQuery):
    song_id = callback_query.data.split("|", 1)[1]

    # delete search results to keep chat clean
    try:
        await callback_query.message.delete()
    except:
        pass

    msg = await callback_query.message.reply_text("🎧 Fetching song...")

    song_url = f"https://www.jiosaavn.com/api.php?_format=json&__call=song.getDetails&p=1&id={song_id}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(song_url) as resp:
                song_data = await resp.json(content_type=None)
        except Exception as e:
            return await msg.edit(f"❌ Failed to fetch song details: {e}")

    media_url = song_data.get("song", {}).get("media_url")
    title = song_data.get("song", {}).get("song", "Unknown")
    artist = song_data.get("song", {}).get("singers", "Unknown")
    duration = song_data.get("song", {}).get("duration")

    if not media_url:
        return await msg.edit("❌ Could not get media URL.")

    # download and send
    file_name = f"{song_id}.mp3"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(media_url) as r:
                with open(file_name, "wb") as f:
                    f.write(await r.read())

        await client.send_audio(
            chat_id=callback_query.message.chat.id,
            audio=file_name,
            title=title,
            performer=artist,
            duration=duration
        )
        os.remove(file_name)
        await msg.delete()
    except Exception as e:
        await msg.edit(f"❌ Failed to download/send song: {e}")
