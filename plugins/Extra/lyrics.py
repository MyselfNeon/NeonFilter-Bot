
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton 
from info import CHNL_LNK
import requests 

import os


API = "https://apis.xditya.me/lyrics?song="

@Client.on_message(filters.text & filters.command(["lyrics"]))
async def sng(bot, message):
    vj = await bot.ask(chat_id=message.from_user.id, text="**__Now Send me Song Name__ 🎙️**")
    if vj.text:
        mee = await vj.reply_text("**__`Searching 🔎`__**")
        song = vj.text
        chat_id = message.from_user.id
        rpl = lyrics(song)
        await mee.delete()
        try:
            await mee.delete()
            await bot.send_message(chat_id, text = rpl, reply_to_message_id = message.id, reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Uᴘᴅᴀᴛᴇs ", url = CHNL_LNK)]]))
        except Exception as e:                            
            await vj.reply_text(f"**__I Can't Find A Song With `{song}` 🚫__**", quote = True, reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("ᴜᴘᴅᴀᴛᴇs", url = CHNL_LNK)]]))
    else:
        await vj.reply_text("**__Send me Only Text Buddy 😊__**")


def search(song):
    r = requests.get(API + song)
    find = r.json()
    return find
       
def lyrics(song):
    fin = search(song)
    text = f'**🎶 __Sᴜᴄᴄᴇꜱꜰᴜʟʟy Exᴛʀᴀᴄᴛᴇᴅ Lyɪʀɪᴄꜱ Oꜰ {song}__**\n\n'
    text += f'`{fin["lyrics"]}`'
    text += '\n\n\n**__Made By Team @NeonFiles ✨__**'
    return text



