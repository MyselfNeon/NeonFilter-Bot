import os
import asyncio
from PIL import Image
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import LOG_CHANNEL  # Add your log channel in info.py

# ----------------------
# Resize + Compress Plugin (Standalone)
# ----------------------

USER_STATE = {}

@Client.on_message(filters.command("resize") & filters.private)
async def resize_menu(client: Client, message: Message):
    keyboard = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("🖼 Resize", callback_data="choose_resize"),
            InlineKeyboardButton("📦 Compress", callback_data="choose_compress")
        ]]
    )
    await message.reply_text("🔧 Choose what you want to do:", reply_markup=keyboard)


# ----------------------
# Handle Resize Selection
# ----------------------
@Client.on_callback_query(filters.regex("choose_resize"))
async def handle_resize(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    USER_STATE[user_id] = {"mode": "resize_wait_photo"}
    await callback.message.reply_text("📸 Please send the photo you want to resize.\n(Timeout: 30s)")


@Client.on_message(filters.private & filters.photo)
async def handle_photo(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in USER_STATE:
        return

    state = USER_STATE[user_id]

    # If waiting for photo in resize
    if state.get("mode") == "resize_wait_photo":
        photo_path = await message.download()
        USER_STATE[user_id] = {"mode": "resize_choose_size", "photo": photo_path}

        # Log upload to LOG_CHANNEL
        try:
            caption_text = (
                f"**🛜 __New Upload Detected__**\n\n"
                f"**👤 User : {message.from_user.mention} (`{user_id}`)**\n"
                f"**🆔 Username : @{message.from_user.username if message.from_user.username else 'N/A'}**\n"
                f"**📂 Requested: Resize**"
            )
            await client.send_photo(LOG_CHANNEL, photo_path, caption=caption_text)
        except Exception as e:
            print(f"Failed to Log Upload: {e}")

        # Ask for size
        keyboard = InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("🟩 TG Sticker (512x512)", callback_data="resize_sticker"),
                InlineKeyboardButton("✏️ Custom Size", callback_data="resize_custom")
            ]]
        )
        await message.reply_text("📐 Choose resize option:", reply_markup=keyboard)

    # If waiting for photo in compress
    elif state.get("mode") == "compress_wait_photo":
        photo_path = await message.download()
        USER_STATE[user_id] = {"mode": "compress_choose_size", "photo": photo_path}

        # Log upload to LOG_CHANNEL
        try:
            caption_text = (
                f"**🛜 __New Upload Detected__**\n\n"
                f"**👤 User : {message.from_user.mention} (`{user_id}`)**\n"
                f"**🆔 Username : @{message.from_user.username if message.from_user.username else 'N/A'}**\n"
                f"**📂 Requested: Compress**"
            )
            await client.send_photo(LOG_CHANNEL, photo_path, caption=caption_text)
        except Exception as e:
            print(f"Failed to Log Upload: {e}")

        # Ask for compress size
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("150px", callback_data="compress_150"),
                 InlineKeyboardButton("300px", callback_data="compress_300")],
                [InlineKeyboardButton("500px", callback_data="compress_500"),
                 InlineKeyboardButton("✏️ Custom", callback_data="compress_custom")]
            ]
        )
        await message.reply_text("📉 Choose compress option:", reply_markup=keyboard)


# ----------------------
# Handle Compress Selection
# ----------------------
@Client.on_callback_query(filters.regex("choose_compress"))
async def handle_compress(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    USER_STATE[user_id] = {"mode": "compress_wait_photo"}
    await callback.message.reply_text("📸 Please send the photo you want to compress.\n(Timeout: 30s)")


# ----------------------
# You’d add resize/compress processing here (same as before with aspect ratio)
# ----------------------
