import os
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

# ----------- UPLOAD FUNCTIONS ------------ #
def upload_envs(image_path):
    upload_url = "https://envs.sh"
    try:
        with open(image_path, 'rb') as file:
            files = {'file': file}
            response = requests.post(upload_url, files=files)
            if response.status_code == 200:
                return response.text.strip()
            else:
                return None
    except Exception as e:
        print(f"envs.sh upload error: {e}")
        return None

def upload_telegraph(image_path):
    upload_url = "https://telegra.ph/upload"
    try:
        with open(image_path, 'rb') as file:
            files = {"file": file}
            response = requests.post(upload_url, files=files)
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and "src" in result[0]:
                    return "https://telegra.ph" + result[0]["src"]
            return None
    except Exception as e:
        print(f"telegra.ph upload error: {e}")
        return None

def upload_catbox(image_path):
    upload_url = "https://catbox.moe/user/api.php"
    try:
        with open(image_path, 'rb') as file:
            files = {"fileToUpload": file}
            data = {"reqtype": "fileupload"}
            response = requests.post(upload_url, data=data, files=files)
            if response.status_code == 200:
                return response.text.strip()
            return None
    except Exception as e:
        print(f"catbox.moe upload error: {e}")
        return None


# ----------- COMMAND HANDLER ------------ #
@Client.on_message(filters.command("telegraph") & filters.private)
async def telegraph_upload(bot, update: Message):
    t_msg = await bot.ask(
        chat_id=update.from_user.id,
        text="**__Now Send Me Your Photo Or Video (Max 5MB)__**"
    )

    if not t_msg.media:
        return await update.reply_text("**__Only Media Supported 😄__**")

    path = await t_msg.download()

    # Ask where to upload
    await update.reply_text(
        "**Where do you want to upload?**",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("envs.sh", callback_data=f"upload_envs|{path}")],
            [InlineKeyboardButton("telegra.ph", callback_data=f"upload_telegraph|{path}")],
            [InlineKeyboardButton("catbox.moe", callback_data=f"upload_catbox|{path}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="close")]
        ])
    )


# ----------- CALLBACK HANDLER ------------ #
@Client.on_callback_query()
async def callback_handler(bot, query: CallbackQuery):
    if query.data == "close":
        return await query.message.delete()

    if "|" in query.data:
        service, path = query.data.split("|", 1)
        uploading_message = await query.message.edit_text("<b><i>Uploading now 📤 ...</i></b>")

        try:
            if service == "upload_envs":
                url = upload_envs(path)
            elif service == "upload_telegraph":
                url = upload_telegraph(path)
            elif service == "upload_catbox":
                url = upload_catbox(path)
            else:
                url = None

            if not url:
                return await uploading_message.edit_text("**__Upload failed 💢__**")

            await uploading_message.edit_text(
                text=f"<b><blockquote>‣ 𝐘𝐎𝐔𝐑 𝐋𝐈𝐍𝐊 </b></blockquote>\n\n<code>{url}</code>",
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(text="Oᴘᴇɴ Lɪɴᴋ 🔓", url=url),
                        InlineKeyboardButton(text="Sʜᴀʀᴇ Lɪɴᴋ 🖇️",
                                             url=f"https://telegram.me/share/url?url={url}")
                    ],
                    [InlineKeyboardButton(text="❌ Cʟᴏsᴇ ❌", callback_data="close")]
                ])
            )

        except Exception as e:
            await uploading_message.edit_text(f"**__Upload failed: {e}__**")
        finally:
            if os.path.exists(path):
                os.remove(path)  # delete file after upload to save space
