# ---------------------------------------------------
# File Name: Super-TTS.2.py
# Author: MyselfNeon
# Original Repo: https://github.com/MyselfNeon/NeonFilter-Bot
# GitHub: https://github.com/MyselfNeon/
# Telegram: https://t.me/MyelfNeon
# ---------------------------------------------------

# --- Imports ---
import asyncio
import os
import edge_tts
from io import BytesIO
from pyrogram import Client, filters, enums
from pyrogram.types import Message

# --- Configuration ---
DEFAULT_VOICE = "en-US-AriaNeural"

VOICE_MAP = {
    # English
    "en": "en-US-AriaNeural",       # US Female
    "en-m": "en-US-GuyNeural",      # US Male
    "en-uk": "en-GB-SoniaNeural",   # UK Female
    
    # Hindi
    "hi": "hi-IN-SwaraNeural",      # Hindi Female
    "hi-m": "hi-IN-MadhurNeural",   # Hindi Male
    
    # Spanish
    "es": "es-ES-ElviraNeural",     # Spanish Female
    "es-m": "es-ES-AlvaroNeural",   # Spanish Male
    
    # French
    "fr": "fr-FR-DeniseNeural",     # French Female
    "fr-m": "fr-FR-HenriNeural",    # French Male
    
    # Others
    "jp": "ja-JP-NanamiNeural",     # Japanese
    "kr": "ko-KR-SunHiNeural",      # Korean
    "ru": "ru-RU-SvetlanaNeural",   # Russian
}

# --- Conversion Engine ---
async def generate_tts(text: str, voice: str) -> BytesIO:
    """Generates audio from text using Edge-TTS."""
    audio_fp = BytesIO()
    audio_fp.name = "voice_msg.mp3"  # Telegram needs a filename

    communicate = edge_tts.Communicate(text, voice)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_fp.write(chunk["data"])

    audio_fp.seek(0)
    return audio_fp

# --- Handlers ---
@Client.on_message(filters.command(["tts", "speak"]))
async def tts_handler(client: Client, message: Message):
    # 1. Parse Arguments
    args = message.command[1:] if len(message.command) > 1 else []
    
    target_voice = DEFAULT_VOICE
    target_text = None
    
    # Check if first arg is a voice code (e.g., /tts hi Hello)
    if args and args[0].lower() in VOICE_MAP:
        target_voice = VOICE_MAP[args[0].lower()]
        # If there is text after the code, capture it
        if len(args) > 1:
            target_text = " ".join(args[1:])
    elif args:
        # No voice code, assume all args are text (Default voice)
        target_text = " ".join(args)

    # 2. Check for Reply (Priority over args if args are empty)
    if not target_text and message.reply_to_message:
        if message.reply_to_message.text:
            target_text = message.reply_to_message.text
        elif message.reply_to_message.caption:
            target_text = message.reply_to_message.caption

    # 3. Interactive Mode (If no text found yet)
    if not target_text:
        # Send Helper Menu
        help_msg = await message.reply_text(
            "**🗣️ TTS Voice Menu**\n\n"
            "**Use Codes:**\n"
            "`en` / `en-m` - English (US)\n"
            "`hi` / `hi-m` - Hindi\n"
            "`es` / `fr` / `jp` - Others\n\n"
            "__👇 Send your text now...__"
        )
        
        try:
            # Requires: pyromod or similar 'listen' capability
            if hasattr(client, "listen"):
                user_response = await client.listen(message.chat.id, timeout=30)
                if user_response and user_response.text:
                    target_text = user_response.text
                    await user_response.delete() # Cleanup user text
                    await help_msg.delete()      # Cleanup menu
                else:
                    return await help_msg.edit("**❌ Time up! Try again.**")
            else:
                return await help_msg.edit("**❌ Usage:** `/tts [code] [text]` OR Reply to a message.")
                
        except Exception as e:
            return await help_msg.edit(f"**❌ Error:** {e}")

    # 4. Final Validation
    if not target_text:
        return await message.reply_text("**❌ No text provided to speak!**")

    if len(target_text) > 4000:
        return await message.reply_text("**❌ Text is too long! (Max 4000 chars)**")

    # 5. Processing
    status_msg = await message.reply_text("🎙️ **Synthesizing Audio...**")
    await client.send_chat_action(message.chat.id, enums.ChatAction.RECORD_AUDIO)

    try:
        audio_file = await generate_tts(target_text, target_voice)
        
        # Determine caption
        v_name = next((k for k, v in VOICE_MAP.items() if v == target_voice), "Custom")
        caption = f"**🗣️ Voice:** `{v_name.upper()}`\n**👤 Requested by:** {message.from_user.mention}"

        await message.reply_audio(
            audio=audio_file,
            caption=caption,
            title="Neon TTS",
            performer=v_name.upper()
        )
        await status_msg.delete()
        audio_file.close()

    except Exception as e:
        await status_msg.edit_text(f"**❌ TTS Error:** `{str(e)}`")

# MyselfNeon
# Don't Remove Credit 🥺
# Telegram Channel @NeonFiles
