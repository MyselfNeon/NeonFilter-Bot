import os
import requests
import aiohttp
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

CATBOX_API = "https://catbox.moe/user/api.php"
MAX_SIZE = 200 * 1024 * 1024  # 200 MB
ENVS_UPLOAD_URL = "https://envs.sh"
ZEROX0_URL = "https://0x0.st"

# Track active uploads per user (only for /telegraph)
active_uploads = {}

# -------------------
# Helper functions
# -------------------

def upload_to_envs(file_path: str):
    try:
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(ENVS_UPLOAD_URL, files=files)
            if response.status_code == 200:
                return response.text.strip()
            return None
    except Exception as e:
        print(f"**__Error Uploading to Envs :\n{e}__**")
        return None

async def upload_to_catbox(file_path: str):
    async with aiohttp.ClientSession() as session:
        with open(file_path, "rb") as f:
            data = aiohttp.FormData()
            data.add_field("reqtype", "fileupload")
            data.add_field("fileToUpload", f, filename=os.path.basename(file_path))
            async with session.post(CATBOX_API, data=data) as resp:
                return await resp.text()

async def upload_to_0x0(file_path: str):
    try:
        async with aiohttp.ClientSession() as session:
            with open(file_path, "rb") as f:
                data = {"file": f}
                async with session.post(ZEROX0_URL, data=data) as resp:
                    return (await resp.text()).strip()
    except Exception as e:
        print(f"**__Error Uploading to 0x0.st :\n{e}__**")
        return None

# -------------------
# /telegraph command
# -------------------

@Client.on_message(filters.command("telegraph") & filters.private)
async def telegraph_start(bot: Client, message: Message):
    user_id = message.from_user.id

    if user_id in active_uploads:
        return await message.reply_text("**__You Already have an Active Upload.\nFinish or Cancel it with /tcancel__**")

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Eɴᴠs.sʜ 🌐", callback_data="telegraph_envs")],
            [InlineKeyboardButton("Cᴀᴛʙᴏx 📦", callback_data="telegraph_catbox")],
            [InlineKeyboardButton("0x0.sᴛ ⚡", callback_data="telegraph_0x0")],
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

    site = query.data.split("_")[1]  # envs, catbox, or 0x0
    active_uploads[user_id] = {"site": site, "message": query.message}

    await query.answer()
    await query.message.edit_text("**__Now Send me your File (Photo, Video, Document, Audio)\n\n/tcancel to Abort the Process__**")

# -------------------
# File handler scoped to active /telegraph users
# -------------------

@Client.on_message(filters.private & (filters.document | filters.photo | filters.video | filters.audio))
async def telegraph_file_handler(bot: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in active_uploads:
        return  # Ignore files not related to /telegraph

    site = active_uploads[user_id]["site"]
    status_msg = await message.reply_text("**__Downloading Your File...__ ⬇️**")
    file_path = await message.download()

    if site == "catbox" and os.path.getsize(file_path) > MAX_SIZE:
        await status_msg.edit_text(f"**❌ __File Too Large (>{MAX_SIZE/1024/1024} MB).\n\nUpload Canceled__ ❌**")
        os.remove(file_path)
        active_uploads.pop(user_id)
        return

    await status_msg.edit_text("**__Uploading Now...__ ⬆️**")

    try:
        if site == "envs":
            link = upload_to_envs(file_path)
        elif site == "catbox":
            link = await upload_to_catbox(file_path)
        elif site == "0x0":
            link = await upload_to_0x0(file_path)
        else:
            link = None

        if not link:
            await status_msg.edit_text("**❌ __Upload Failed__ 🥲**")
            return

        await status_msg.edit_text(
            text=f"**✅ __Upload Completed !!\n\nYour Link 🖇️\n{link}__**",
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("Oᴘᴇɴ Lɪɴᴋ 🔓", url=link),
                        InlineKeyboardButton("Sʜᴀʀᴇ Lɪɴᴋ 🖇️", url=f"https://telegram.me/share/url?url={link}")
                    ],
                    [InlineKeyboardButton("❌ Cᴀɴᴄᴇʟ ❌", callback_data="close")]
                ]
            )
        )
    except Exception as e:
        await status_msg.edit_text(f"**❌ __Upload Failed :\n`{e}`__**")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        active_uploads.pop(user_id, None)

# -------------------
# /cancel command
# -------------------

@Client.on_message(filters.command("tcancel") & filters.private)
async def telegraph_cancel(bot: Client, message: Message):
    user_id = message.from_user.id
    if user_id in active_uploads:
        active_uploads.pop(user_id)
        await message.reply_text("**❌ __Upload Canceled Successfully__ 🤧**")
    else:
        await message.reply_text("**🤷 __There Are No Active Uploads to Cancel At The Use /telegraph to Create an Upload__**")
        

# Dont remove Credits
# Developer Telegram @MyselfNeon
# Update channel - @NeonFiles
