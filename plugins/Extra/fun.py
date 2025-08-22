import os
import httpx
import asyncio
from pyrogram import Client, filters

# Hugging Face Real-ESRGAN API
HF_API_URL = "https://api-inference.huggingface.co/models/nateraw/real-esrgan"
HF_TOKEN = os.getenv("HF_TOKEN")
HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}


async def fake_progress(msg, steps=5, delay=3):
    """Simulate a progress bar by editing the message"""
    for i in range(1, steps + 1):
        percent = int((i / steps) * 100)
        try:
            await msg.edit_text(f"✨ Enhancing your image...\nProgress: {percent}%")
        except:
            pass
        await asyncio.sleep(delay)


@Client.on_message(filters.command("enhance") & filters.reply)
async def enhance_image(client, message):
    """Enhance any replied image (photo/doc/webp) using Hugging Face Real-ESRGAN"""
    if not HF_TOKEN:
        return await message.reply("⚠️ HuggingFace token not set. Please configure HF_TOKEN.")

    replied = message.reply_to_message

    # Identify image source
    file_id = None
    if replied.photo:
        file_id = replied.photo.file_id
    elif replied.document and replied.document.mime_type.startswith("image/"):
        file_id = replied.document.file_id
    elif replied.sticker and not replied.sticker.is_animated:
        file_id = replied.sticker.file_id

    if not file_id:
        return await message.reply("⚠️ Please reply to a photo, image document, or static sticker.")

    msg = await message.reply("✨ Enhancing your image...")

    # Start progress simulation in background
    asyncio.create_task(fake_progress(msg))

    # Download file
    input_path = await client.download_media(file_id)

    try:
        # Send to Hugging Face
        with open(input_path, "rb") as f:
            async with httpx.AsyncClient(timeout=300) as http:
                resp = await http.post(HF_API_URL, headers=HEADERS, data=f)

        if resp.status_code != 200:
            return await msg.edit_text(f"❌ Enhancement failed: {resp.text}")

        # Save enhanced image
        output_path = "enhanced_" + os.path.basename(input_path)
        with open(output_path, "wb") as out:
            out.write(resp.content)

        # Send result back
        await message.reply_photo(output_path, caption="✅ Enhanced by AI (Real-ESRGAN)")
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"⚠️ Error: {e}")

    finally:
        # Cleanup
        for file in (input_path, locals().get("output_path", None)):
            if file and os.path.exists(file):
                os.remove(file)