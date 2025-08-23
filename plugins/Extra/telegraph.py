import os
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

# --- Upload to envs.sh (old style) ---
def upload_envs(file_path):
    try:
        with open(file_path, 'rb') as f:
            response = requests.post("https://envs.sh", files={'file': f})
        return response.text.strip()  # returns the URL directly
    except Exception as e:
        print(f"Envsh upload error: {e}")
        return None

# --- Simple Catbox upload ---
def upload_catbox(file_path):
    try:
        with open(file_path, 'rb') as f:
            response = requests.post(
                "https://catbox.moe/user/api.php",
                files={'fileToUpload': f},
                data={'reqtype': 'fileupload'}
            )
        return response.text.strip()  # returns the URL directly
    except Exception as e:
        print(f"Catbox error: {e}")
        return None

# --- /telegraph command (old envs.sh style) ---
@Client.on_message(filters.command("telegraph") & filters.private)
async def telegraph_upload(bot, message: Message):
    t_msg = await bot.ask(
        chat_id=message.from_user.id,
        text="**Send your photo or video to get envs.sh link 🖇️**"
    )

    if not t_msg.media:
        return await message.reply_text("**Only media supported 😄**")

    path = await t_msg.download()
    uploading_msg = await message.reply_text("<b><i>Uploading to envs.sh 📤 ...</i></b>")

    file_url = upload_envs(path)
    if not file_url:
        await uploading_msg.edit_text("**Failed to upload file 💢**")
        os.remove(path)
        return

    await uploading_msg.edit_text(
        text=f"<b><blockquote>‣ 𝐘𝐎𝐔𝐑 𝐄𝐍𝐕𝐒 𝐋𝐈𝐍𝐊 </b></blockquote>\n\n<code>{file_url}</code>",
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

# --- /catbox command (simple Catbox uploader) ---
@Client.on_message(filters.command("catbox") & filters.private)
async def catbox_upload(bot, message: Message):
    t_msg = await bot.ask(
        chat_id=message.from_user.id,
        text="**Send your photo or video to upload on Catbox.moe 🖇️**"
    )

    if not t_msg.media:
        return await message.reply_text("**Only media supported 😄**")

    path = await t_msg.download()
    uploading_msg = await message.reply_text("<b><i>Uploading to Catbox.moe 📤 ...</i></b>")

    file_url = upload_catbox(path)
    if not file_url:
        await uploading_msg.edit_text("**Failed to upload file 💢**")
        os.remove(path)
        return

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

# --- Close button handler ---
@Client.on_callback_query(filters.regex("close"))
async def close_callback(bot, callback):
    await callback.message.delete()
    await callback.answer()
