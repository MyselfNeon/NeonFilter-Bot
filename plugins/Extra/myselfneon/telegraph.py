# ---------------------------------------------------
# File Name: Telegraph.py
# Author: MyselfNeon
# Original Repo: https://github.com/MyselfNeon/NeonFilter-Bot
# GitHub: https://github.com/MyselfNeon/
# Telegram: https://t.me/MyelfNeon
# ---------------------------------------------------

import os
import requests
import aiohttp
import asyncio
from datetime import datetime
from telegraph import Telegraph  # New Import
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from info import LOG_CHANNEL, ADMINS, DATABASE_NAME, DATABASE_URI

from motor.motor_asyncio import AsyncIOMotorClient

# --- Constants ---
MAX_SIZE = 200 * 1024 * 1024  # Local max file size 200 MB
CATBOX_API = "https://catbox.moe/user/api.php"
ENVS_UPLOAD_URL = "https://envs.sh"
LINKS_PER_PAGE = 10

# Initialize Telegraph Client
telegraph_client = Telegraph()
try:
    telegraph_client.create_account(short_name='NeonFiles')
except Exception:
    pass # Account might already exist locally

# Track active uploads per user
active_uploads = {}

# --- MongoDB Setup ---
mongo_client = AsyncIOMotorClient(DATABASE_URI)
db = mongo_client[DATABASE_NAME]
telelist_col = db["telelist"]

# --- Helpers ---
def format_date():
    return datetime.now().strftime("%d %B 2K%y")

def upload_to_envs(file_path: str):
    try:
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(ENVS_UPLOAD_URL, files=files, timeout=60)
            if response.status_code == 200:
                return response.text.strip()
            return None
    except Exception as e:
        print(f"**__Error Uploading to Envs:\n{e}__**")
        return None

async def upload_to_catbox(file_path: str):
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
            with open(file_path, "rb") as f:
                data = aiohttp.FormData()
                data.add_field("reqtype", "fileupload")
                data.add_field("fileToUpload", f, filename=os.path.basename(file_path))
                async with session.post(CATBOX_API, data=data) as resp:
                    return await resp.text()
    except Exception as e:
        print(f"**__Error Uploading to Catbox:\n{e}__**")
        return None

def upload_text_to_graph(text_content):
    try:
        title = "Neon Telegraph"
        content = text_content

        # Check for custom title syntax: "Title: My Title"
        if text_content.startswith("Title:") or text_content.startswith("title:"):
            lines = text_content.split("\n", 1)
            if len(lines) > 1:
                # Extract title and remove "Title:" prefix
                possible_title = lines[0].split(":", 1)[1].strip()
                if possible_title:
                    title = possible_title
                    content = lines[1]
        
        # Convert newlines to HTML line breaks for Telegraph
        html_content = content.replace("\n", "<br>")

        response = telegraph_client.create_page(
            title=title,
            html_content=html_content
        )
        return response['url']
    except Exception as e:
        print(f"**__Error Uploading to Graph:\n{e}__**")
        return None

# --- /telegraph command ---
@Client.on_message(filters.command("telegraph") & filters.private)
async def telegraph_start(bot: Client, message: Message):
    user_id = message.from_user.id

    if user_id in active_uploads:
        return await message.reply_text(
            "**__You Already have an Active Upload.\nFinish or Cancel it with /tcancel__**"
        )

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Eɴᴠs.sʜ 🌐", callback_data="telegraph_envs"),
             InlineKeyboardButton("Cᴀᴛʙᴏx 📦", callback_data="telegraph_catbox")],
            [InlineKeyboardButton("Gʀᴀᴘʜ.ᴏʀɢ 📝", callback_data="telegraph_graph")]
        ]
    )
    await message.reply_text(
        "**__Choose The Destination__**",
        reply_markup=keyboard
    )

