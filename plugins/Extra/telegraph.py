import os
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

# --- Upload to envs.sh (original behavior) ---
def upload_envs(file_path):
    try:
        with open(file_path, 'rb') as f:
            response = requests.post("https://envs.sh", files={'file': f})
        if response.status_code == 200:
            return response.text.strip()
        else:
            print(f"Envsh upload failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"Envsh upload error: {e}")
        return None

# --- Upload to Catbox ---
def upload_catbox(file_path):
    try:
        with open(file_path, 'rb') as f:
            data = {'reqtype': 'fileupload'}
            response = requests.post("https://catbox.moe/user/api.php", files={'fileToUpload': f}, data=data)
        if response.status_code == 200:
            return response.text.strip()
        else:
            print(f"Catbox upload failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"Catbox upload error: {e}")
        return None

# --- /telegraph command (OLD style, envs.sh only) ---
@Client.on_message(filters.command("telegraph") & filters.private)
async def telegraph_upload(bot, message: Message):
    t_msg = await bot.ask(
        chat_id=message.from_user.id,
        text="**Send your photo or video (under 5MB) to get media link 🖇️**"
    )
    
    if not t_msg.media:
        return await message.reply_text("**Only media supported 😄**")
    
    path = await t_msg.download()
    uploading_msg = await message.reply_text("<b><i>Uploading now 📤 ...</i></b>")
    
    file_url = upload_envs(path)
    if not file_url:
        await uploading_msg.edit_text("**Failed to upload file 💢**")
        os.remove(path)
        return
    
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
    
    os.remove(path)

# --- /catbox command (NEW, direct Catbox upload) ---
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
