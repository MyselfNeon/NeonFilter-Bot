from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
import os
from PyPDF2 import PdfReader, PdfWriter
from zipfile import ZipFile, ZIP_DEFLATED

# --- CONFIG ---
BOT = Client("PasswordBot")  # your bot session

# Temporary storage for users waiting to provide password
user_waiting = {}

# --- HELPERS ---
def encrypt_pdf(input_path, output_path, password):
    reader = PdfReader(input_path)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(password)
    with open(output_path, "wb") as f:
        writer.write(f)

def decrypt_pdf(input_path, output_path, password):
    reader = PdfReader(input_path)
    if reader.is_encrypted:
        reader.decrypt(password)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    with open(output_path, "wb") as f:
        writer.write(f)

def encrypt_zip(input_path, output_path, password):
    with ZipFile(output_path, "w", ZIP_DEFLATED) as zipf:
        with ZipFile(input_path, "r") as old_zip:
            for file in old_zip.namelist():
                data = old_zip.read(file)
                zipf.writestr(file, data, compress_type=ZIP_DEFLATED)
    # Note: Standard zipfile module cannot set password directly for writing
    # You can use pyminizip for actual password protection if needed

def decrypt_zip(input_path, output_path, password):
    with ZipFile(input_path, "r") as zipf:
        zipf.extractall(path=output_path, pwd=password.encode())

# --- HANDLERS ---
@BOT.on_message(filters.command("killpdf") & filters.reply)
async def killpdf(client, message):
    if not message.reply_to_message.document:
        await message.reply_text("Reply to a PDF or ZIP file!")
        return
    
    file_type = message.reply_to_message.document.file_name.lower()
    if not (file_type.endswith(".pdf") or file_type.endswith(".zip")):
        await message.reply_text("Only PDF or ZIP files are supported!")
        return

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔒 Add Password", callback_data=f"add|{message.reply_to_message.message_id}"),
         InlineKeyboardButton("🔓 Remove Password", callback_data=f"remove|{message.reply_to_message.message_id}")]
    ])
    await message.reply_text("Choose an action:", reply_markup=markup)

@BOT.on_callback_query()
async def callback(client, query):
    action, msg_id = query.data.split("|")
    msg = await client.get_messages(query.message.chat.id, int(msg_id))
    user_waiting[query.from_user.id] = {"action": action, "file_msg": msg}

    if action == "add":
        await query.message.reply_text("Send me the new password to set:", reply_markup=ForceReply())
    else:
        await query.message.reply_text("Send me the current password to remove:", reply_markup=ForceReply())

@BOT.on_message(filters.reply & filters.private)
async def handle_password(client, message):
    user_data = user_waiting.get(message.from_user.id)
    if not user_data:
        return

    action = user_data["action"]
    file_msg = user_data["file_msg"]
    password = message.text

    # Download the file
    file_path = await file_msg.download()
    output_file = f"{os.path.splitext(file_path)[0]}_modified{os.path.splitext(file_path)[1]}"

    try:
        if file_path.lower().endswith(".pdf"):
            if action == "add":
                encrypt_pdf(file_path, output_file, password)
            else:
                decrypt_pdf(file_path, output_file, password)
        elif file_path.lower().endswith(".zip"):
            if action == "add":
                encrypt_zip(file_path, output_file, password)
            else:
                decrypt_zip(file_path, f"{output_file}_extracted", password)
        await message.reply_document(output_file, caption="Here is your processed file ✅")
    except Exception as e:
        await message.reply_text(f"❌ Failed: {e}")
    finally:
        # Clean up
        os.remove(file_path)
        if os.path.exists(output_file):
            os.remove(output_file)
        user_waiting.pop(message.from_user.id, None)

# --- RUN BOT ---
BOT.run()
