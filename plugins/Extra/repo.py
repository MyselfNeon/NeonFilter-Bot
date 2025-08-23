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
<b><i>Name : {qw.get("name")}</b></i>

<b><i>Full Name : {qw.get("full_name")}</b></i>

<b><i>Link : <a href="{qw.get("html_url")}">Click Here</a></i></b>

<b><i>Fork Count : {qw.get("forks_count")}</i></b>

<b><i>Open Issues : {qw.get("open_issues")}</i></b>

<b><i>Powered by : {CHNL_LNK}</i></b>

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
