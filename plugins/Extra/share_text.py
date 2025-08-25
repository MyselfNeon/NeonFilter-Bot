
import os
from pyrogram import Client, filters
from urllib.parse import quote
from info import CHNL_LNK
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

@Client.on_message(filters.command(["share_text", "share", "sharetext"]))
async def share_text(client, message):
    vj = await client.ask(chat_id = message.from_user.id, text = "**__Now Send Me Your Text__ 😄**")
    if vj and (vj.text or vj.caption):
        input_text = vj.text or vj.caption
    else:
        await vj.reply_text(
            text=f"**__Notice:\n\n01. Send Any Text Messages.\n02. No Media Support__**\n\n**Join Update Channel**",               
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Updates Channel", url=CHNL_LNK)]])
            )                                                   
        return
    await vj.reply_text(
        text=f"**__Here is Your Sharing Text__ 👇**\n\nhttps://t.me/share/url?url=" + quote(input_text),
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("♂️ Sʜᴀʀᴇ", url=f"https://t.me/share/url?url={quote(input_text)}")]])       
    )
