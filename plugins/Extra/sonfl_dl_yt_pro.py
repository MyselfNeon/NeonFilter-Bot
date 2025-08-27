import os
import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message

# Temporary cache for search results (chat_id → search info)
SEARCH_CACHE = {}

# -----------------------------
# /sonfl command -> search YouTube
# -----------------------------
@Client.on_message(filters.command("sonfl") & filters.private)
async def sonfl_search(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: `/sonfl <song name>`")

    query = " ".join(message.command[1:])
    m = await message.reply_text(f"🔎 Searching YouTube for **{query}** ...")

    # Check if cookies file exists
    cookies_path = "cookies.txt"
    if not os.path.exists(cookies_path):
        await m.edit("⚠ Cookies file not found! Please export YouTube cookies to `cookies.txt` in the bot folder.")
        return

    try:
        ydl_opts = {"quiet": True, "noplaylist": True, "extract_flat": True, "cookiefile": cookies_path}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch5:{query}", download=False)

        if "entries" not in info or len(info["entries"]) == 0:
            return await m.edit("❌ No results found!")

        results = info["entries"]
        SEARCH_CACHE[message.chat.id] = results

        buttons = []
        for i, video in enumerate(results, start=1):
            title = video.get("title")
            buttons.append([InlineKeyboardButton(f"{i}. {title}", callback_data=f"sonfl_{i}")])

        await m.edit(
            f"🎶 Top results for **{query}**:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except yt_dlp.utils.DownloadError as e:
        await m.edit(f"⚠ Download error:\n{e}")
    except Exception as e:
        await m.edit(f"⚠ Unexpected error:\n{e}")


# -----------------------------
# Handle inline button -> choose song + quality
# -----------------------------
@Client.on_callback_query(filters.regex(r"^sonfl_\d+$"))
async def sonfl_quality(client: Client, callback: CallbackQuery):
    chat_id = callback.message.chat.id
    if chat_id not in SEARCH_CACHE:
        return await callback.answer("❌ Old search expired, please search again!", show_alert=True)

    index = int(callback.data.split("_")[1]) - 1
    results = SEARCH_CACHE[chat_id]

    if index >= len(results):
        return await callback.answer("❌ Invalid choice.", show_alert=True)

    video = results[index]
    # Ask for quality
    buttons = [
        [InlineKeyboardButton("128 kbps", callback_data=f"download_{index}_128")],
        [InlineKeyboardButton("192 kbps", callback_data=f"download_{index}_192")],
        [InlineKeyboardButton("320 kbps", callback_data=f"download_{index}_320")],
    ]
    await callback.message.edit(
        f"🎵 Selected: {video.get('title')}\nChoose quality:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# -----------------------------
# Handle quality selection -> download + send
# -----------------------------
@Client.on_callback_query(filters.regex(r"^download_\d+_\d+$"))
async def sonfl_download(client: Client, callback: CallbackQuery):
    chat_id = callback.message.chat.id
    if chat_id not in SEARCH_CACHE:
        return await callback.answer("❌ Old search expired, search again!", show_alert=True)

    parts = callback.data.split("_")
    index = int(parts[1])
    quality = parts[2]  # 128 / 192 / 320 kbps
    results = SEARCH_CACHE[chat_id]
    video = results[index]

    m = await callback.message.edit(f"⬇ Downloading {video.get('title')} @ {quality} kbps ...")

    file_name = "".join(c for c in video.get('title') if c.isalnum() or c in " -_") + ".mp3"

    cookies_path = "cookies.txt"
    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "outtmpl": file_name,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": quality,
            }
        ],
        "cookiefile": cookies_path,
        "nocheckcertificate": True,
        "geo_bypass": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video.get("url")])

        await client.send_audio(
            chat_id=chat_id,
            audio=file_name,
            title=video.get("title"),
            performer="YouTube",
            caption=f"🎶 {video.get('title')}\n📻 YouTube"
        )
        await m.delete()
        os.remove(file_name)

    except yt_dlp.utils.DownloadError as e:
        await m.edit(f"⚠ Download error:\n{e}\n\nCheck your cookies or video availability.")
    except Exception as e:
        await m.edit(f"⚠ Unexpected error:\n{e}")
