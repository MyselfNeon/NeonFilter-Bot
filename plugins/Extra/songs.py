from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import aiohttp
from info import CHNL_LNK

API = "https://lyrics-api.fly.dev/search?q="


@Client.on_message(filters.command("lrc"))
async def lyrics_cmd(bot, message):
    if len(message.command) < 2:
        return await message.reply_text("❗Usage: `/lrc <song name>`", quote=True)

    song = " ".join(message.command[1:])
    msg = await message.reply_text(f"🎶 Searching lyrics for **{song}** 🔎")

    lyrics_data = await search(song)

    if not lyrics_data or "lyrics" not in lyrics_data:
        return await msg.edit_text(f"❌ No lyrics found for **{song}**")

    text = (
        f"🎶 **Lyrics for {song}** 🎶\n\n"
        f"{lyrics_data['lyrics']}\n\n"
        f"✨ Join [Updates]({CHNL_LNK})"
    )

    # Split long lyrics into multiple messages
    parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
    await msg.delete()

    for part in parts:
        await message.reply_text(
            part,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Updates", url=CHNL_LNK)]]
            ),
            disable_web_page_preview=True
        )


async def search(song):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API + song) as resp:
                if resp.status == 200:
                    return await resp.json()
    except Exception as e:
        print(f"Lyrics API error: {e}")
    return None
