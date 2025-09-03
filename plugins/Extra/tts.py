import asyncio
from io import BytesIO
import edge_tts
from pyrogram import Client, filters
from pyrogram.types import Message

# Default voice if user doesn't specify
DEFAULT_VOICE = "en-US-AriaNeural"

# Example mapping of simple language codes to voices
VOICE_MAP = {
    "en": "en-US-AriaNeural",
    "hi": "hi-IN-SwaraNeural",
    "es": "es-ES-ElviraNeural",
    "fr": "fr-FR-DeniseNeural"
}

async def convert(text: str, voice: str) -> BytesIO:
    audio = BytesIO()
    audio.name = "Neon.mp3"

    communicate = edge_tts.Communicate(text, voice=voice)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio.write(chunk["data"])

    audio.seek(0)
    return audio

@Client.on_message(filters.command("tts"))
async def text_to_speech(bot, message: Message):
    args = message.text.split(maxsplit=1)
    
    # Pick voice from user input
    if len(args) > 1:
        voice_input = args[1].strip()
        voice = VOICE_MAP.get(voice_input, voice_input)  # Map code or direct voice
    else:
        voice = DEFAULT_VOICE
    
    # Send both messages together
    ask_msg = await message.reply_text("**__Now Send Me Your Text__ 😄**")
    reminder_msg = await message.reply_text("**__Use Custom Voice Models__ 🗣️**\n\n<code>/tts es</code> - **__Eʟᴠɪʀᴀ__**\n<code>/tts en</code> - **__Aʀɪᴀ__**\n<code>/tts hi</code>  - **__Sᴡᴀʀᴀ__**\n<code>/tts fr</code>   - **__Dᴇɴɪᴄᴇ__**")
    asyncio.create_task(auto_delete(reminder_msg))  # run async without blocking

    # Wait for user reply
    neo = await bot.listen(message.chat.id)

    if neo.text:
        m = await neo.reply_text("🎙️ **__Processing Your Voice__...**")
        try:
            audio = await convert(neo.text, voice)
            await neo.reply_audio(audio)
            await m.delete()
            audio.close()
        except Exception as e:
            await m.edit(f"❌ Error: {e}")
    else:
        await neo.reply_text("**__Send Me Only Text Buddy__**")

async def auto_delete(msg):
    await asyncio.sleep(4)  # auto delete after 4 seconds
    await msg.delete()
