# ---------------------------------------------------
# File Name: Telegraph-V2.py
# Author: MyselfNeon
# Original Repo: https://github.com/MyselfNeon/NeonFilter-Bot
# GitHub: https://github.com/MyselfNeon/
# Telegram: https://t.me/MyelfNeon
# ---------------------------------------------------

import os
import aiohttp
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from info import LOG_CHANNEL, ADMINS, DATABASE_NAME, DATABASE_URI, IMGBB_API_KEY

from motor.motor_asyncio import AsyncIOMotorClient

# --- Constants ---
MAX_SIZE = 200 * 1024 * 1024  # 200 MB
CATBOX_API = "https://catbox.moe/user/api.php"
IMGBB_API_URL = "https://api.imgbb.com/1/upload"
LINKS_PER_PAGE = 10
TIMEOUT_SECONDS = 60  # Auto timecut

# --- Global State ---
# Stores: user_id -> {'site': str, 'status': str, 'task': asyncio.Task, 'message': Message}
active_tasks = {}

# --- MongoDB Setup ---
mongo_client = AsyncIOMotorClient(DATABASE_URI)
db = mongo_client[DATABASE_NAME]
telelist_col = db["telelist"]

# --- Helpers ---
def format_date():
    return datetime.now().strftime("%d %B 2K%y")

async def upload_to_imgbb(file_path: str):
    if not IMGBB_API_KEY:
        return None
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
            with open(file_path, "rb") as f:
                data = aiohttp.FormData()
                data.add_field("image", f, filename=os.path.basename(file_path))
                async with session.post(IMGBB_API_URL, params={"key": IMGBB_API_KEY}, data=data) as resp:
                    if resp.status == 200:
                        res_json = await resp.json()
                        return res_json["data"]["url"]
                    return None
    except Exception as e:
        print(f"ImgBB Error: {e}")
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
        print(f"Catbox Error: {e}")
        return None

# --- /telegraph command ---
@Client.on_message(filters.command("telegraph") & filters.private)
async def telegraph_start(bot: Client, message: Message):
    user_id = message.from_user.id

    if user_id in active_tasks:
        return await message.reply_text(
            "**⚠️ __You already have a task running!__**\n"
            "__Use **/tcancel** to stop the current task first.__"
        )

    buttons = []
    if IMGBB_API_KEY:
        buttons.append([
            InlineKeyboardButton("IᴍɢBB 📸", callback_data="telegraph_imgbb"),
            InlineKeyboardButton("Cᴀᴛʙᴏx 📦", callback_data="telegraph_catbox")
        ])
        text = "**__Choose The Site To Upload Your File__**"
    else:
        buttons.append([InlineKeyboardButton("Cᴀᴛʙᴏx 📦", callback_data="telegraph_catbox")])
        text = "**__Choose The Site To Upload Your File__**\n⚠️ `IMGBB_API_KEY` missing."

    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

# --- Callback: Mode Selection ---
@Client.on_callback_query(filters.regex(r"^telegraph_"))
async def telegraph_callback(bot: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if user_id in active_tasks:
        return await query.answer("Use /tcancel to stop current task!", show_alert=True)

    site = query.data.split("_")[1]
    
    # Store 'waiting' state with reference to the prompt message
    active_tasks[user_id] = {"site": site, "status": "waiting", "message": query.message}
    
    await query.answer()
    
    try:
        await query.message.edit_text(
            f"**__Selected: {site.capitalize()}__**\n\n"
            "**__👇 Send me your file now.__**\n"
            f"**__⏱️ You have {TIMEOUT_SECONDS} seconds.__**\n\n"
            "__**/tcancel** to Cancel__"
        )
    except Exception:
        pass 

    # 60s Timeout for sending file
    await asyncio.sleep(TIMEOUT_SECONDS)
    
    # Check if user is still in 'waiting' state (didn't send file)
    if user_id in active_tasks and active_tasks[user_id].get("status") == "waiting":
        # Remove user from active tasks
        del active_tasks[user_id]
        
        # EDIT the original message to say Time's Up
        try:
            await query.message.edit_text(
                "**__⏰ Time's Up! No file received.__**\n"
                "__Use /telegraph to start again.__"
            )
        except Exception as e:
            print(f"Timeout Edit Error: {e}")

# --- Core Process: Download & Upload ---
async def process_media(bot, message, site):
    user_id = message.from_user.id
    status_msg = await message.reply_text("**__Downloading...__ ⬇️**")
    
    # Update global state with the status message object
    if user_id in active_tasks:
        active_tasks[user_id]["message"] = status_msg

    file_path = None
    try:
        # 1. Download
        file_path = await message.download()

        if not file_path:
            raise Exception("Download failed.")

        # Check Size for Catbox
        if site == "catbox" and os.path.getsize(file_path) > MAX_SIZE:
            await status_msg.edit_text("**❌ File Too Large (>200MB).**")
            return

        # 2. Upload
        await status_msg.edit_text("**__Uploading...__ 🚀**")
        
        link = await upload_to_imgbb(file_path) if site == "imgbb" else await upload_to_catbox(file_path)

        if not link:
            await status_msg.edit_text("**__❌ Upload Failed or API Error.__**")
            return

        # 3. Success
        site_name = "ImgBB" if site == "imgbb" else "Catbox"
        await telelist_col.insert_one({"link": link, "site": site_name, "date": format_date()})

        # Log
        try:
            log_text = (
                f"**__🛜 New Upload Detected__**\n"
                f"**__👤 User:** {message.from_user.mention} (`{user_id}`)__\n"
                f"**__🌐 Site:** {site_name}__\n"
                f"**__🖇️ Link:** {link}__"
            )
            await bot.send_message(LOG_CHANNEL, log_text, disable_web_page_preview=True)
        except:
            pass

        await status_msg.edit_text(
            text=f"**✅ __Upload Completed !!__**\n\n**🖇️ __Link : [Click Here]({link})__**\n`{link}`",
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Oᴘᴇɴ 👀", url=link), InlineKeyboardButton("Cʟᴏsᴇ ❌", callback_data="close")]
            ])
        )

    except asyncio.CancelledError:
        await status_msg.edit_text("**__❌ Process Cancelled.__**")
    except Exception as e:
        await status_msg.edit_text(f"**__❌ Error:** `{e}`__")
    finally:
        # Cleanup
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        active_tasks.pop(user_id, None)