# --- Callback handler for /telegraph buttons ---
@Client.on_callback_query(filters.regex(r"^telegraph_"))
async def telegraph_callback(bot: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if user_id in active_uploads:
        return await query.answer("Finish or Cancel your Current Upload First.", show_alert=True)

    site = query.data.split("_")[1]  # envs, catbox, or graph
    active_uploads[user_id] = {"site": site, "message": query.message}

    await query.answer()
    
    if site == "graph":
        msg_text = (
            "**__Send me your Text Content.__** 📝\n\n"
            "**📌 Hint:** To set a custom title, start your message with:\n"
            "`Title: Your Custom Title`\n\n"
            "__/tcancel to Abort__"
        )
    else:
        msg_text = "**__Now Send me your File (Photo, Video, Document, Audio)\n\n/tcancel to Abort the Process__**"

    await query.message.edit_text(msg_text)

    # 30-second timeout for inactivity
    await asyncio.sleep(60) # Increased to 60s for typing text
    if user_id in active_uploads and "received" not in active_uploads[user_id]:
        active_uploads.pop(user_id, None)
        timeout_msg = await query.message.edit_text(
            "**⏰ __Time's Up !!\n\nYou did not Send anything in 60 Sec.__**\n"
            "**__Start a New Upload /telegraph__**"
        )
        await asyncio.sleep(20)
        try:
            await timeout_msg.delete()
        except:
            pass

# --- Text Handler (For Graph.org) ---
@Client.on_message(filters.private & filters.text & ~filters.command(["telegraph", "tcancel", "telegraphhelp", "telelist"]))
async def telegraph_text_handler(bot: Client, message: Message):
    user_id = message.from_user.id
    
    if user_id not in active_uploads:
        return

    data = active_uploads[user_id]
    if data["site"] != "graph":
        return await message.reply_text("**__⚠️ Please send a File, not Text.__**")

    active_uploads[user_id]["received"] = True
    status_msg = await message.reply_text("**__Publishing to Graph.org ...__ 📝**")

    try:
        link = await asyncio.to_thread(upload_text_to_graph, message.text)
        
        if not link:
            await status_msg.edit_text("**❌ __Publish Failed__ 🥲**")
            active_uploads.pop(user_id, None)
            return

        # Save to DB
        await telelist_col.insert_one({"link": link, "site": "Graph.org", "date": format_date()})

        # Log To Channel
        try:
            caption_text = (
                f"**📝 __New Telegraph Page__**\n\n"
                f"**👤 __User : {message.from_user.mention} (`{user_id}`)__**\n"
                f"**🆔 __Username : @{message.from_user.username if message.from_user.username else 'N/A'}__**\n"
                f"**▶️ __Generated Link 🖇️\n {link}__**"
            )
            await bot.send_message(LOG_CHANNEL, caption_text, disable_web_page_preview=True)
        except Exception:
            pass

        await status_msg.edit_text(
            text=f"**✅ __Published Successfully !!\n\nYour Link 🖇️\n{link}__**",
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Oᴘᴇɴ 👀", url=link), InlineKeyboardButton("Cʟᴏsᴇ ❌", callback_data="close")]]
            )
        )

    except Exception as e:
        await status_msg.edit_text(f"**❌ __Error :\n`{e}`__**")
    finally:
        active_uploads.pop(user_id, None)

# ---- File handler (For Media) ---
@Client.on_message(filters.private & (filters.document | filters.photo | filters.video | filters.audio))
async def telegraph_file_handler(bot: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in active_uploads:
        return

    data = active_uploads[user_id]
    site = data["site"]

    if site == "graph":
        return await message.reply_text("**__⚠️ Please send Text for Graph.org, not a File.__**")

    active_uploads[user_id]["received"] = True

    status_msg = await message.reply_text("**__Downloading Your File ...__ ⚡⬇️**")
    file_path = await message.download()

    if site == "catbox" and os.path.getsize(file_path) > MAX_SIZE:
        await status_msg.edit_text(f"**❌ File Too Large (>{MAX_SIZE/1024/1024} MB).\n\nUpload Canceled ❌**")
        os.remove(file_path)
        active_uploads.pop(user_id)
        return

    await status_msg.edit_text("**__Uploading Now ...__ 🚀⬆️**")

    try:
        link = upload_to_envs(file_path) if site == "envs" else await upload_to_catbox(file_path)
        if not link:
            await status_msg.edit_text("**❌ __Upload Failed__ 🥲**")
            return

        # Save to DB with date + site
        site_name = "Catbox" if "catbox.moe" in link else "Envs"
        await telelist_col.insert_one({"link": link, "site": site_name, "date": format_date()})

        # Log To Channel
        try:
            caption_text = (
                f"**🛜 __New Upload Detected__**\n\n"
                f"**👤 __User : {message.from_user.mention} (`{user_id}`)__**\n"
                f"**🆔 __Username : @{message.from_user.username if message.from_user.username else 'N/A'}__**\n"
                f"**▶️ __Generated Link 🖇️\n {link}__**"
            )
            await bot.send_message(LOG_CHANNEL, caption_text, disable_web_page_preview=True)
        except Exception:
            pass

        # Send link to user
        await status_msg.edit_text(
            text=f"**✅ __Upload Completed !!\n\nYour Link 🖇️\n{link}__**",
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Oᴘᴇɴ 👀", url=link), InlineKeyboardButton("Cʟᴏsᴇ ❌", callback_data="close")]]
            )
        )
    except Exception as e:
        await status_msg.edit_text(f"**❌ __Upload Failed :\n`{e}`__**")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        active_uploads.pop(user_id, None)

