from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from info import STREAM_MODE, URL, LOG_CHANNEL
from urllib.parse import quote_plus
from Neon.util.file_properties import get_name, get_hash, get_media_file_size
from Neon.util.human_readable import humanbytes

@Client.on_message(filters.private & filters.command("stream"))
async def stream_start(client, message):
    if not STREAM_MODE:
        return await message.reply("🚫 Streaming mode is disabled.")

    msg = await client.ask(
        message.chat.id, 
        "**__Now send me your file or video to get stream & download links.__**"
    )

    if msg.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.DOCUMENT]:
        return await message.reply("❌ Unsupported media type. Please send a video or document.")

    # ✅ Fix here
    file = getattr(msg, msg.media.value)
    filename = file.file_name
    filesize = humanbytes(get_media_file_size(msg))
    fileid = file.file_id
    user = message.from_user

    log_msg = await client.send_cached_media(
        chat_id=LOG_CHANNEL,
        file_id=fileid
    )

    file_name_encoded = quote_plus(get_name(log_msg))
    file_hash = get_hash(log_msg)

    stream = f"{URL}watch/{log_msg.id}/{file_name_encoded}?hash={file_hash}"
    download = f"{URL}{log_msg.id}/{file_name_encoded}?hash={file_hash}"

    await log_msg.reply_text(
        text=f"**• Link generated for ID:** `{user.id}`\n"
             f"**• Username:** {user.mention}\n\n"
             f"**• File Name:** {get_name(log_msg)}",
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Fast Download", url=download),
             InlineKeyboardButton("🖥 Watch Online", url=stream)]
        ])
    )

    rm = InlineKeyboardMarkup([
        [InlineKeyboardButton("🖥 Stream", url=stream),
         InlineKeyboardButton("📥 Download", url=download)]
    ])

    msg_text = (
        "<i><u>𝗬𝗼𝘂𝗿 𝗟𝗶𝗻𝗸 𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗲𝗱!</u></i>\n\n"
        f"<b>📂 File Name:</b> <i>{get_name(log_msg)}</i>\n"
        f"<b>📦 File Size:</b> <i>{filesize}</i>\n\n"
        f"<b>📥 Download:</b> <i>{download}</i>\n"
        f"<b>🖥 Watch:</b> <i>{stream}</i>\n\n"
        "<b>🚸 Note:</b> Link won’t expire unless I delete it."
    )

    await message.reply_text(
        text=msg_text,
        disable_web_page_preview=True,
        reply_markup=rm
    )
