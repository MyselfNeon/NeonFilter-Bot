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
    audio.name = "tts.mp3"

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

    vj = await bot.ask(
        chat_id=message.from_user.id, 
        text="Now send me your text."
    )

    if vj.text:
        m = await vj.reply_text("🎙️ Processing your voice...")
        try:
            audio = await convert(vj.text, voice)
            await vj.reply_audio(audio)
            await m.delete()
            audio.close()
        except Exception as e:
            await m.edit(f"❌ Error: {e}")
    else:
        await vj.reply_text("Send me only text Buddy.")
