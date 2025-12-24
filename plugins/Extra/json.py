# ---------------------------------------------------
# File Name: JSON.2.py
# Author: MyselfNeon
# Original Repo: https://github.com/MyselfNeon/NeonFilter-Bot
# GitHub: https://github.com/MyselfNeon/
# Telegram: https://t.me/MyelfNeon
# ---------------------------------------------------

import io
import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

@Client.on_message(filters.command(["json", "js"]))
async def jsonify(client, message):
    """
    Dumps the message object.
    Usage: /json (reply to a message or use in current message)
    """
    # 1. Determine target message (reply or self)
    target_message = message.reply_to_message if message.reply_to_message else message

    # 2. Get the string representation
    json_output = str(target_message)

    # 3. Create Close Button
    close_btn = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Close", callback_data="close_data")]])

    # 4. Check Length
    if len(json_output) < 4090:
        try:
            await message.reply_text(
                f"<code>{json_output}</code>",
                reply_markup=close_btn,
                quote=True
            )
        except Exception:
            # Fallback to .txt if text fails
            await send_as_file(message, json_output, "message_dump.txt")
    else:
        # 5. Send as .txt File if too long
        await send_as_file(message, json_output, "message_dump.txt", caption="⚠️ Message too long, sent as file.")


@Client.on_message(filters.command(["write"]))
async def create_file(client, message):
    """
    Creates a file from text.
    Usage: /written [filename] (reply to text)
    """
    # 1. Check for Reply
    if not message.reply_to_message:
        return await message.reply_text("⚠️ **Usage:** Reply to a text message to save it as a file.\n\n`/written [filename]`")

    # 2. Get Content (Text or Caption)
    content = message.reply_to_message.text or message.reply_to_message.caption
    if not content:
        return await message.reply_text("⚠️ The replied message doesn't have any text to save.")

    # 3. Determine Filename (Smart Extension Handling)
    if len(message.command) > 1:
        file_name = message.text.split(" ", 1)[1]
        # If user didn't add an extension (like .py, .html), default to .txt
        if "." not in file_name:
            file_name += ".txt"
    else:
        # Default name
        file_name = f"note_{message.reply_to_message.id}.txt"

    # 4. Processing Message
    status_msg = await message.reply_text("📝 **Generating file...**")

    try:
        # 5. Create file in memory
        file_stream = io.BytesIO(content.encode('utf-8'))
        file_stream.name = file_name

        # 6. Send Document
        await message.reply_document(
            document=file_stream,
            caption=f"📂 **File Created**\n🏷️ **Name:** `{file_name}`",
            quote=True
        )
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit(f"❌ **Error:** `{e}`")


async def send_as_file(message, content, filename, caption=""):
    """Helper function to send strings as files using BytesIO"""
    try:
        file_stream = io.BytesIO(content.encode('utf-8'))
        file_stream.name = filename
        await message.reply_document(
            document=file_stream,
            caption=caption,
            quote=True
        )
    except Exception as e:
        await message.reply_text(f"❌ Failed to send file: {e}")

# --- Callback Handler for Close Button ---
@Client.on_callback_query(filters.regex("^close_data"))
async def close_callback(_, query):
    await query.message.delete()
    
# MyselfNeon
# Don't Remove Credit 🥺
# Telegram Channel @NeonFiles
