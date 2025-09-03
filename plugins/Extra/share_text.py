import os
from pyrogram import Client, filters
from urllib.parse import quote
from info import CHNL_LNK
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

@Client.on_message(filters.command(["share_text", "share", "sharetext"]))
async def share_text(client, message):
    neo = await client.ask(chat_id = message.from_user.id, text = "**__Now Send Me Your Text__ 😄**")
    if neo and (neo.text or neo.caption):
        input_text = neo.text or neo.caption
    else:
        await neo.reply_text(
            text=f"**__Notice:\n\n01. Send Any Text Messages.\n02. No Media Support__**\n\n**Join Update Channel**",               
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Updates Channel", url=CHNL_LNK)]])
            )                                                   
        return
    await neo.reply_text(
        text=f"**__Here is Your Sharing Text__ 👇**\n\nhttps://t.me/share/url?url=" + quote(input_text),
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("♂️ Sʜᴀʀᴇ", url=f"https://t.me/share/url?url={quote(input_text)}")]])       
    )
