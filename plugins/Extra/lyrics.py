from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import requests
import uuid
import html

API_URL = "https://apis.xditya.me/lyrics?song="
OWNER = "https://t.me/myselfneon"
CHNL_LNK = "https://t.me/NeonFiles"  # keep or import from info

# Simple in-memory cache for the current lyrics pages (uid -> data)
LYRICS_CACHE = {}


def get_lyrics_from_api(song: str) -> str:
    """Fetch raw English lyrics from your API."""
    r = requests.get(API_URL + song, timeout=15)
    r.raise_for_status()
    data = r.json()
    if "lyrics" not in data or not data["lyrics"]:
        raise ValueError("Lyrics not found")
    return data["lyrics"]


def translate_to_hindi(text: str) -> str:
    """
    Translate English -> Hindi using the public Google translate endpoint.
    Note: it's unofficial and may be rate-limited; for production use the
    official Google Cloud Translate API.
    """
    # If text is huge you may want to chunk it. For simplicity we translate whole text.
    url = "https://translate.googleapis.com/translate_a/single"
    params = {
        "client": "gtx",
        "sl": "en",
        "tl": "hi",
        "dt": "t",
        "q": text
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    j = resp.json()
    # j[0] is list of segments: [[translated_segment, original_segment, ...], ...]
    translated = "".join(segment[0] for segment in j[0])
    return translated


def format_html(title: str, lyrics: str) -> str:
    """Return HTML-safe formatted message (title + pre block for lyrics)."""
    return f"<b>🎶 {html.escape(title)}</b>\n\n<pre>{html.escape(lyrics)}</pre>\n\n<b>✨ Join @NeonFiles</b>"


@Client.on_message(filters.command("lyrics") & filters.private)
async def fetch_lyrics(bot: Client, message):
    prompt = await bot.ask(chat_id=message.from_user.id, text="**__Now Send me Song Name__ 🎙️**")
    if not prompt.text:
        return await prompt.reply_text("**__Send me Only Text Buddy 😊__**")

    song = prompt.text.strip()
    loading = await prompt.reply_text("`Searching 🔎`")

    try:
        english_lyrics = get_lyrics_from_api(song)
    except Exception:
        return await loading.edit_text(
            f"**__I Can't Find A Song With `{song}` 🚫__**",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✨ Updates", url=CHNL_LNK)]])
        )

    # try translating; fallback to english if translation fails
    try:
        hindi_lyrics = translate_to_hindi(english_lyrics)
    except Exception:
        hindi_lyrics = english_lyrics  # fallback

    # cache under a short uid (used in callback_data)
    uid = uuid.uuid4().hex[:12]
    LYRICS_CACHE[uid] = {"song": song, "english": english_lyrics, "hindi": hindi_lyrics}

    # initial page = HINDI
    hindi_text = format_html(f"{song} — हिंदी", hindi_lyrics)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Owner", url=OWNER),
         InlineKeyboardButton("English", callback_data=f"lang|english|{uid}")]
    ])

    await loading.edit_text(hindi_text, reply_markup=keyboard, disable_web_page_preview=True, parse_mode="html")


@Client.on_callback_query()
async def language_toggle(bot: Client, query: CallbackQuery):
    """
    callback_data format:
      - lang|english|<uid>
      - lang|hindi|<uid>
      - close|<uid>
    """
    if not query.data:
        return await query.answer()

    parts = query.data.split("|")
    await query.answer()  # remove 'loading' on client

    if parts[0] == "lang" and len(parts) == 3:
        target = parts[1]
        uid = parts[2]
        cached = LYRICS_CACHE.get(uid)
        if not cached:
            return await query.message.edit_text("⚠️ This lyrics session expired. Please run /lyrics again.")

        song = cached["song"]

        if target == "english":
            text = format_html(f"{song} — English", cached["english"])
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("Hindi", callback_data=f"lang|hindi|{uid}"),
                 InlineKeyboardButton("Close", callback_data=f"close|{uid}")]
            ])
            await query.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True, parse_mode="html")

        elif target == "hindi":
            text = format_html(f"{song} — हिंदी", cached["hindi"])
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("Owner", url=OWNER),
                 InlineKeyboardButton("English", callback_data=f"lang|english|{uid}")]
            ])
            await query.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True, parse_mode="html")

    elif parts[0] == "close":
        uid = parts[1] if len(parts) > 1 else None
        # delete message and clear cache for this uid
        try:
            await query.message.delete()
        except Exception:
            pass
        if uid and uid in LYRICS_CACHE:
            del LYRICS_CACHE[uid]
            
