import os
import requests
import aiohttp
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from info import LOG_CHANNEL, ADMINS, DATABASE_NAME, DATABASE_URI  # import DB vars

from motor.motor_asyncio import AsyncIOMotorClient

# -------------------
# Constants
# -------------------
MAX_SIZE = 200 * 1024 * 1024  # Local max file size 200 MB
CATBOX_API = "https://catbox.moe/user/api.php"
ENVS_UPLOAD_URL = "https://envs.sh"
LINKS_PER_PAGE = 15

# Track active uploads per user
active_uploads = {}

# -------------------
# MongoDB Setup
# -------------------
mongo_client = AsyncIOMotorClient(DATABASE_URI)
db = mongo_client[DATABASE_NAME]
telelist_col = db["telelist"]

# -------------------
# Helpers
# -------------------
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
        print(f"Error Uploading to Envs:\n{e}")
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
        print(f"Error Uploading to Catbox:\n{e}")
        return None

# -------------------
# /telegraph command
# -------------------
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
             InlineKeyboardButton("Cᴀᴛʙᴏx 📦", callback_data="telegraph_catbox")]
        ]
    )
    await message.reply_text(
        "**__Choose The Site To Upload Your File__**",
        reply_markup=keyboard
    )

# -------------------
# Callback handler for /telegraph buttons
# -------------------
@Client.on_callback_query(filters.regex(r"^telegraph_"))
async def telegraph_callback(bot: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if user_id in active_uploads:
        return await query.answer("Finish or Cancel your Current Upload First.", show_alert=True)

    site = query.data.split("_")[1]  # envs or catbox
    active_uploads[user_id] = {"site": site, "message": query.message}

    await query.answer()
    await query.message.edit_text("**__Now Send me your File (Photo, Video, Document, Audio)\n\n/tcancel to Abort the Process__**")

    # 30-second timeout for inactivity
    await asyncio.sleep(30)
    if user_id in active_uploads and "file_sent" not in active_uploads[user_id]:
        active_uploads.pop(user_id, None)
        timeout_msg = await query.message.edit_text(
            "**⏰ Time's Up !!\nYou did not Send any File in 30 sec.**\n"
            "**Start a New Upload /telegraph**"
        )
        await asyncio.sleep(20)
        try:
            await timeout_msg.delete()
        except:
            pass

# -------------------
# File handler
# -------------------
@Client.on_message(filters.private & (filters.document | filters.photo | filters.video | filters.audio))
async def telegraph_file_handler(bot: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in active_uploads:
        return

    active_uploads[user_id]["file_sent"] = True
    site = active_uploads[user_id]["site"]

    status_msg = await message.reply_text("**__Downloading Your File...__ ⬇️**")
    file_path = await message.download()

    if site == "catbox" and os.path.getsize(file_path) > MAX_SIZE:
        await status_msg.edit_text(f"**❌ File Too Large (>{MAX_SIZE/1024/1024} MB).\n\nUpload Canceled ❌**")
        os.remove(file_path)
        active_uploads.pop(user_id)
        return

    await status_msg.edit_text("**__Uploading Now...__ ⬆️**")

    try:
        link = upload_to_envs(file_path) if site == "envs" else await upload_to_catbox(file_path)
        if not link:
            await status_msg.edit_text("**❌ Upload Failed 🥲**")
            return

        # Save to DB with date + site
        site_name = "Catbox" if "catbox.moe" in link else "Envs"
        await telelist_col.insert_one({"link": link, "site": site_name, "date": format_date()})

        # Log to channel
        try:
            caption_text = (
                f"**🛜 New Upload Detected**\n\n"
                f"**👤 User : {message.from_user.mention} (`{user_id}`)**\n"
                f"**🆔 Username : @{message.from_user.username if message.from_user.username else 'N/A'}**\n"
                f"**▶️ Link :** {link}"
            )
            await bot.send_message(LOG_CHANNEL, caption_text, disable_web_page_preview=True)
        except Exception as e:
            print(f"Failed to Log Upload: {e}")

        # Send link to user
        await status_msg.edit_text(
            text=f"**✅ Upload Completed !!\n\nYour Link 🖇️\n{link}**",
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("Oᴘᴇɴ 👀", url=link),
                        InlineKeyboardButton("Cʟᴏsᴇ ❌", callback_data="close")
                    ]
                ]
            )
        )
    except Exception as e:
        await status_msg.edit_text(f"**❌ Upload Failed :\n`{e}`**")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        active_uploads.pop(user_id, None)

