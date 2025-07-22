
from pyrogram import Client, filters
from pyrogram.enums import MessageMediaType
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ForceReply

async def refunc(client, message, new_name, msg):
    try:
        file = getattr(msg, msg.media.value)
        filename = file.file_name
        types = file.mime_type.split("/")
        mime = types[0]
        try:
            if ".mp4" or ".mkv" in new_name:
                if ".mp4" in new_name:
                    new_name = new_name.replace(".mp4", "")  # Remove the dot from new_name
                if ".mkv" in new_name:
                    new_name = new_name.replace(".mkv", "")
            else:
                new_name = new_name
            if "." in new_name:
                new_name = new_name.replace(".", "")  
            if mime == "video":
                markup = InlineKeyboardMarkup([[
                    InlineKeyboardButton("📁 Document", callback_data="upload_document"),
                    InlineKeyboardButton("🎥 Video", callback_data="upload_video")]])
            elif mime == "audio":
                markup = InlineKeyboardMarkup([[InlineKeyboardButton(
                    "📁 Document", callback_data="upload_document"), InlineKeyboardButton("🎵 audio", callback_data="upload_audio")]])
            else:
                markup = InlineKeyboardMarkup(
                    [[InlineKeyboardButton("📁 Document", callback_data="upload_document")]])
            await message.reply_text(f"**--𝐒𝐄𝐋𝐄𝐂𝐓 𝐎𝐔𝐓𝐏𝐔𝐓 𝐅𝐈𝐋𝐄 𝐓𝐘𝐏𝐄--  🌐**\n\n𝙉𝙚𝙬 𝙉𝙖𝙢𝙚 📝 : \n```{out_filename}```", reply_to_message_id=msg.id, reply_markup=markup)

        except:
            try:
                out = filename.split(".")
                out_name = out[-1]
                out_filename = new_name + "." + out_name
            except:
                await message.reply_text("**<u>💢 __ERROR__ 💢</u>** :\n**__No  Extension in File, Not Supporting__**")
                return
            if mime == "video":
                markup = InlineKeyboardMarkup([[InlineKeyboardButton(
                    "📁 Document", callback_data="upload_document"), InlineKeyboardButton("🎥 Video", callback_data="upload_video")]])
            elif mime == "audio":
                markup = InlineKeyboardMarkup([[InlineKeyboardButton(
                    "📁 Document", callback_data="upload_document"), InlineKeyboardButton("🎵 Audio", callback_data="upload_audio")]])
            else:
                markup = InlineKeyboardMarkup(
                    [[InlineKeyboardButton("📁 Document", callback_data="upload_document")]])
            await message.reply_text(f"**--𝐒𝐄𝐋𝐄𝐂𝐓 𝐎𝐔𝐓𝐏𝐔𝐓 𝐅𝐈𝐋𝐄 𝐓𝐘𝐏𝐄--  🌐**\n\n𝙉𝙚𝙬 𝙉𝙖𝙢𝙚 📝 : \n{out_filename}", reply_to_message_id=msg.id, reply_markup=markup)
    except Exception as e:
        print(f"error: {e}")
