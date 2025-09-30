# audiobook.py
from pyrogram import Client, filters
from pyrogram.types import Message
from fpdf import FPDF
from gtts import gTTS
import tempfile
import os

@Client.on_message(filters.command("audiobook") & filters.reply)
async def audiobook(client: Client, message: Message):
    # Check if the replied message has a PDF
    reply = message.reply_to_message
    if not reply.document or not reply.document.file_name.endswith(".pdf"):
        await message.reply_text("❌ Please reply to a PDF file to convert it into audio.")
        return

    # Download the PDF
    pdf_file = await reply.download()
    
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        
        if not text.strip():
            await message.reply_text("❌ Could not extract text from this PDF.")
            return
        
        # Convert text to speech
        tts = gTTS(text=text, lang="en")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tts.save(tmp.name)
            tmp_file = tmp.name
        
        # Send the audio
        await message.reply_audio(tmp_file, caption="🎧 Here’s your audiobook!")
    
    except Exception as e:
        await message.reply_text(f"❌ Failed to generate audiobook.\nError: {e}")
    
    finally:
        # Cleanup
        if os.path.exists(pdf_file):
            os.remove(pdf_file)
        if 'tmp_file' in locals() and os.path.exists(tmp_file):
            os.remove(tmp_file)
