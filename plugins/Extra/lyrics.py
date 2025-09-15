from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import requests, asyncio, uuid, html

API_URL = "https://apis.xditya.me/lyrics?song="

# Cache to store lyrics and translations
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
    """Translate English -> Hindi using Google translate endpoint."""
    url = "https://translate.googleapis.com/translate_a/single"
    params = {"client": "gtx", "sl": "en", "tl": "hi", "dt": "t", "q": text}
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    j = resp.json()
    translated = "".join(segment[0] for segment in j[0])
    return translated


def format_html(title: str, lyrics: str) -> str:
    """Return HTML-safe formatted message (title + pre block for lyrics)."""
    return f"<b>🎶 {html.escape(title)}</b>\n\n<pre>{html.escape(lyrics)}</pre>\n\n<b>✨ Join @NeonFiles</b>"


async def show_progress(msg, text="Translating"):
    """Fake progress bar animation."""
    steps = [
        "[░░░░░░░░░░] 0%",
        "[▓░░░░░░░░░] 10%",
        "[▓▓░░░░░░░░] 30%",
        "[▓▓▓░░░░░░░] 50%",
        "[▓▓▓▓▓░░░░░] 70%",
        "[▓▓▓▓▓▓▓▓▓] 100%"
    ]
    for step in steps:
        try:
            await msg.edit_text(f"⏳ {text} {step}")
            await asyncio.sleep(0.4)  # delay between steps
        except Exception:
            break


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
        return await loading.edit_text(f"**__I Can't Find A Song With `{song}` 🚫__**")

    uid = uuid.uuid4().hex[:12]
    LYRICS_CACHE[uid] = {"song": song, "english": english_lyrics, "hindi": None}

    # Initial page = Hindi (but still English text until translation is requested)
    hindi_text = format_html(f"{song} — हिंदी", english_lyrics)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("English", callback_data=f"lang|english|{uid}"),
         InlineKeyboardButton("Close", callback_data=f"close|{uid}")]
    ])

    await loading.edit_text(hindi_text, reply_markup=keyboard,
                            disable_web_page_preview=True, parse_mode="html")


@Client.on_callback_query()
async def language_toggle(bot: Client, query: CallbackQuery):
    if not query.data:
        return await query.answer()

    parts = query.data.split("|")
    await query.answer()

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
            await query.message.edit_text(text, reply_markup=kb,
                                          disable_web_page_preview=True, parse_mode="html")

        elif target == "hindi":
            # Show progress while translating
            prog_msg = query.message
            await show_progress(prog_msg, "Translating")

            if cached["hindi"] is None:
                try:
                    cached["hindi"] = translate_to_hindi(cached["english"])
                except Exception:
                    cached["hindi"] = cached["english"]  # fallback

            text = format_html(f"{song} — हिंदी", cached["hindi"])
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("English", callback_data=f"lang|english|{uid}"),
                 InlineKeyboardButton("Close", callback_data=f"close|{uid}")]
            ])
            await prog_msg.edit_text(text, reply_markup=kb,
                                     disable_web_page_preview=True, parse_mode="html")

    elif parts[0] == "close":
        try:
            await query.message.delete()
        except Exception:
            pass
        uid = parts[1] if len(parts) > 1 else None
        if uid and uid in LYRICS_CACHE:
            del LYRICS_CACHE[uid]
