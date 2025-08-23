import os
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

# --- Upload functions ---
def upload_envs(file_path):
    try:
        with open(file_path, 'rb') as f:
            response = requests.post("https://envs.sh", files={'file': f})
        if response.status_code == 200:
            return response.text.strip()
        return None
    except Exception as e:
        print(f"Envsh error: {e}")
        return None

def upload_catbox(file_path):
    try:
        with open(file_path, 'rb') as f:
            data = {'reqtype': 'fileupload'}
            response = requests.post("https://catbox.moe/user/api.php", files={'fileToUpload': f}, data=data)
        if response.status_code == 200:
            return response.text.strip()
        return None
    except Exception as e:
        print(f"Catbox error: {e}")
        return None

# --- Dictionary to store temporary media per user for /telegraph ---
user_media = {}

# --- /telegraph command (interactive choice, old style preserved) ---
@Client.on_message(filters.command("telegraph") & filters.private)
async def telegraph_command(bot, message: Message):
    t_msg = await bot.ask(
        chat_id=message.from_user.id,
        text="**Send your photo or video (under 5MB) to get a media link 🖇️**"
    )
    
    if not t_msg.media:
        return await message.reply_text("**Only media supported 😄**")
    
    path = await t_msg.download()
    user_media[message.from_user.id] = path

    # Ask user which service to upload
    await message.reply_text(
        "Choose the upload service:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("envs.sh", callback_data="upload_envs")],
            [InlineKeyboardButton("Catbox.moe", callback_data="upload_catbox")]
        ])
    )

# --- Callback for /telegraph service selection ---
@Client.on_callback_query()
async def service_callback(bot, callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_media:
        return await callback.answer("No media found. Please send a file first.", show_alert=True)

    path = user_media[user_id]
    uploading_msg = await callback.message.edit_text("<b><i>Uploading now 📤 ...</i></b>")

    if callback.data == "upload_envs":
        file_url = upload_envs(path)
    else:
        file_url = upload_catbox(path)

    if not file_url:
        return await uploading_msg.edit_text("**Failed to upload file 💢**")

    await uploading_msg.edit_text(
        text=f"<b><blockquote>‣ 𝐘𝐎𝐔𝐑 𝐋𝐈𝐍𝐊 </b></blockquote>\n\n<code>{file_url}</code>",
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Oᴘᴇɴ Lɪɴᴋ 🔓", url=file_url),
                InlineKeyboardButton("Sʜᴀʀᴇ Lɪɴᴋ 🖇️", url=f"https://telegram.me/share/url?url={file_url}")
            ],
            [InlineKeyboardButton("❌ Cʟᴏsᴇ ❌", callback_data="close")]
        ])
    )

    # Cleanup
    del user_media[user_id]
    os.remove(path)

# --- /catbox command (direct upload, independent) ---
@Client.on_message(filters.command("catbox") & filters.private)
async def catbox_upload(bot, message: Message):
    t_msg = await bot.ask(
        chat_id=message.from_user.id,
        text="**Send your photo or video (under 200MB) to upload on Catbox.moe 🖇️**"
    )

    if not t_msg.media:
        return await message.reply_text("**Only media supported 😄**")

    path = await t_msg.download()
    uploading_msg = await message.reply_text("<b><i>Uploading to Catbox.moe 📤 ...</i></b>")

    file_url = upload_catbox(path)
    if not file_url:
        return await uploading_msg.edit_text("**Failed to upload file 💢**")

    await uploading_msg.edit_text(
        text=f"<b><blockquote>‣ 𝐘𝐎𝐔𝐑 𝐂𝐚𝐭𝐛𝐨𝐱 𝐋𝐈𝐍𝐊 </b></blockquote>\n\n<code>{file_url}</code>",
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Oᴘᴇɴ Lɪɴᴋ 🔓", url=file_url),
                InlineKeyboardButton("Sʜᴀʀᴇ Lɪɴᴋ 🖇️", url=f"https://telegram.me/share/url?url={file_url}")
            ],
            [InlineKeyboardButton("❌ Cʟᴏsᴇ ❌", callback_data="close")]
        ])
    )

    os.remove(path)

# --- Optional close button handler ---
@Client.on_callback_query(filters.regex("close"))
async def close_callback(bot, callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()