# --- Close button handler ---
@Client.on_callback_query(filters.regex(r"^close$"))
async def close_callback(bot: Client, query: CallbackQuery):
    try:
        await query.message.delete()
        await query.answer("Message Closed ❌", show_alert=False)
    except Exception as e:
        await query.answer(f"Failed to Close: {e}", show_alert=True)

# --- /tcancel command ---
@Client.on_message(filters.command("tcancel") & filters.private)
async def telegraph_cancel(bot: Client, message: Message):
    user_id = message.from_user.id
    if user_id in active_uploads:
        active_uploads.pop(user_id)
        await message.reply_text("**❌ __Upload Canceled Successfully__ 🤧**")
    else:
        await message.reply_text("**🤷 __No Active Uploads. Use /telegraph to Start__.**")

# --- /telegraphhelp ---
@Client.on_message(filters.command("telegraphhelp") & filters.private)
async def telegraph_help(bot: Client, message: Message):
    help_text = (
        "<blockquote>**🛠️ 𝐓𝐄𝐋𝐄𝐆𝐑𝐀𝐏𝐇 𝐏𝐋𝐔𝐆𝐈𝐍**</blockquote>\n\n"
        "1️⃣ __/telegraph \n- **Start a New Upload Session.__**\n"
        "**__- Choose Envs/Catbox for Files, or Graph.org for Text.__**\n"
        "**__- Text Mode: Start message with 'Title: X' to set a custom title.__**\n\n"
        "2️⃣ __/tcancel \n- **Cancel An Active Upload Session.__**\n"
        "**__- Use This If You Made A Mistake Or Changed Your Mind.__**\n\n"
        "3️⃣ __/telegraphhelp \n- **Show This Help Message.__**\n\n"
        "**📌 __Additional Features:__**\n"
        "**- __Active Uploads Are Tracked Per User.__**\n"
        "**- __File Size Limit For Catbox: 200 MB.__\n\n🔥 __Powered By @NeonFiles__ 🔥**\n"
    )
    await message.reply_text(help_text)

# /telelist command (Admin only with pagination)
@Client.on_message(filters.command("telelist") & filters.private)
async def telegraph_list(bot: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        return await message.reply_text("**- __You Are Not Authorized__ ❌**")

    await send_telelist_page(bot, message.chat.id, 0, new_msg=True)

async def send_telelist_page(bot: Client, chat_id: int, page: int, new_msg: bool = False, query: CallbackQuery = None):
    cursor = telelist_col.find({})
    docs = [doc async for doc in cursor]

    if not docs:
        if new_msg:
            return await bot.send_message(chat_id, "**📂 __No Uploads Found Yet !!__**")
        else:
            return await query.message.edit_text("**📂 __No Uploads Found Yet !!__**")

    total_pages = (len(docs) + LINKS_PER_PAGE - 1) // LINKS_PER_PAGE
    start = page * LINKS_PER_PAGE
    end = start + LINKS_PER_PAGE
    page_docs = docs[start:end]

    formatted_list = "\n\n".join([
        f"{start+idx+1:02d}. {doc.get('date', format_date())} | {doc.get('site', 'Unknown')}\n{doc['link']}"
        for idx, doc in enumerate(page_docs)
    ])

    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton("⬅️ Pʀᴇᴠ", callback_data=f"telelist_prev_{page-1}"))

    buttons.append(InlineKeyboardButton(f"📄 Pᴀɢᴇ {page+1}/{total_pages}", callback_data="telelist_ignore"))

    if end < len(docs):
        buttons.append(InlineKeyboardButton("Nᴇxᴛ ➡️", callback_data=f"telelist_next_{page+1}"))

    keyboard = InlineKeyboardMarkup([buttons])

    text = f"**📝 __Uploaded Links (Page {page+1}/{total_pages}) 🖇️\n\n{formatted_list}__**"

    if new_msg:
        await bot.send_message(chat_id, text, disable_web_page_preview=True, reply_markup=keyboard)
    else:
        await query.message.edit_text(text, disable_web_page_preview=True, reply_markup=keyboard)

@Client.on_callback_query(filters.regex(r"^telelist_(prev|next)_"))
async def telelist_page_callback(bot: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if user_id not in ADMINS:
        return await query.answer("❌ Not Authorized", show_alert=True)
    action, page = query.data.split("_")[1], int(query.data.split("_")[2])
    await send_telelist_page(bot, query.message.chat.id, page, new_msg=False, query=query)

@Client.on_callback_query(filters.regex(r"^telelist_ignore$"))
async def telelist_ignore_callback(bot: Client, query: CallbackQuery):
    pass 

# MyselfNeon
# Don't Remove Credit 🥺
# Telegram Channel @NeonFiles
