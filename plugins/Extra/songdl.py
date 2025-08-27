import os
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Temporary cache for search results (chat_id → results)
SEARCH_CACHE = {}

# -----------------------------
# SEARCH & SHOW RESULTS
# -----------------------------
@Client.on_message(filters.command("song") & filters.private)
async def saavn_search(client, message):
    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: `/song <name>`")

    query = " ".join(message.command[1:])
    m = await message.reply_text(f"🔎 Searching **{query}** ...")

    try:
        url = f"https://saavn.dev/api/search/songs?query={query}"
        data = requests.get(url).json()

        results = data["data"]["results"][:5]  # take top 5
        if not results:
            return await m.edit("❌ No results found!")

        # Save results in cache
        SEARCH_CACHE[message.chat.id] = results

        buttons = []
        for i, song in enumerate(results, start=1):
            title = song["name"]
            artist = ", ".join([a["name"] for a in song["artists"]["primary"]])
            buttons.append([
                InlineKeyboardButton(f"{i}. {title} - {artist}", callback_data=f"song_{i}")
            ])

        await m.edit(
            f"🎶 Top results for **{query}**:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        await m.edit(f"⚠ Error: {e}")


# -----------------------------
# HANDLE BUTTON & DOWNLOAD
# -----------------------------
@Client.on_callback_query(filters.regex(r"^song_"))
async def saavn_download(client, callback: CallbackQuery):
    chat_id = callback.message.chat.id
    if chat_id not in SEARCH_CACHE:
        return await callback.answer("❌ Old search expired, please search again!", show_alert=True)

    index = int(callback.data.split("_")[1]) - 1
    results = SEARCH_CACHE[chat_id]

    if index >= len(results):
        return await callback.answer("❌ Invalid choice.", show_alert=True)

    song = results[index]
    m = await callback.message.edit("⬇ Downloading song...")

    try:
        # Fetch full song details
        url = f"https://saavn.dev/api/songs/{song['id']}"
        data = requests.get(url).json()

        if "data" not in data or not data["data"]:
            return await m.edit("❌ Failed to fetch song details.")

        song_info = data["data"][0]
        title = song_info["name"]
        artist = ", ".join([a["name"] for a in song_info["artists"]["primary"]])
        mp3_url = song_info["downloadUrl"][-1]["url"]

        file_name = f"{title}.mp3"
        r = requests.get(mp3_url, stream=True)
        with open(file_name, "wb") as f:
            for chunk in r.iter_content(1024):
                f.write(chunk)

        # Send back
        await client.send_audio(
            chat_id=chat_id,
            audio=file_name,
            title=title,
            performer=artist,
            caption=f"🎶 {title}\n👤 {artist}",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅ Back", callback_data="back_to_results")]]
            )
        )

        await m.delete()
        os.remove(file_name)

    except Exception as e:
        await m.edit(f"⚠ Error: {e}")


# -----------------------------
# HANDLE BACK BUTTON
# -----------------------------
@Client.on_callback_query(filters.regex(r"^back_to_results$"))
async def saavn_back(client, callback: CallbackQuery):
    chat_id = callback.message.chat.id
    if chat_id not in SEARCH_CACHE:
        return await callback.answer("❌ Old search expired, please search again!", show_alert=True)

    results = SEARCH_CACHE[chat_id]

    buttons = []
    for i, song in enumerate(results, start=1):
        title = song["name"]
        artist = ", ".join([a["name"] for a in song["artists"]["primary"]])
        buttons.append([
            InlineKeyboardButton(f"{i}. {title} - {artist}", callback_data=f"song_{i}")
        ])

    await callback.message.edit(
        "🎶 Pick a song:",
        reply_markup=InlineKeyboardMarkup(buttons)
                            )
