from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import requests, re
from bs4 import BeautifulSoup
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

# --- Scrapers ---
def search_lyricsmint(query: str):
    try:
        url = f"https://www.lyricsmint.com/search?q={query.replace(' ', '+')}"
        r = requests.get(url, timeout=10).text
        soup = BeautifulSoup(r, "html.parser")
        song_link = soup.find("a", class_="title")
        if not song_link: return None, None
        page = requests.get(song_link["href"], timeout=10).text
        soup = BeautifulSoup(page, "html.parser")
        lyrics_div = soup.find("div", {"class": "lyricbox"})
        lyrics = lyrics_div.get_text("\n").strip() if lyrics_div else None
        info_div = soup.find("div", class_="info")
        artist = info_div.get_text("\n").strip() if info_div else "Unknown"
        return lyrics, artist
    except:
        return None, None

def search_bharatlyrics(query: str):
    try:
        url = f"https://bharatlyrics.com/?s={query.replace(' ', '+')}"
        r = requests.get(url, timeout=10).text
        soup = BeautifulSoup(r, "html.parser")
        song_link = soup.find("a", class_="eg-post-title")
        if not song_link: return None, None
        page = requests.get(song_link["href"], timeout=10).text
        soup = BeautifulSoup(page, "html.parser")
        lyrics_div = soup.find("div", class_="lyric-content")
        lyrics = lyrics_div.get_text("\n").strip() if lyrics_div else None
        meta = soup.find("div", class_="post-meta")
        artist = meta.get_text("\n").strip() if meta else "Unknown"
        return lyrics, artist
    except:
        return None, None

def search_starmaker(query: str):
    try:
        url = f"https://www.starmakerstudios.com/en/search?keyword={query.replace(' ', '%20')}"
        r = requests.get(url, timeout=10).text
        soup = BeautifulSoup(r, "html.parser")
        song_link = soup.find("a", href=re.compile(r"/song/"))
        if not song_link: return None, None
        page = requests.get("https://www.starmakerstudios.com"+song_link["href"], timeout=10).text
        soup = BeautifulSoup(page, "html.parser")
        lyrics_div = soup.find("div", {"class": "lyrics"})
        lyrics = lyrics_div.get_text("\n").strip() if lyrics_div else None
        artist_div = soup.find("h2", class_="artist")
        artist = artist_div.get_text().strip() if artist_div else "Unknown"
        return lyrics, artist
    except:
        return None, None

# --- Detect Roman Hindi or Hindi ---
def detect_lang(query: str) -> str:
    # List of typical Hindi words in Roman script
    roman_hindi_keywords = ["ishq","bukhar","pyaar","dil","nasha","jaan","mohabbat","aashiqui"]
    if re.search(r"[\u0900-\u097F]", query):   # Hindi Unicode
        return "hindi"
    if any(word.lower() in query.lower() for word in roman_hindi_keywords):
        return "hindi"
    return "hindi"  # everything else treat as Hindi (no English fallback)

# --- Transliterate Devanagari to Roman ---
def devanagari_to_roman(text: str):
    try:
        return transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
    except:
        return text

# --- /lyrics command ---
@Client.on_message(filters.command("lyrics"))
async def lyrics_handler(client, message):
    if len(message.command)<2:
        return await message.reply("🎵 Usage: `/lyrics <song>`")
    query = " ".join(message.command[1:])
    lang_type = detect_lang(query)

    await message.reply(f"🔎 Searching ({lang_type}) lyrics for: **{query}** ...")

    # Search sequence: LyricsMint → BharatLyrics → Starmaker
    lyrics, artist = search_lyricsmint(query)
    if not lyrics: lyrics, artist = search_bharatlyrics(query)
    if not lyrics: lyrics, artist = search_starmaker(query)
    if not lyrics: return await message.reply("⚠️ Sorry, no lyrics found.")

    if len(lyrics)>4000: lyrics = lyrics[:3990] + "\n...\n⚠️ Lyrics truncated."

    roman_lyrics = devanagari_to_roman(lyrics)

    buttons = InlineKeyboardMarkup([[
        InlineKeyboardButton("👤 Owner", url="https://t.me/myselfneon"),
        InlineKeyboardButton("🌍 English", callback_data=f"lyrics:roman:{query}")
    ]])

    await message.reply_text(f"{lyrics}\n\n👤 Artist: {artist}", reply_markup=buttons, disable_web_page_preview=True)

# --- Callback handler ---
@Client.on_callback_query(filters.regex(r"^lyrics:"))
async def lyrics_callback(client, callback: CallbackQuery):
    data = callback.data.split(":")
    action = data[1]

    if action=="roman":
        query = data[2]
        lyrics, artist = search_lyricsmint(query)
        if not lyrics: lyrics, artist = search_bharatlyrics(query)
        if not lyrics: lyrics, artist = search_starmaker(query)
        roman_lyrics = devanagari_to_roman(lyrics)
        buttons = InlineKeyboardMarkup([[
            InlineKeyboardButton("🇮🇳 Hindi", callback_data=f"lyrics:hindi:{query}"),
            InlineKeyboardButton("❌ Close", callback_data="lyrics:close")
        ]])
        await callback.message.edit_text(f"{roman_lyrics}\n\n👤 Artist: {artist}", reply_markup=buttons, disable_web_page_preview=True)

    elif action=="hindi":
        query = data[2]
        lyrics, artist = search_lyricsmint(query)
        if not lyrics: lyrics, artist = search_bharatlyrics(query)
        if not lyrics: lyrics, artist = search_starmaker(query)
        buttons = InlineKeyboardMarkup([[
            InlineKeyboardButton("👤 Owner", url="https://t.me/myselfneon"),
            InlineKeyboardButton("🌍 English", callback_data=f"lyrics:roman:{query}")
        ]])
        await callback.message.edit_text(f"{lyrics}\n\n👤 Artist: {artist}", reply_markup=buttons, disable_web_page_preview=True)

    elif action=="close":
        await callback.message.delete()
