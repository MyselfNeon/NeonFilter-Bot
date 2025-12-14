# ---------------------------------------------------
# File Name: Github.py
# Author: NeonAnurag
# GitHub: https://github.com/MyselfNeon/
# Telegram: https://t.me/MyelfNeon
# ---------------------------------------------------

import logging
import requests
from info import CHNL_LNK
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from datetime import datetime

# In-memory cache to store search results for pagination
REPO_CACHE = {}

def format_date(date_str):
    """Convert ISO date string to human friendly format"""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
        return dt.strftime("%d %b %Y, %I:%M %p")
    except Exception:
        return date_str

def get_repo_buttons(owner_url, html_url, current_index, total_count, unique_id):
    """Generates advanced inline buttons with pagination"""
    
    # Row 1: External Links
    buttons = [
        [
            InlineKeyboardButton("🖇️ 𝐋𝐢𝐧𝐤", url=html_url),
            InlineKeyboardButton("📥 𝐙𝐢𝐩", url=f"{html_url}/archive/master.zip"),
            InlineKeyboardButton("👤 𝐎𝐰𝐧𝐞𝐫", url=owner_url) # FIXED: Uses correct Owner URL
        ]
    ]

    # Row 2: Pagination (only if more than 1 result)
    if total_count > 1:
        nav_buttons = []
        # Previous Button
        if current_index > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"repo_prev_{unique_id}_{current_index}"))
        else:
            nav_buttons.append(InlineKeyboardButton("🛑", callback_data="repo_noop"))

        # Counter (Center)
        nav_buttons.append(InlineKeyboardButton(f"{current_index + 1}/{total_count}", callback_data="repo_noop"))

        # Next Button
        if current_index < total_count - 1:
            nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"repo_next_{unique_id}_{current_index}"))
        else:
            nav_buttons.append(InlineKeyboardButton("🛑", callback_data="repo_noop"))
            
        buttons.append(nav_buttons)

    # Row 3: Close
    buttons.append([InlineKeyboardButton("❌ 𝐂𝐥𝐨𝐬𝐞", callback_data="close_data")])
    
    return InlineKeyboardMarkup(buttons)

def generate_repo_text(repo_data):
    """Generates the formatted text using your specific style"""
    name = repo_data.get("name").capitalize()
    owner = repo_data["owner"]["login"].capitalize()
    html_url = repo_data.get("html_url")
    stars = f"{repo_data.get('stargazers_count'):,}"
    watchers = f"{repo_data.get('watchers_count'):,}"
    forks = f"{repo_data.get('forks_count'):,}"
    issues = f"{repo_data.get('open_issues'):,}"
    
    # Extra Advanced Fields
    language = repo_data.get("language") or "None"
    license_info = repo_data.get("license", {}).get("name") if repo_data.get("license") else "None"
    size_mb = round(repo_data.get("size", 0) / 1024, 2)
    topics = repo_data.get("topics", [])
    
    # Create Hashtags from topics
    topic_text = " ".join([f"#{t}" for t in topics[:5]]) if topics else ""

    txt = f"""
<blockquote><b>𝐑𝐄𝐏𝐎𝐒𝐈𝐓𝐎𝐑𝐘 𝐑𝐄𝐒𝐔𝐋𝐓𝐒</b></blockquote>

<b>🪪 <i>Nᴀᴍᴇ : {name}</b></i>
<b>🛐 <i>Oᴡɴᴇʀ : {owner}</b></i>
<b>⚖️ <i>Lɪᴄᴇɴsᴇ : {license_info}</i></b>

<b>⭐ <i>Sᴛᴀʀs : {stars}</i></b>
<b>👀 <i>Wᴀᴛᴄʜᴇʀs : {watchers}</i></b>
<b>🍴 <i>Fᴏʀᴋs : {forks}</i></b>
<b>🐞 <i>Oᴘᴇɴ Issᴜᴇs : {issues}</i></b>

<b>🔥 <i>Bᴏᴛ Pᴏᴡᴇʀᴇᴅ Bʏ : <a href="{CHNL_LNK}">@NeonFiles</a></i></b>
"""

    if repo_data.get("description"):
        txt += f'\n<b><i>📝 Dᴇsᴄʀɪᴘᴛɪᴏɴ :</b></i>\n<blockquote expandable>{repo_data.get("description")}</blockquote>'

    # Technical Details
    txt += f'\n<b><i>💾 Sɪᴢᴇ : {size_mb} MB</i></b>'
    txt += f'\n<b><i>⚡ Sᴄᴏʀᴇ : {repo_data.get("score", 0)}</i></b>'
    txt += f'\n<b><i>🗣️ Lᴀɴɢᴜᴀɢᴇ : {language}</i></b>'
    
    if topic_text:
        txt += f'\n<b><i>🏷️ Tᴏᴘɪᴄs : <code>{topic_text}</code></i></b>'

    if repo_data.get("created_at"):
        txt += f'\n\n<b><i>📅 Cʀᴇᴀᴛᴇᴅ : {format_date(repo_data.get("created_at"))}</i></b>'
    if repo_data.get("updated_at"):
        txt += f'\n<b><i>🔄 Uᴘᴅᴀᴛᴇᴅ : {format_date(repo_data.get("updated_at"))}</i></b>'
    
    if repo_data.get("archived"):
        txt += f"\n\n<b><i>🔐 Tʜɪs Pʀᴏjᴇᴄᴛ Is Aʀᴄʜɪᴠᴇᴅ 🔐</i></b>"
        
    return txt

