from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import requests
from info import CHNL_LNK

API_URL = "https://apis.xditya.me/lyrics?song="


@Client.on_message(filters.command("lyrics") & filters.private)
async def fetch_lyrics(bot, message):
    """Ask for song name and display lyrics with language toggle buttons."""
    prompt = await bot.ask(
        chat_id=message.from_user.id,
        text="🎤 **Please send the song name:**"
    )

    if not prompt.text:
        return await prompt.reply_text("❌ Only text is allowed!")

    song_name = prompt.text
    loading_msg = await prompt.reply_text("🔎 Searching lyrics...")

    try:
        # Fetch both Hindi and English lyrics
        lyrics_hindi, lyrics_english = get_lyrics(song_name)

        # Send initial Hindi lyrics with buttons
        await loading_msg.edit_text(
            text=lyrics_hindi,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Owner", url="https://t.me/myselfneon"),
                    InlineKeyboardButton("English", callback_data=f"lang|english|{song_name}")
                ]
            ]),
            disable_web_page_preview=True
        )
    except Exception:
        await loading_msg.edit_text(
            f"🚫 **Couldn't find lyrics for:** `{song_name}`",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("✨ Updates", url=CHNL_LNK)]]
            )
        )


@Client.on_callback_query()
async def language_toggle(bot: Client, query: CallbackQuery):
    """Handle inline button presses for language toggle or closing message."""
    data = query.data.split("|")
    
    if data[0] == "lang":
        lang = data[1]
        song_name = data[2]

        lyrics_hindi, lyrics_english = get_lyrics(song_name)

        if lang == "english":
            await query.message.edit_text(
                text=lyrics_english,
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("Hindi", callback_data=f"lang|hindi|{song_name}"),
                        InlineKeyboardButton("Close", callback_data="close")
                    ]
                ]),
                disable_web_page_preview=True
            )
        elif lang == "hindi":
            await query.message.edit_text(
                text=lyrics_hindi,
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("Owner", url="https://t.me/myselfneon"),
                        InlineKeyboardButton("English", callback_data=f"lang|english|{song_name}")
                    ]
                ]),
                disable_web_page_preview=True
            )

    elif data[0] == "close":
        await query.message.delete()


def get_lyrics(song):
    """Fetch lyrics from the API in both Hindi and English."""
    response = requests.get(API_URL + song)
    data = response.json()

    if "lyrics" not in data or not data["lyrics"]:
        raise ValueError("Lyrics not found")

    # Example conversion for demonstration
    # In real scenario, you may have separate Hindi/English fields from API
    lyrics_english = f"🎶 **Lyrics of '{song}' in English:**\n\n`{data['lyrics']}`\n\n✨ **Join @NeonFiles**"
    lyrics_hindi = f"🎶 **'{song}' के गाने के बोल:**\n\n`{translate_to_hindi(data['lyrics'])}`\n\n✨ **Join @NeonFiles**"

    return lyrics_hindi, lyrics_english


def translate_to_hindi(text):
    """Dummy function: Replace with proper Hindi translation or API."""
    # Here we just return same text for demo; you can integrate Google Translate API
    return text.replace("Aaj ki raat", "आज की रात")
