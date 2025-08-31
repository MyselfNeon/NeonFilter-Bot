import aiohttp
import os
import mimetypes
from pyrogram import Client, filters
from pyrogram.types import Message

# Max file size you want to allow (in bytes), adjust as needed
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200 MB

# Temporary download folder
TEMP_DIR = "./downloads"
os.makedirs(TEMP_DIR, exist_ok=True)

@Client.on_message(filters.command("getfile") & filters.private)
async def download_file(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text(
            "❌ Please provide a direct download link.\n\nUsage: `/getfile <link>`"
        )
        return

    url = message.command[1]
    status_msg = await message.reply_text("⏳ Downloading your file... Please wait.")

    try:
        # Generate temporary file path
        filename = os.path.join(TEMP_DIR, url.split("/")[-1])

        # Download file
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    await status_msg.edit_text("❌ Failed to download file. Check the link.")
                    return

                # Check content length if available
                content_length = resp.content_length
                if content_length and content_length > MAX_FILE_SIZE:
                    await status_msg.edit_text(
                        f"❌ File too large! Max allowed size is {MAX_FILE_SIZE / (1024*1024)} MB."
                    )
                    return

                # Save the file
                with open(filename, "wb") as f:
                    while True:
                        chunk = await resp.content.read(1024*1024)  # 1MB chunks
                        if not chunk:
                            break
                        f.write(chunk)

        # Detect file type
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type:
            if mime_type.startswith("video"):
                await message.reply_video(filename)
            elif mime_type.startswith("audio"):
                await message.reply_audio(filename)
            else:
                await message.reply_document(filename)
        else:
            await message.reply_document(filename)

        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"❌ Error occurred: {e}")

    finally:
        # Clean up downloaded file
        if os.path.exists(filename):
            os.remove(filename)
          
