from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from info import STREAM_MODE, URL, LOG_CHANNEL
from urllib.parse import quote_plus
from Neon.util.file_properties import get_name, get_hash, get_media_file_size
from Neon.util.human_readable import humanbytes
import random

@Client.on_message(filters.private & filters.command("stream"))
async def stream_start(client, message):
    if STREAM_MODE is False:
        return 
    
    msg = await client.ask(
        message.chat.id, 
        "**__Now Send me your File/Video to get Stream and Download Link.__**"
    )

    # only accept video or document
    if msg.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.DOCUMENT]:
        return await message.reply("**__Please send me Supported Media.__**")
    
    file = getattr(msg, msg.media)
    filename = file.file_name
    filesize = humanbytes(get_media_file_size(msg))  # consistent usage
    fileid = file.file_id
    user_id = message.from_user.id
    username = message.from_user.mention 

    # forward to log channel
    log_msg = await client.send_cached_media(
        chat_id=LOG_CHANNEL,
        file_id=fileid,
    )

    # file name (fixed: no { })
    fileName = quote_plus(get_name(log_msg))

    # links
    stream = f"{URL}watch/{str(log_msg.id)}/{fileName}?hash={get_hash(log_msg)}"
    download = f"{URL}{str(log_msg.id)}/{fileName}?hash={get_hash(log_msg)}"
 
    # log channel info
    await log_msg.reply_text(
        text=f"•• Link generated for ID #{user_id} \n•• Username : {username} \n\n•• File Name : {get_name(log_msg)}",
        quote=True,
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("🚀 Fast Download 🚀", url=download),
                InlineKeyboardButton('🖥️ Watch Online 🖥️', url=stream)
            ]]
        )
    )

    # user reply buttons
    rm = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("Sᴛʀᴇᴀᴍ 🖥", url=stream),
            InlineKeyboardButton('Dᴏᴡɴʟᴏᴀᴅ 📥', url=download)
        ]] 
    )

    # final message to user
    msg_text = """<i><u>𝗬𝗼𝘂𝗿 𝗟𝗶𝗻𝗸 𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗲𝗱 !</u></i>\n\n<b>📂 Fɪʟᴇ Nᴀᴍᴇ :</b> <i>{}</i>\n\n<b>📦 Fɪʟᴇ Sɪᴢᴇ :</b> <i>{}</i>\n\n<b>📥 Dᴏᴡɴʟᴏᴀᴅ :</b> <i>{}</i>\n\n<b>🖥 Wᴀᴛᴄʜ :</b> <i>{}</i>\n\n<b>🚸 Note : Link won't Expire till i Delete</b>"""

    await message.reply_text(
        text=msg_text.format(get_name(log_msg), filesize, download, stream),
        quote=True,
        disable_web_page_preview=True,
        reply_markup=rm
    )
