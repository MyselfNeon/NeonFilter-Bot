import logging
import os
import requests
from info import CHNL_LNK
from pyrogram import Client, filters
from datetime import datetime


def format_date(date_str):
    """Convert ISO date string to human friendly format"""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
        return dt.strftime("%d %b %Y, %I:%M %p")
    except Exception:
        return date_str


@Client.on_message(filters.command('repo'))
async def git(bot, message):
    pablo = await message.reply_text("**__Processing...__ ✨**")

    # Check if user provided input
    if len(message.command) == 1:
        await pablo.edit("**__No Input Found__**")
        return

    # Extract search text
    args = message.text.split(None, 1)[1]

    # Call GitHub API
    r = requests.get("https://api.github.com/search/repositories", params={"q": args})
    lool = r.json()

    if lool.get("total_count") == 0:
        await pablo.edit("**__File Not Found__ 🥲**")
        return

    # First repo from results
    lol = lool.get("items")
    qw = lol[0]

    # Format numbers with commas
    stars = f"{qw.get('stargazers_count'):,}"
    watchers = f"{qw.get('watchers_count'):,}"
    forks = f"{qw.get('forks_count'):,}"
    issues = f"{qw.get('open_issues'):,}"

    txt = f"""
<blockquote><b>𝐑𝐄𝐏𝐎𝐒𝐈𝐓𝐎𝐑𝐘 𝐑𝐄𝐒𝐔𝐋𝐓𝐒</b></blockquote>

<b>🪪 <i>Nᴀᴍᴇ : {qw.get("name").capitalize()}</b></i>
<b>🛐 <i>Oᴡɴᴇʀ : {qw["owner"]["login"].capitalize()}</b></i>

<b>🖇️ <i>Rᴇᴘᴏ Lɪɴᴋ : <a href="{qw.get("html_url")}">Click Here</a></i></b>

<b>⭐ <i>Sᴛᴀʀs : {stars}</i></b>
<b>👀 <i>Wᴀᴛᴄʜᴇʀs : {watchers}</i></b>
<b>🍴 <i>Fᴏʀᴋs : {forks}</i></b>
<b>🐞 <i>Oᴘᴇɴ Issᴜᴇs : {issues}</i></b>

<b>🔥 <i>Bᴏᴛ Pᴏᴡᴇʀᴇᴅ Bʏ : <a href="{CHNL_LNK}">@NeonFiles</a></i></b>
"""

    # Put description immediately after main details
    if qw.get("description"):
        txt += f'\n<b><i>📝 Dᴇsᴄʀɪᴘᴛɪᴏɴ :</b></i>\n<blockquote expandable>{qw.get("description")}</blockquote>'

    # Then add technical/meta info
    if qw.get("size"):
        txt += f'\n<b><i>Sɪᴢᴇ : {qw.get("size"):,} KB</i></b>'
    if qw.get("score"):
        txt += f'\n<b><i>Sᴄᴏʀᴇ : {qw.get("score")}</i></b>'
    if qw.get("language"):
        txt += f'\n<b><i>Lᴀɴɢᴜᴀɢᴇ : {qw.get("language")}</i></b>'
    if qw.get("created_at"):
        txt += f'\n\n<b><i>Cʀᴇᴀᴛᴇᴅ Oɴ : {format_date(qw.get("created_at"))}</i></b>'
    if qw.get("updated_at"):
        txt += f'\n<b><i>Uᴘᴅᴀᴛᴇᴅ Oɴ : {format_date(qw.get("updated_at"))}</i></b>'
    if qw.get("archived") is True:
        txt += f"\n\n<b><i>🔐 Tʜɪs Pʀᴏjᴇᴄᴛ Is Aʀᴄʜɪᴠᴇᴅ 🔐</i></b>"

    # Final edit
    await pablo.edit(txt, disable_web_page_preview=True)
