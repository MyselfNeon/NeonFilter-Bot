import os
import asyncio
from PIL import Image
from pyrogram import Client, filters
from pyrogram.types import Message
from info import LOG_CHANNEL  # Add your log channel in info.py

# ----------------------
# Resize + Compress Plugin (Standalone)
# ----------------------

USER_STATE = {}

@Client.on_message(filters.command("resize") & filters.private)
async def resize_menu(client: Client, message: Message):
    await message.reply_text("🔧 Send me the photo you want to resize or compress.\n(Timeout: 30s)")


@Client.on_message(filters.private & filters.photo)
async def handle_photo(client: Client, message: Message):
    user_id = message.from_user.id
    photo_path = await message.download()
    USER_STATE[user_id] = {"photo": photo_path, "mode": None}  # mode will be determined next

    # Log upload to LOG_CHANNEL
    try:
        caption_text = (
            f"**🛜 __New Upload Detected__**\n\n"
            f"**👤 User : {message.from_user.mention} (`{user_id}`)**\n"
            f"**🆔 Username : @{message.from_user.username if message.from_user.username else 'N/A'}**\n"
            f"**📂 Action: Awaiting Resize/Compress Choice**"
        )
        await client.send_photo(LOG_CHANNEL, photo_path, caption=caption_text)
    except Exception as e:
        print(f"Failed to log upload: {e}")

    # Ask user what they want to do directly
    await message.reply_text(
        "📌 Do you want to **resize** or **compress** this photo?\n"
        "Reply with:\n`resize` or `compress`\n(Timeout: 30s)"
    )
    USER_STATE[user_id]["mode"] = "await_choice"


@Client.on_message(filters.private & filters.text)
async def handle_text(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in USER_STATE:
        return

    state = USER_STATE[user_id]
    text = message.text.lower()

    if state.get("mode") == "await_choice":
        if text == "resize":
            state["mode"] = "resize_wait_size"
            await message.reply_text("📐 Enter the new size in `WIDTHxHEIGHT` format (e.g., 512x512):")
        elif text == "compress":
            state["mode"] = "compress_wait_size"
            await message.reply_text("📉 Enter the max width for compression (e.g., 150, 300, 500):")
        else:
            await message.reply_text("❌ Invalid choice! Please reply with `resize` or `compress`.")


@Client.on_message(filters.private & filters.text)
async def handle_size_input(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in USER_STATE:
        return

    state = USER_STATE[user_id]
    text = message.text.lower()

    # Handle Resize
    if state.get("mode") == "resize_wait_size":
        try:
            width, height = map(int, text.lower().split("x"))
        except Exception:
            await message.reply_text("❌ Invalid format! Use `WIDTHxHEIGHT` (e.g., 512x512).")
            return

        photo_path = state["photo"]
        img = Image.open(photo_path)
        img = img.resize((width, height))
        save_path = f"resized_{os.path.basename(photo_path)}"
        img.save(save_path)
        await message.reply_photo(save_path, caption=f"✅ Resized to {width}x{height}")
        os.remove(photo_path)
        os.remove(save_path)
        USER_STATE.pop(user_id)

    # Handle Compress
    elif state.get("mode") == "compress_wait_size":
        try:
            max_width = int(text)
        except Exception:
            await message.reply_text("❌ Invalid number! Enter a valid width (e.g., 150, 300, 500).")
            return

        photo_path = state["photo"]
        img = Image.open(photo_path)
        w_percent = max_width / float(img.size[0])
        h_size = int((float(img.size[1]) * float(w_percent)))
        img = img.resize((max_width, h_size))
        save_path = f"compressed_{os.path.basename(photo_path)}"
        img.save(save_path, optimize=True, quality=85)
        await message.reply_photo(save_path, caption=f"✅ Compressed to width {max_width}px")
        os.remove(photo_path)
        os.remove(save_path)
        USER_STATE.pop(user_id)
        