@Client.on_message(filters.command(['repo', 'git']))
async def git_search(bot, message):
    pablo = await message.reply_text("**__Processing...__ ✨**")

    if len(message.command) == 1:
        await pablo.edit("**__No Input Found__ 🥲**")
        return

    query = message.text.split(None, 1)[1]
    
    try:
        r = requests.get("https://api.github.com/search/repositories", params={"q": query, "per_page": 10})
        res = r.json()
    except Exception as e:
        await pablo.edit(f"**Error:** `{e}`")
        return

    if res.get("total_count", 0) == 0:
        await pablo.edit("**__No Repositories Found__ 🥲**")
        return

    items = res.get("items", [])
    
    # Store results in cache with a unique ID (chat_id-msg_id)
    unique_id = f"{message.chat.id}-{message.id}"
    REPO_CACHE[unique_id] = items

    # Display the first result (index 0)
    repo_data = items[0]
    text = generate_repo_text(repo_data)
    
    # FIXED: Extract owner URL here and pass it correctly
    owner_url = repo_data["owner"]["html_url"]
    buttons = get_repo_buttons(owner_url, repo_data["html_url"], 0, len(items), unique_id)

    await pablo.edit(text, reply_markup=buttons, disable_web_page_preview=True)


@Client.on_callback_query(filters.regex(r"^repo_(next|prev)_"))
async def repo_pagination(bot, query: CallbackQuery):
    data = query.data.split("_")
    action = data[1]       # next or prev
    unique_id = data[2]    # Cache Key
    current_index = int(data[3])

    # Retrieve data from cache
    items = REPO_CACHE.get(unique_id)
    if not items:
        await query.answer("❌ Search results expired. Please search again.", show_alert=True)
        return

    # Calculate new index
    if action == "next":
        new_index = current_index + 1
    else:
        new_index = current_index - 1

    # Validate index
    if 0 <= new_index < len(items):
        repo_data = items[new_index]
        text = generate_repo_text(repo_data)
        
        # FIXED: Extract owner URL here and pass it correctly
        owner_url = repo_data["owner"]["html_url"]
        buttons = get_repo_buttons(owner_url, repo_data["html_url"], new_index, len(items), unique_id)
        
        await query.edit_message_text(
            text, 
            reply_markup=buttons, 
            disable_web_page_preview=True
        )
    else:
        await query.answer("End of results!", show_alert=False)

@Client.on_callback_query(filters.regex("^repo_noop"))
async def repo_noop(bot, query: CallbackQuery):
    await query.answer()

# Note: Ensure 'close_data' handler exists in your bot's other plugins