# -------------------
# Close button handler
# -------------------
@Client.on_callback_query(filters.regex(r"^close$"))
async def close_callback(bot: Client, query: CallbackQuery):
    try:
        await query.message.delete()
        await query.answer("Message closed ❌", show_alert=False)
    except Exception as e:
        await query.answer(f"Failed to close: {e}", show_alert=True)

# -------------------
# /tcancel command
# -------------------
@Client.on_message(filters.command("tcancel") & filters.private)
async def telegraph_cancel(bot: Client, message: Message):
    user_id = message.from_user.id
    if user_id in active_uploads:
        active_uploads.pop(user_id)
        await message.reply_text("**❌ Upload Canceled Successfully 🤧**")
    else:
        await message.reply_text("**🤷 No Active Uploads. Use /telegraph to Start.**")

# -------------------
# /telegraphhelp
# -------------------
@Client.on_message(filters.command("telegraphhelp") & filters.private)
async def telegraph_help(bot: Client, message: Message):
    help_text = (
        "**🛠️ 𝐓𝐄𝐋𝐄𝐆𝐑𝐀𝐏𝐇 𝐏𝐋𝐔𝐆𝐈𝐍**\n\n"
        "1️⃣ /telegraph - Start a New Upload Session.\n"
        "- Choose the Site.\n"
        "- Send File (Photo, Video, Document, Audio).\n\n"
        "2️⃣ /tcancel - Cancel Current Upload Session.\n\n"
        "3️⃣ /telegraphhelp - Show this Help.\n\n"
        "📌 Features:\n"
        "- Tracks Active Uploads per User.\n"
        "- Catbox Size Limit: 200 MB.\n\n"
        "🔥 Powered By @NeonFiles 🔥"
    )
    await message.reply_text(help_text)

# -------------------
# /telelist command (Admin only with pagination)
# -------------------
@Client.on_message(filters.command("telelist") & filters.private)
async def telegraph_list(bot: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        return await message.reply_text("**- You Are Not Authorized 😁❌**")

    await send_telelist_page(bot, message.chat.id, 0)

async def send_telelist_page(bot: Client, chat_id: int, page: int):
    cursor = telelist_col.find({})
    docs = [doc async for doc in cursor]

    if not docs:
        return await bot.send_message(chat_id, "**📂 No Uploads Found Yet !!**")

    start = page * LINKS_PER_PAGE
    end = start + LINKS_PER_PAGE
    page_docs = docs[start:end]

    formatted_list = "\n\n".join([
        f"{start+idx+1:02d}. {doc.get('date', format_date())} | {doc.get('site', 'Unknown')}\n{doc['link']}"
        for idx, doc in enumerate(page_docs)
    ])

    keyboard = []
    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton("⬅️ Pʀᴇᴠ", callback_data=f"telelist_prev_{page-1}"))
    if end < len(docs):
        buttons.append(InlineKeyboardButton("Nᴇxᴛ ➡️", callback_data=f"telelist_next_{page+1}"))
    if buttons:
        keyboard.append(buttons)

    await bot.send_message(
        chat_id,
        f"**📝 Uploaded Links (Page {page+1})**\n\n{formatted_list}",
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
    )

# -------------------
# Callback handler for pagination
# -------------------
@Client.on_callback_query(filters.regex(r"^telelist_(prev|next)_"))
async def telelist_page_callback(bot: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if user_id not in ADMINS:
        return await query.answer("❌ Not Authorized", show_alert=True)

    action, page = query.data.split("_")[1], int(query.data.split("_")[2])

    await query.message.delete()
    await send_telelist_page(bot, query.message.chat.id, page)


# Dont remove Credits
# Developer Telegram @MyselfNeon
# Update channel - @NeonFiles
