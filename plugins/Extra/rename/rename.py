import os
import json
from asyncio import sleep
import humanize
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from plugins.Extra.rename.filedetect import refunc
from info import RENAME_MODE

METADATA_FILE = "metadata.json"

# =========================
# 🔹 Metadata functions
# =========================
def load_metadata():
    if not os.path.exists(METADATA_FILE):
        return {}
    with open(METADATA_FILE, "r") as f:
        return json.load(f)

def get_user_metadata(user_id):
    data = load_metadata()
    return data.get(str(user_id), {"enabled": False, "code": ""})

# =========================
# 🔹 Core rename function
# =========================
async def rename_flow(client: Client, message: Message, file):
    try:
        filename = getattr(file, "file_name", None) or "Unnamed_File"
        filesize = humanize.naturalsize(getattr(file, "file_size", 0))

        # Ask for new filename
        ask = await client.ask(
            chat_id=message.chat.id,
            text=f"**Original File:**\n`{filename}`\nSize: `{filesize}`\n\n✏️ Send me the new file name (with extension):",
            filters=filters.text,
            timeout=60,
            reply_to_message_id=message.id
        )
        new_filename = ask.text.strip()

        # Download file
        status_msg = await message.reply_text("📥 Downloading your file...")
        downloaded_file = await client.download_media(message, file_name=filename)

        # Rename locally
        new_file_path = os.path.join(os.path.dirname(downloaded_file), new_filename)
        os.rename(downloaded_file, new_file_path)

        # Metadata caption
        user_meta = get_user_metadata(message.from_user.id)
        caption = f"**Renamed File ✅**\n`{new_filename}`"
        if user_meta["enabled"] and user_meta["code"]:
            caption = user_meta["code"].replace("{filename}", new_filename)

        # Send file according to type
        if message.document:
            await client.send_document(message.chat.id, new_file_path, caption=caption, reply_to_message_id=message.id)
        elif message.video:
            await client.send_video(message.chat.id, new_file_path, caption=caption, reply_to_message_id=message.id)
        elif message.audio:
            await client.send_audio(message.chat.id, new_file_path, caption=caption, reply_to_message_id=message.id)
        elif message.photo:
            await client.send_photo(message.chat.id, new_file_path, caption=caption, reply_to_message_id=message.id)

        await status_msg.delete()

    except Exception as e:
        await message.reply_text(f"⚠️ Error: {e}")

# =========================
# 🔹 Command-based rename
# =========================
@Client.on_message(filters.private & filters.command("rename"))
async def rename_command(client, message: Message):
    if not RENAME_MODE:
        return await message.reply_text("⚠️ Renaming is currently disabled.")
    # Ask user to send file
    ask_msg = await client.ask(message.chat.id, "**Send the file/video/audio/photo you want to rename:**")
    if not ask_msg.media:
        return await message.reply_text("⚠️ Unsupported media. Please send a document, video, audio, or photo.")
    
    file_attr = getattr(ask_msg, ask_msg.media.value)
    await rename_flow(client, ask_msg, file_attr)

# =========================
# 🔹 Automatic media-based rename
# =========================
@Client.on_message(filters.private & (filters.document | filters.video | filters.audio | filters.photo))
async def rename_auto(client, message: Message):
    if not RENAME_MODE:
        return
    file = message.document or message.video or message.audio or message.photo
    await rename_flow(client, message, file)
