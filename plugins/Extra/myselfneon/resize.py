#Resize.py Plugin
import os
import asyncio
from PIL import Image
from pyrogram import Client, filters
from pyrogram.types import Message

# ----------------------
# CONFIG (edit as needed)
# ----------------------
LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", 0))  # put channel id in env or directly replace with int

# ----------------------
# INTERNAL STORAGE
# ----------------------
USER_STATE = {}  # temp state machine for interactive resize

# ----------------------
# HELPER: delayed delete
# ----------------------
async def delayed_delete(msg: Message, delay: int):
    try:
        await asyncio.sleep(delay)
        await msg.delete()
    except:
        pass

# ----------------------
# RESIZE START
# ----------------------
@Client.on_message(filters.command("resize") & filters.private)
async def resize_start(client: Client, message: Message):
    user_id = message.from_user.id
    USER_STATE[user_id] = {"step": "await_photo"}

    await message.reply_text(
        "📸 Please send me the photo you want to resize.\n\n"
        "⏳ Timeout: 30s\n"
        "❌ Use /rcancel anytime to cancel."
    )

    try:
        # Wait for photo
        response: Message = await client.listen(user_id, timeout=30)
        if not response.photo:
            USER_STATE.pop(user_id, None)
            err = await message.reply_text("❌ You didn’t send a valid photo. Process canceled.")
            asyncio.create_task(delayed_delete(err, 10))
            return

        # Schedule deletion of user photo in 10s
        asyncio.create_task(delayed_delete(response, 10))

        # Download photo
        photo_path = await response.download()
        USER_STATE[user_id] = {"step": "await_width", "photo": photo_path, "orig_msg": response}

        ask_width_msg = await message.reply_text(
            "✏️ Enter the width (numbers only):\n\n⏳ Timeout: 30s\n❌ /rcancel to cancel."
        )

        # Wait for width
        width_response: Message = await client.listen(user_id, timeout=30)
        if not (width_response.text and width_response.text.isdigit()):
            USER_STATE.pop(user_id, None)
            os.remove(photo_path)
            err = await message.reply_text("❌ Invalid width. Process canceled.")
            asyncio.create_task(delayed_delete(err, 10))
            return

        width = int(width_response.text)
        USER_STATE[user_id]["width"] = width

        # delete bot+user width messages in 5s
        asyncio.create_task(delayed_delete(ask_width_msg, 5))
        asyncio.create_task(delayed_delete(width_response, 5))

        ask_height_msg = await message.reply_text(
            "📏 Now enter the height (numbers only):\n\n⏳ Timeout: 30s\n❌ /rcancel to cancel."
        )

        # Wait for height
        height_response: Message = await client.listen(user_id, timeout=30)
        if not (height_response.text and height_response.text.isdigit()):
            USER_STATE.pop(user_id, None)
            os.remove(photo_path)
            err = await message.reply_text("❌ Invalid height. Process canceled.")
            asyncio.create_task(delayed_delete(err, 10))
            return

        height = int(height_response.text)

        # delete bot+user height messages in 5s
        asyncio.create_task(delayed_delete(ask_height_msg, 5))
        asyncio.create_task(delayed_delete(height_response, 5))

        # Show processing message
        processing_msg = await message.reply_text("⚙️ Please wait, your photo is being processed...")

        # Process image
        img = Image.open(photo_path)
        resized_img = img.resize((width, height))

        output_file = f"resized_{user_id}.jpg"
        resized_img.save(output_file, "JPEG")

        # Send both photo and document
        result_photo = await message.reply_photo(output_file, caption=f"✅ Resized to {width}x{height}px")
        result_doc = await message.reply_document(output_file)

        # auto-delete final results after 5 minutes
        asyncio.create_task(delayed_delete(result_photo, 300))
        asyncio.create_task(delayed_delete(result_doc, 300))

        # delete processing message immediately after sending final
        asyncio.create_task(delayed_delete(processing_msg, 0))

        # Log original photo + user info (permanent in log channel)
        if LOG_CHANNEL:
            try:
                orig_msg = USER_STATE[user_id]["orig_msg"]
                caption_text = (
                    f"**🖼️ Image Resize Request**\n\n"
                    f"👤 User: {message.from_user.mention} (`{user_id}`)\n"
                    f"🆔 Username: @{message.from_user.username if message.from_user.username else 'N/A'}"
                )
                await orig_msg.copy(LOG_CHANNEL, caption=caption_text)
            except Exception as e:
                print(f"Failed to log resize: {e}")

        # Cleanup
        os.remove(photo_path)
        os.remove(output_file)
        USER_STATE.pop(user_id, None)

    except asyncio.TimeoutError:
        USER_STATE.pop(user_id, None)
        msgx = await message.reply_text("⌛ Timeout! Process canceled.")
        asyncio.create_task(delayed_delete(msgx, 10))
    except Exception as e:
        USER_STATE.pop(user_id, None)
        msgx = await message.reply_text(f"⚠️ Error: `{e}`")
        asyncio.create_task(delayed_delete(msgx, 10))


# ----------------------
# CANCEL COMMAND
# ----------------------
@Client.on_message(filters.command("rcancel") & filters.private)
async def resize_cancel(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id in USER_STATE:
        try:
            photo_path = USER_STATE[user_id].get("photo")
            if photo_path and os.path.exists(photo_path):
                os.remove(photo_path)
        except:
            pass

        USER_STATE.pop(user_id, None)
        done = await message.reply_text("🛑 Resize process canceled successfully.")
        asyncio.create_task(delayed_delete(done, 10))

        if LOG_CHANNEL:
            try:
                caption_text = (
                    f"**❌ Resize Canceled**\n\n"
                    f"👤 User: {message.from_user.mention} (`{user_id}`)\n"
                    f"🆔 Username: @{message.from_user.username if message.from_user.username else 'N/A'}"
                )
                await client.send_message(LOG_CHANNEL, caption_text)
            except Exception as e:
                print(f"Failed to log cancel: {e}")
    else:
        warn = await message.reply_text("⚠️ No active resize process to cancel.")
        asyncio.create_task(delayed_delete(warn, 10))
        
