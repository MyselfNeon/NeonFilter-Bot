
import os
import requests
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

def upload_image_requests(image_path):
    upload_url = "https://envs.sh"

    try:
        with open(image_path, 'rb') as file:
            files = {'file': file} 
            response = requests.post(upload_url, files=files)

            if response.status_code == 200:
                return response.text.strip() 
            else:
                return print(f"Upload failed with status code {response.status_code}")

    except Exception as e:
        print(f"Error during upload: {e}")
        return None

@Client.on_message(filters.command("telegraph") & filters.private)
async def telegraph_upload(bot, update):
    t_msg = await bot.ask(chat_id = update.from_user.id, text = "**__Now Send Me Your Photo Or Video Under 5MB To Get Media Link 🖇️__**")
    if not t_msg.media:
        return await update.reply_text("**__Only Media Supported 😄__**")
    path = await t_msg.download()
    uploading_message = await update.reply_text("<b><i>Uploading now 📤 ...</i></b>")
    try:
        image_url = upload_image_requests(path)
        if not image_url:
            return await uploading_message.edit_text("**__Failed to upload file 💢__**")
    except Exception as error:
        await uploading_message.edit_text(f"**__Upload failed: {error}__**")
        return
    await uploading_message.edit_text(
        text=f"<b><blockquote>‣ 𝐘𝐎𝐔𝐑 𝐋𝐈𝐍𝐊 </b></blockquote>\n\n<code>{image_url}</code>",
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup( [[
            InlineKeyboardButton(text="Oᴘᴇɴ Lɪɴᴋ 🔓", url=image_url),
            InlineKeyboardButton(text="Sʜᴀʀᴇ Lɪɴᴋ 🖇️", url=f"https://telegram.me/share/url?url={image_url}")
            ],[
            InlineKeyboardButton(text="❌ Cʟᴏsᴇ ❌", callback_data="close")
            ]])
        )
    