# --- File Handler ---
@Client.on_message(filters.private & (filters.document | filters.photo | filters.video | filters.audio))
async def telegraph_file_handler(bot: Client, message: Message):
    user_id = message.from_user.id
    
    # Must be in 'waiting' state
    task_info = active_tasks.get(user_id)
    if not task_info or task_info.get("status") != "waiting":
        return

    site = task_info["site"]
    
    # Mark as running
    active_tasks[user_id]["status"] = "running"
    
    # Run the process as an asyncio Task to allow cancellation
    task = asyncio.create_task(process_media(bot, message, site))
    active_tasks[user_id]["task"] = task
    
    try:
        await task
    except asyncio.CancelledError:
        pass # Handled in process_media

# --- /tcancel command ---
@Client.on_message(filters.command("tcancel") & filters.private)
async def telegraph_cancel_command(bot: Client, message: Message):
    user_id = message.from_user.id
    task_info = active_tasks.get(user_id)

    if not task_info:
        return await message.reply_text("🤷 __No active upload session found.__")

    # If waiting for file
    if task_info["status"] == "waiting":
        # Edit the prompt message to say Cancelled
        try:
            if "message" in task_info:
                await task_info["message"].edit_text("**__❌ Session Cancelled.__**")
        except:
            pass
        del active_tasks[user_id]
        await message.reply_text("**❌ __Session Cancelled Successfully.__**")

    # If uploading/downloading
    elif task_info["status"] == "running":
        if "task" in task_info:
            task_info["task"].cancel()
        # The finally block in process_media will handle cleanup
        await message.reply_text("**❌ __Upload Process Cancelled.__**")

# --- Close Button Handler ---
@Client.on_callback_query(filters.regex(r"^close$"))
async def close_callback(bot: Client, query: CallbackQuery):
    try:
        await query.message.delete()
    except:
        pass

# --- /telelist command ---
@Client.on_message(filters.command("telelist") & filters.private)
async def telegraph_list(bot: Client, message: Message):
    if message.from_user.id not in ADMINS:
        return
    await send_telelist_page(bot, message.chat.id, 0, new_msg=True)

async def send_telelist_page(bot, chat_id, page, new_msg=False, query=None):
    cursor = telelist_col.find({})
    docs = [doc async for doc in cursor]
    
    if not docs:
        text = "**__📂 No Uploads Found.__**"
        if new_msg: await bot.send_message(chat_id, text)
        else: await query.message.edit_text(text)
        return

    total_pages = (len(docs) + LINKS_PER_PAGE - 1) // LINKS_PER_PAGE
    start = page * LINKS_PER_PAGE
    page_docs = docs[start : start + LINKS_PER_PAGE]

    formatted_list = "\n".join([
        f"{start+i+1}. {d.get('date')} | {d.get('site')}\n{d['link']}\n" 
        for i, d in enumerate(page_docs)
    ])
    
    buttons = []
    if page > 0: buttons.append(InlineKeyboardButton("⬅️", callback_data=f"telelist_prev_{page-1}"))
    buttons.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="telelist_ignore"))
    if start + LINKS_PER_PAGE < len(docs): buttons.append(InlineKeyboardButton("➡️", callback_data=f"telelist_next_{page+1}"))
    
    text = f"**📝 Upload History**\n\n{formatted_list}"
    markup = InlineKeyboardMarkup([buttons])
    
    if new_msg: await bot.send_message(chat_id, text, reply_markup=markup, disable_web_page_preview=True)
    else: await query.message.edit_text(text, reply_markup=markup, disable_web_page_preview=True)

@Client.on_callback_query(filters.regex(r"^telelist_(prev|next)_"))
async def telelist_page_cb(bot, query):
    if query.from_user.id not in ADMINS: return
    _, action, page = query.data.split("_")
    await send_telelist_page(bot, query.message.chat.id, int(page), False, query)

@Client.on_callback_query(filters.regex(r"^telelist_ignore$"))
async def telelist_ignore(bot, query):
    await query.answer()

# Dont remove Credits
# Developer Telegram @MyselfNeon
# Update channel - @NeonFiles
