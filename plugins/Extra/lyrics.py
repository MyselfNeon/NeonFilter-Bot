# Lyrics_Ultimate_Fixed.py
import asyncio
import aiohttp
from urllib.parse import quote
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# --- ⚙️ CONFIG ---
SEARCH_STICKER = "CAACAgIAAxkBAAIpb2jHer7l0e-CfAOB2Yy2SBDOzi7oAALdAAMw1J0RjVUlFacabq8eBA"

# --- 🌐 ASYNC API CLIENT ---
async def fetch_lyrics(query: str):
    """Fetches lyrics and album art asynchronously."""
    async with aiohttp.ClientSession() as session:
        try:
            # 1. Clean the query
            clean_query = query.replace(".mp3", "").replace(".flac", "").strip()
            
            # 2. Encode the query (Fixes 'not working' issue with spaces)
            encoded_query = quote(clean_query)
            
            # 3. Call API
            url = f"https://lyrist.vercel.app/api/{encoded_query}" 
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                
                if "lyrics" not in data or not data["lyrics"]:
                    return None
                
                return {
                    # Use .title() to make it look nice if API returns lowercase
                    "title": data.get("title", clean_query.title()),
                    "artist": data.get("artist", "Unknown Artist"),
                    "lyrics": data.get("lyrics", ""),
                    "image": data.get("image", "https://telegra.ph/file/5a53e8392182270921478.jpg")
                }
        except Exception:
            return None

# --- 🛠 HELPERS ---
def split_text(text: str, limit=1000):
    """Splits long lyrics into pages."""
    chunks = []
    current_chunk = ""
    for line in text.split("\n"):
        if len(current_chunk) + len(line) < limit:
            current_chunk += line + "\n"
        else:
            chunks.append(current_chunk)
            current_chunk = line + "\n"
    chunks.append(current_chunk)
    return chunks

# --- 🎵 MAIN HANDLER ---
@Client.on_message(filters.command(["lyrics", "lrc"]))
async def lyrics_handler(client: Client, message: Message):
    query = ""
    
    # 1️⃣ Case: Argument (/lyrics Faded)
    if len(message.command) > 1:
        query = message.text.split(maxsplit=1)[1]
        
    # 2️⃣ Case: Reply to Audio
    elif message.reply_to_message and message.reply_to_message.audio:
        audio = message.reply_to_message.audio
        # If metadata exists, use it. If not, fallback to filename.
        if audio.title:
            query = audio.title  # Just search Title (Artist is optional)
        else:
            query = audio.file_name or "Unknown"

    # 3️⃣ Case: Reply to Text
    elif message.reply_to_message and message.reply_to_message.text:
        query = message.reply_to_message.text

    # 4️⃣ Case: Interactive (Ask User)
    else:
        try:
            stk = await message.reply_sticker(SEARCH_STICKER)
            await asyncio.sleep(1)
            await stk.delete()
            
            # FIXED PROMPT: Only asks for Song Name now
            ask_msg = await client.ask(
                message.chat.id, 
                "**__Now Send me Song Name__ 🎙️**",
                timeout=30
            )
            if ask_msg.text:
                query = ask_msg.text
            else:
                return await message.reply_text("❌ **Text only please.**")
        except:
            return await message.reply_text("⚠️ **Usage:** `/lyrics <song name>`")

    # --- Processing ---
    status_msg = await message.reply_text(f"🔎 **Searching lyrics for:** `{query}`...")
    
    song_data = await fetch_lyrics(query)
    
    if not song_data:
        # Helpful error message, not demanding
        return await status_msg.edit(
            f"❌ **Lyrics not found for:** `{query}`\n\n"
            f"__💡 Hint: Try typing `SongName ArtistName` (e.g., `Believer Imagine Dragons`) if the song is common.__"
        )

    # --- Pagination Setup ---
    lyrics_pages = split_text(song_data['lyrics'])
    total_pages = len(lyrics_pages)
    
    # Generate First Page Text
    text_content = (
        f"💿 **{song_data['title']}**\n"
        f"👤 **{song_data['artist']}**\n\n"
        f"{lyrics_pages[0]}"
    )
    if total_pages > 1:
        text_content += f"\n\n📖 **Page 1/{total_pages}**"

    # Buttons
    buttons = []
    if total_pages > 1:
        buttons.append([
            InlineKeyboardButton("➡️ Next", callback_data=f"lyr_next|0|{query}")
        ])
    
    buttons.append([
        InlineKeyboardButton("👾 Developer", url="https://myselfneon.github.io/neon/"),
        InlineKeyboardButton("🗑 Close", callback_data="lyr_close")
    ])

    await status_msg.delete()
    
    # Send Result
    await message.reply_photo(
        photo=song_data['image'],
        caption=text_content,
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    
# --- 🖱️ CALLBACK HANDLERS ---
@Client.on_callback_query(filters.regex(r"^lyr_"))
async def lyrics_callback(client: Client, query: CallbackQuery):
    data = query.data.split("|")
    action = data[0]
    
    if action == "lyr_close":
        await query.message.delete()
        return

    current_page = int(data[1])
    search_query = data[2]
    
    song_data = await fetch_lyrics(search_query) 
    if not song_data:
        return await query.answer("❌ Error reloading lyrics.", show_alert=True)
        
    pages = split_text(song_data['lyrics'])
    total = len(pages)
    
    if action == "lyr_next":
        new_page = current_page + 1
    elif action == "lyr_prev":
        new_page = current_page - 1
    else:
        new_page = 0
        
    if new_page < 0 or new_page >= total:
        return await query.answer("🚫 No more pages.", show_alert=True)

    new_text = (
        f"💿 **{song_data['title']}**\n"
        f"👤 **{song_data['artist']}**\n\n"
        f"{pages[new_page]}\n\n"
        f"📖 **Page {new_page+1}/{total}**"
    )

    nav_buttons = []
    if new_page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"lyr_prev|{new_page}|{search_query}"))
    if new_page < total - 1:
        nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"lyr_next|{new_page}|{search_query}"))
        
    final_kb = [nav_buttons] if nav_buttons else []
    final_kb.append([
        InlineKeyboardButton("👾 Developer", url="https://myselfneon.github.io/neon/"),
        InlineKeyboardButton("🗑 Close", callback_data="lyr_close")
    ])

    await query.message.edit_caption(
        caption=new_text,
        reply_markup=InlineKeyboardMarkup(final_kb)
            )
    
