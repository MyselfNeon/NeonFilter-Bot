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
    msg = await client.ask(message.chat.id, "**__Now send me your File/Video/Audio you want to Rename.__ 📝**")
    if not msg.media:
        return await message.reply("**__Please send me supported media.__**")
    if msg.media in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.DOCUMENT, enums.MessageMediaType.AUDIO]:
        file = getattr(msg, msg.media.value)
        filename = file.file_name
        filesize = humanize.naturalsize(file.file_size) 
        fileid = file.file_id
        text = f"""**<u>𝐄𝐍𝐓𝐄𝐑 𝐍𝐄𝐖 𝐅𝐈𝐋𝐄 𝐍𝐀𝐌𝐄</u>  🆕**\n\n𝙊𝙧𝙞𝙜𝙞𝙣𝙖𝙡 𝙁𝙞𝙡𝙚 𝙉𝙖𝙢𝙚 :\n`{filename}`\n\n𝙊𝙧𝙞𝙜𝙞𝙣𝙖𝙡 𝙁𝙞𝙡𝙚 𝙎𝙞𝙯𝙚 : `{filesize}`"""
        await message.reply_text(text)
        kk = await client.listen(message.from_user.id)
        await refunc(client, message, kk.text, msg)
        
