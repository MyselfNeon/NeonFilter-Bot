import logging
import os
import requests
from info import CHNL_LNK
from pyrogram import Client, filters


@Client.on_message(filters.command('repo'))
async def git(bot, message):
    pablo = await message.reply_text("**__Processing...__ ✨**")
    args = message.text.split(None, 1)[1]
    if len(message.command) == 1:
        await pablo.edit("**__No Input Found__**")
        return
    r = requests.get("https://api.github.com/search/repositories", params={"q": args})
    lool = r.json()
    if lool.get("total_count") == 0:
        await pablo.edit("**__File Not Found__ 🥲**")
        return
    else:
        lol = lool.get("items")
        qw = lol[0]
        txt = f"""
<blockquote>𝐑𝐄𝐏𝐎𝐒𝐈𝐓𝐎𝐑𝐘 𝐑𝐄𝐒𝐔𝐋𝐓𝐒</blockquote>

<b>🪪 <i>Nᴀᴍᴇ : {qw.get("name")}</b></i>
<b>🛐 <i>Oᴡɴᴇʀ : {qw["owner"]["login"].capitalize()}</b></i>

<b>🖇️ <i>Rᴇᴘᴏ Lɪɴᴋ : <a href="{qw.get("html_url")}">Click Here</a></i></b>

<b>🍴 <i>Fᴏʀᴋ Cᴏᴜɴᴛ : {qw.get("forks_count")}</i></b>
<b>🐞 <i>Oᴘᴇɴ Issᴜᴇs : {qw.get("open_issues")}</i></b>

<b>🔥 <i>Bᴏᴛ Pᴏᴡᴇʀᴇᴅ Bʏ : <a href="{CHNL_LNK}">@NeonFiles</a></i></b>

"""
      
        if qw.get("size"):
            txt += f'<b><i>Sɪᴢᴇ : {qw.get("size")}</i></b>'
        if qw.get("score"):
            txt += f'\n<b><i>Sᴄᴏʀᴇ : {qw.get("score")}</i></b>'
        if qw.get("language"):
            txt += f'\n<b><i>Lᴀɴɢᴜᴀɢᴇ : {qw.get("language")}</i></b>'
        if qw.get("created_at"):
            txt += f'\n<b><i>Cʀᴇᴀᴛᴇᴅ Oɴ : {qw.get("created_at").replace("Z", "").replace("T", " T")}</i></b>'
            
        if qw.get("description"):
            txt += f'\n\n<b><i>📝 Dᴇsᴄʀɪᴘᴛɪᴏɴ :</b></i>\n<blockquote expandable>{qw.get("description")}</blockquote>'            

        if qw.get("archived") == True:
            txt += f"<b><i>\nTʜɪs Pʀᴏjᴇᴄᴛ Is Aʀᴄʜɪᴠᴇᴅ 🔐</i></b>"  
        await pablo.edit(txt, disable_web_page_preview=True)
