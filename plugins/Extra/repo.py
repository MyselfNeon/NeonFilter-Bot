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

<b>📛 <i>Nᴀᴍᴇ : {qw.get("name")}</b></i>

<b>🪪 <i>Owner : {qw["owner"]["login"]}</b></i>

<b>🖇️ <i>Lɪɴᴋ : <a href="{qw.get("html_url")}">Click Here</a></i></b>

<b>🍴 <i>Fᴏʀᴋ Cᴏᴜɴᴛ : {qw.get("forks_count")}</i></b>

<b>🐞 <i>Oᴘᴇɴ Issᴜᴇs : {qw.get("open_issues")}</i></b>

<b>🔥 <i>Pᴏᴡᴇʀᴇᴅ Bʏ : <a href="{CHNL_LNK}">@NeonFiles</a></i></b>

"""
        if qw.get("description"):
            txt += f'<b>Description :</b> <code>{qw.get("description")}</code>'

        if qw.get("language"):
            txt += f'<b>Language :</b> <code>{qw.get("language")}</code>'

        if qw.get("size"):
            txt += f'<b>Size :</b> <code>{qw.get("size")}</code>'

        if qw.get("score"):
            txt += f'<b>Score :</b> <code>{qw.get("score")}</code>'

        if qw.get("created_at"):
            txt += f'<b>Created At :</b> <code>{qw.get("created_at")}</code>'

        if qw.get("archived") == True:
            txt += f"<b>This Project is Archived</b>"
        await pablo.edit(txt, disable_web_page_preview=True)
