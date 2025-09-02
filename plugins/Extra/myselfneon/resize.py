import os
import asyncio
from PIL import Image
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from info import LOG_CHANNEL  # <-- Add your log channel here

# ----------------------
# Resize + Compress Plugin (Standalone)
# ----------------------

USER_STATE = {}

# /resize command entry
@Client.on_message(filters.command("resize") & filters.private)
async def resize_menu(client: Client, message: Message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🖼️ Resize", callback_data="resize_mode")],
        [InlineKeyboardButton("📉 Compress", callback_data="compress_mode")]
    ])
    await message.reply_text("⚙️ Choose an option:", reply_markup=keyboard)


# Callback for Resize / Compress choice
@Client.on_callback_query()
async def handle_callback(client: Client, callback_query):
    user_id = callback_query.from_user.id

    if callback_query.data == "resize_mode":
        USER_STATE[user_id] = {"mode": "resize", "step": "await_photo"}
        await callback_query.message.reply_text("📸 Send me the photo you want to resize (Timeout: 30s).")

    elif callback_query.data == "compress_mode":
        USER_STATE[user_id] = {"mode": "compress", "step": "await_photo"}
        await callback_query.message.reply_text("📸 Send me the photo you want to compress (Timeout: 30s).")

    elif callback_query.data == "resize_sticker":
        USER_STATE[user_id]["resize_type"] = "sticker"
        await process_resize(client, callback_query.message, user_id)

    elif callback_query.data == "resize_custom":
        USER_STATE[user_id]["resize_type"] = "custom"
        await callback_query.message.reply_text("✏️ Enter custom width:")

    elif callback_query.data.startswith("compress_"):
        size_px = int(callback_query.data.split("_")[1])
        USER_STATE[user_id]["compress_size"] = size_px
        await process_compress(client, callback_query.message, user_id, size_px)

    elif callback_query.data == "compress_custom":
        USER_STATE[user_id]["compress_type"] = "custom"
        await callback_query.message.reply_text("✏️ Enter custom max size in KB:")


# Handle user messages for custom inputs
@Client.on_message(filters.private & filters.text)
async def handle_custom_inputs(client: Client, message: Message):
    user_id = message.from_user.id

    if user_id not in USER_STATE:
        return

    state = USER_STATE[user_id]

    # Resize custom width/height
    if state.get("mode") == "resize" and state.get("resize_type") == "custom":
        if "width" not in state:
            if not message.text.isdigit():
                return await message.reply_text("❌ Invalid width. Numbers only.")
            state["width"] = int(message.text)
            await message.delete()
            await message.reply_text("📏 Now enter the height:")
        else:
            if not message.text.isdigit():
                return await message.reply_text("❌ Invalid height. Numbers only.")
            state["height"] = int(message.text)
            await message.delete()
            await process_resize(client, message, user_id)

    # Compress custom size
    elif state.get("mode") == "compress" and state.get("compress_type") == "custom":
        if not message.text.isdigit():
            return await message.reply_text("❌ Invalid size. Numbers only.")
        state["compress_size"] = int(message.text)
        await message.delete()
        await process_compress(client, message, user_id, state["compress_size"])


# Handle photo uploads
@Client.on_message(filters.private & filters.photo)
async def handle_photos(client: Client, message: Message):
    user_id = message.from_user.id

    if user_id not in USER_STATE:
        return

    state = USER_STATE[user_id]

    # Store photo path
    photo_path = await message.download()
    state["photo"] = photo_path
    state["original_msg"] = message  # Save original message for logging

    # Log original upload
    try:
        caption_text = (
            f"**🛜 New Upload Detected**\n\n"
            f"👤 **User:** {message.from_user.mention} (`{user_id}`)\n"
            f"🆔 **Username:** @{message.from_user.username if message.from_user.username else 'N/A'}\n"
            f"📂 **Action:** {state['mode'].capitalize()} requested"
        )
        await client.send_photo(LOG_CHANNEL, photo_path, caption=caption_text)
    except Exception as e:
        print(f"⚠️ Failed to log upload: {e}")

    # Ask next step
    if state.get("mode") == "resize":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🤖 TG Sticker (512px)", callback_data="resize_sticker")],
            [InlineKeyboardButton("✏️ Custom", callback_data="resize_custom")]
        ])
        await message.reply_text("⚙️ Choose resize option:", reply_markup=keyboard)

    elif state.get("mode") == "compress":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("150px", callback_data="compress_150")],
            [InlineKeyboardButton("300px", callback_data="compress_300")],
            [InlineKeyboardButton("500px", callback_data="compress_500")],
            [InlineKeyboardButton("✏️ Custom", callback_data="compress_custom")]
        ])
        await message.reply_text("⚙️ Choose compression size:", reply_markup=keyboard)


# Process Resize
async def process_resize(client, message, user_id):
    try:
        state = USER_STATE[user_id]
        photo_path = state["photo"]

        processing_msg = await message.reply_text("⚙️ Processing... please wait.")

        img = Image.open(photo_path)

        if state["resize_type"] == "sticker":
            img.thumbnail((512, 512), Image.Resampling.LANCZOS)
        else:
            width = state["width"]
            height = state["height"]
            img = img.resize((width, height), Image.Resampling.LANCZOS)

        output_file = f"resized_{user_id}.jpg"
        img.save(output_file, "JPEG")

        await processing_msg.delete()
        await message.reply_photo(output_file, caption="✅ Here’s your resized image")
        await message.reply_document(output_file)

        os.remove(photo_path)
        os.remove(output_file)
        USER_STATE.pop(user_id, None)

    except Exception as e:
        await message.reply_text(f"⚠️ Error during resize: {e}")
        USER_STATE.pop(user_id, None)


# Process Compress
async def process_compress(client, message, user_id, target_size):
    try:
        state = USER_STATE[user_id]
        photo_path = state["photo"]

        processing_msg = await message.reply_text("⚙️ Processing... please wait.")

        img = Image.open(photo_path)
        img.thumbnail((target_size, target_size), Image.Resampling.LANCZOS)

        output_file = f"compressed_{user_id}.jpg"
        img.save(output_file, "JPEG", quality=95)

        await processing_msg.delete()
        await message.reply_photo(output_file, caption=f"✅ Compressed to ~{target_size}px (aspect ratio kept)")
        await message.reply_document(output_file)

        os.remove(photo_path)
        os.remove(output_file)
        USER_STATE.pop(user_id, None)

    except Exception as e:
        await message.reply_text(f"⚠️ Error during compress: {e}")
        USER_STATE.pop(user_id, None)
        
