#Lyrics.py
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import asyncio

API = "https://apis.xditya.me/lyrics?song="

STICKER_ID = "CAACAgIAAxkBAAIpb2jHer7l0e-CfAOB2Yy2SBDOzi7oAALdAAMw1J0RjVUlFacabq8eBA"


@Client.on_message(filters.command("lyrics") & filters.private)
async def sng(bot, message):
    # Ask user for song name
    neo = await bot.ask(
        chat_id=message.from_user.id,
        text="**__Now Send me Song Name__ 🎙️**"
    )

    if not neo.text:
        return await neo.reply_text("**__Send me Only Text Buddy 😊__**")

    song = neo.text.strip()

    # Send sticker as "searching" indicator
    sticker_msg = await bot.send_sticker(message.chat.id, STICKER_ID)
    await asyncio.sleep(2)  # keep sticker for 2 sec
    await sticker_msg.delete()

    try:
        rpl = lyrics(song)
        await bot.send_message(
            chat_id=message.from_user.id,
            text=rpl,
            reply_to_message_id=message.id,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Aᴡᴇsᴏᴍᴇ Dᴇᴠᴇʟᴏᴘᴇʀ", url="tg://user?id=841851780")]]
            ),
            disable_web_page_preview=True
        )
    except Exception:
        await neo.reply_text(
            f"**__I Can't Find A Song With `{song}` 🚫__**",
            quote=True,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Aᴡᴇsᴏᴍᴇ Dᴇᴠᴇʟᴏᴘᴇʀ 😎", url="https://t.me/MyselfNeon")]]
            )
        )


def search(song: str) -> dict:
    """Fetch lyrics JSON from API."""
    r = requests.get(API + song, timeout=10)
    r.raise_for_status()
    return r.json()


def lyrics(song: str) -> str:
    """Format lyrics message."""
    fin = search(song)
    return (
        f"<blockquote>**🎶 __Successfully Extracted Lyrics Of {song}__**</blockquote>\n\n"
        f"`{fin['lyrics']}`"
    )


# Dont Remove Credits
# Join @NeonFiles
# Developer @MyselfNeon
