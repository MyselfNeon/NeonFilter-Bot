from asyncio import sleep
from plugins.Extra.rename.filedetect import refunc
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ForceReply, CallbackQuery
from pyrogram.errors import FloodWait
from info import RENAME_MODE
import humanize
import random

@Client.on_message(filters.private & filters.command("rename"))
async def rename_start(client, message):
    if RENAME_MODE == False:
        return 
    msg = await client.ask(message.chat.id, "**__Now send me your File/Video/Audio you want to Rename 📝__**")
    if not msg.media:
        return await message.reply("**__Please send me supported media.__**")
    if msg.media in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.DOCUMENT, enums.MessageMediaType.AUDIO]:
        file = getattr(msg, msg.media.value)
        filename = file.file_name
        filesize = humanize.naturalsize(file.file_size) 
        fileid = file.file_id
        text = f"""<blockquote>**‣ ℕ𝕠𝕨 𝔼𝕟𝕥𝕖𝕣 ℕ𝕖𝕨 𝔽𝕚𝕝𝕖 𝕟𝕒𝕞𝕖 ....**</blockquote>\n\n<blockquote>**__‣ 𝕆𝕣𝕚𝕘𝕚𝕟𝕒𝕝 𝔽𝕚𝕝𝕖 ℕ𝕒𝕞𝕖__**</blockquote>\n`{filename}`\n\n**__Original File Size__** : `{filesize}`"""
        await message.reply_text(text)
        kk = await client.listen(message.from_user.id)
        await refunc(client, message, kk.text, msg)
      
