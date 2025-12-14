# ---------------------------------------------------
# File Name: Paste_Pro.py
# Author: NeonAnurag
# GitHub: https://github.com/MyselfNeon/
# Telegram: https://t.me/MyelfNeon
# ---------------------------------------------------

import os
import re
import aiohttp
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

# 🌐 PASTEBIN API CLIENTS
# -----------------------
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.104 Safari/537.36",
    "Content-Type": "application/json",
}

async def paste_pasty(session, content, extension="txt"):
    """Primary: Pasty.lus.pm"""
    url = "https://pasty.lus.pm/api/v1/pastes"
    try:
        async with session.post(url, json={"content": content}, headers=HEADERS) as resp:
            if resp.status == 201:
                data = await resp.json()
                id_ = data["id"]
                return {
                    "url": f"https://pasty.lus.pm/{id_}.{extension}",
                    "raw": f"https://pasty.lus.pm/{id_}/raw",
                    "service": "Pasty"
                }
    except: pass
    return None

async def paste_spacebin(session, content, extension="txt"):
    """Fallback 1: Spaceb.in"""
    url = "https://spaceb.in/api/v1/documents/"
    try:
        async with session.post(url, json={"content": content, "extension": extension}) as resp:
            if resp.status == 201:
                data = await resp.json()
                id_ = data["payload"]["id"]
                return {
                    "url": f"https://spaceb.in/{id_}",
                    "raw": f"https://spaceb.in/api/v1/documents/{id_}/raw",
                    "service": "Spacebin"
                }
    except: pass
    return None

async def paste_dpaste(session, content, extension="txt"):
    """Fallback 2: Dpaste.org (Very Reliable)"""
    url = "https://dpaste.org/api/"
    data = {"content": content, "format": "json", "expiry_days": 7}
    try:
        async with session.post(url, data=data) as resp:
            if resp.status == 200:
                res = await resp.json()
                return {
                    "url": res["url"],
                    "raw": res["url"].replace("/api/", "/raw/"),
                    "service": "Dpaste"
                }
    except: pass
    return None

async def paste_nekobin(session, content, extension="txt"):
    """Fallback 3: Nekobin"""
    url = "https://nekobin.com/api/documents"
    try:
        async with session.post(url, json={"content": content}) as resp:
            if resp.status == 201:
                data = await resp.json()
                key = data["result"]["key"]
                return {
                    "url": f"https://nekobin.com/{key}",
                    "raw": f"https://nekobin.com/raw/{key}",
                    "service": "Nekobin"
                }
    except: pass
    return None

# 🎮 CONTROLLER LOGIC
# -----------------------
async def universal_paste(content):
    """Tries multiple services until one works."""
    async with aiohttp.ClientSession() as session:
        # Priority Order
        tasks = [
            paste_pasty(session, content),
            paste_spacebin(session, content),
            paste_dpaste(session, content),
            paste_nekobin(session, content)
        ]
        
        # Try one by one
        for task in tasks:
            result = await task
            if result:
                return result
                
    return {"error": "All paste services are currently down."}

# 🤖 BOT COMMAND
# -----------------------
@Client.on_message(filters.command(["paste", "bin"]))
async def paste_handler(client: Client, message: Message):
    # 1. Status Message
    status_msg = await message.reply_text("🔄 **Reading Input...**")
    
    # 2. Extract Text / File Content
    content = ""
    is_file = False
    
    # CASE A: Command Arguments
    if len(message.command) > 1:
        content = message.text.split(maxsplit=1)[1]
        
    # CASE B: Reply to Text
    elif message.reply_to_message and message.reply_to_message.text:
        content = message.reply_to_message.text
        
    # CASE C: Reply to Document/File
    elif message.reply_to_message and message.reply_to_message.document:
        is_file = True
        doc = message.reply_to_message.document
        
        # Limit file size to 2MB to prevent bot crashes
        if doc.file_size > 2 * 1024 * 1024:
            return await status_msg.edit("❌ **File too large!** (Max 2MB)")
        
        if doc.mime_type and "image" in doc.mime_type:
            return await status_msg.edit("❌ **Images not supported!** Text only.")

        await status_msg.edit("📥 **Downloading File...**")
        
        # Download to memory (no disk I/O)
        try:
            file_path = await message.reply_to_message.download()
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            os.remove(file_path) # Cleanup
        except Exception as e:
            return await status_msg.edit(f"❌ **Read Error:** `{e}`")

    else:
        return await status_msg.edit("**⚠️ Usage:**\n1. `/paste <text>`\n2. Reply to text/file with `/paste`")

    if not content.strip():
        return await status_msg.edit("❌ **Content is empty!**")

    # 3. Uploading
    await status_msg.edit("☁️ **Uploading to Cloud...**")
    result = await universal_paste(content)

    if "error" in result:
        return await status_msg.edit(f"❌ **Failed:** {result['error']}")

    # 4. Result UI
    # Create clean inline buttons
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔗 View Paste", url=result['url']),
            InlineKeyboardButton("📄 Raw Data", url=result['raw'])
        ]
    ])
    
    text = (
        f"**✅ Paste Uploaded Successfully!**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔹 **Service:** `{result['service']}`\n"
        f"🔹 **Type:** `{'File' if is_file else 'Text'}`\n"
        f"🔹 **Size:** `{len(content)} chars`"
    )

    await status_msg.edit(text, reply_markup=buttons, disable_web_page_preview=True)
    
