# audiobook.py
from pyrogram import Client, filters
from pyrogram.types import Message
from gtts import gTTS
import tempfile
import os
from PyPDF2 import PdfReader  # only this is needed for reading PDFs

@Client.on_message(filters.command("audiobook") & filters.reply)
async def audiobook(client: Client, message: Message):
    reply = message.reply_to_message
    if not reply.document or not reply.document.file_name.endswith(".pdf"):
        await message.reply_text("❌ Please reply to a PDF file to convert it into audio.")
        return

    pdf_file = await reply.download()
    
    try:
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"

        if not text.strip():
            await message.reply_text("❌ Could not extract text from this PDF.")
            return

        tts = gTTS(text=text, lang="en")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tts.save(tmp.name)
            tmp_file = tmp.name

        await message.reply_audio(tmp_file, caption="🎧 Here’s your audiobook!")

    except Exception as e:
        await message.reply_text(f"❌ Failed to generate audiobook.\nError: {e}")

    finally:
        if os.path.exists(pdf_file):
            os.remove(pdf_file)
        if 'tmp_file' in locals() and os.path.exists(tmp_file):
            os.remove(tmp_file)
