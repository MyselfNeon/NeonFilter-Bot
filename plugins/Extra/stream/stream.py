from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from info import STREAM_MODE, URL, LOG_CHANNEL
from urllib.parse import quote_plus
from Neon.util.file_properties import get_name, get_hash, get_media_file_size
from Neon.util.human_readable import humanbytes

@Client.on_message(filters.private & filters.command("stream"))
async def stream_start(client, message):
    if not STREAM_MODE:
        return await message.reply("🚫 Streaming Mode is Disabled.")

    msg = await client.ask(
        message.chat.id, 
        "**__Now send me your File or Video to get Stream & Download Links.__**"
    )

    if msg.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.DOCUMENT]:
        return await message.reply("❌ Unsupported Media Type. Please Send a Video or Document.")

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
        text=f"**__➠ Link Generated for ID:** `{user.id}`\n"
             f"**__➠ Username:** {user.mention}__\n\n"
             f"**__➠ File Name:** {get_name(log_msg)}__",
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Fᴀsᴛ Dᴏᴡɴʟᴏᴀᴅ", url=download),
             InlineKeyboardButton("🖥 Wᴀᴛᴄʜ Oɴʟɪɴᴇ", url=stream)]
        ])
    )

    rm = InlineKeyboardMarkup([
        [InlineKeyboardButton("🖥 Sᴛʀᴇᴀᴍ", url=stream),
         InlineKeyboardButton("📥 Dᴏᴡɴʟᴏᴀᴅ", url=download)]
    ])

    msg_text = (
        "<i><u>𝗬𝗼𝘂𝗿 𝗟𝗶𝗻𝗸 𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗲𝗱!</u></i>\n\n"
        f"<b><i>📂 File Name:</b>\n{get_name(log_msg)}</i>\n"
        f"<b><i>📦 File Size:</b> {filesize}</i>\n\n"
        f"<b><i>📥 Download:</i></b>\n<code>{download}</code>\n"
        f"<b><i>🖥 Watch:</i></b>\n<code>{stream}</code>\n\n"
        "<b><i>🚫 Link won’t Expire unless I Delete it.</i></b>"
    )

    await message.reply_text(
        text=msg_text,
        disable_web_page_preview=True,
        reply_markup=rm
    )
