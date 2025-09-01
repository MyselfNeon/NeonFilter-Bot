import os
import aiohttp
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message

STREAMABLE_USER = os.environ.get("STREAMABLE_USER")
STREAMABLE_PASS = os.environ.get("STREAMABLE_PASS")
MAX_SIZE = 200 * 1024 * 1024  # 200 MB

@Client.on_message(filters.command("streamable") & filters.private)
async def streamable_command(client: Client, message: Message):
    # If credentials not set, ignore command
    if not STREAMABLE_USER or not STREAMABLE_PASS:
        return

    prompt = await message.reply_text(
        "📹 Send the video you want to upload to Streamable (max 200 MB).\n⏳ You have 30 seconds to send it."
    )

    try:
        # Wait for user's video reply (30 sec timeout)
        video_msg: Message = await client.listen(message.chat.id, filters.video, timeout=30)
    except asyncio.TimeoutError:
        timeout_msg = await message.reply_text("⏰ Time's up! You didn't send a video in time.")
        await asyncio.sleep(20)
        await timeout_msg.delete()
        await prompt.delete()
        return

    if video_msg.video.file_size > MAX_SIZE:
        await message.reply_text("❌ Video too large! Maximum allowed size is 200 MB.")
        return

    uploading_msg = await message.reply_text("⏳ Downloading and uploading your video... (max 1 minute)")

    try:
        # Download video
        video_path = await video_msg.download()

        # Upload with 1-minute timeout
        async with aiohttp.ClientSession() as session:
            with open(video_path, "rb") as f:
                data = aiohttp.FormData()
                data.add_field("file", f)
                try:
                    async with asyncio.wait_for(
                        session.post(
                            "https://api.streamable.com/upload",
                            data=data,
                            auth=aiohttp.BasicAuth(STREAMABLE_USER, STREAMABLE_PASS)
                        ),
                        timeout=60
                    ) as resp:
                        result = await resp.json()
                except asyncio.TimeoutError:
                    await uploading_msg.edit("⏰ Upload took too long! Cancelled.")
                    return

        if resp.status == 200 and "shortcode" in result:
            link = f"https://streamable.com/{result['shortcode']}"
            await uploading_msg.edit(f"✅ Uploaded successfully!\n\n🔗 {link}")
        else:
            await uploading_msg.edit(f"❌ Failed to upload!\n\nResponse: {result}")

    except Exception as e:
        await uploading_msg.edit(f"❌ Error occurred:\n{e}")
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)

      
