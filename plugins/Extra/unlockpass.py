import os
import pyzipper
import pikepdf
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# --- Setup ---
TEMP_DIR = "temp_files"
os.makedirs(TEMP_DIR, exist_ok=True)

# Track state for interactive password input
WAITING_PASSWORD = {}  # chat_id -> {"file_path": str, "file_name": str, "action": "addpass"|"removepass"}

# --- Helper functions ---
async def add_zip_password(file_path, password, output_path):
    with pyzipper.AESZipFile(file_path) as zip_in:
        with pyzipper.AESZipFile(output_path, 'w', encryption=pyzipper.WZ_AES) as zip_out:
            zip_out.setpassword(password.encode())
            for f in zip_in.namelist():
                zip_out.writestr(f, zip_in.read(f))

async def remove_zip_password(file_path, output_path):
    with pyzipper.AESZipFile(file_path) as zip_in:
        with pyzipper.AESZipFile(output_path, 'w') as zip_out:
            for f in zip_in.namelist():
                zip_out.writestr(f, zip_in.read(f))

async def add_pdf_password(file_path, password, output_path):
    pdf = pikepdf.open(file_path)
    pdf.save(output_path, encryption=pikepdf.Encryption(owner=password, user=password, R=4))
    pdf.close()

async def remove_pdf_password(file_path, output_path, password=None):
    pdf = pikepdf.open(file_path, password=password or "")
    pdf.save(output_path)
    pdf.close()

async def extract_zip(file_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    with pyzipper.AESZipFile(file_path) as zip_in:
        files = zip_in.namelist()
        for f in files:
            zip_in.extract(f, path=output_dir)
    return [os.path.join(output_dir, f) for f in files]

# --- /addpass command ---
@Client.on_message(filters.command("addpass") & filters.reply)
async def addpass_interactive(client: Client, message: Message):
    reply = message.reply_to_message
    if not reply.document:
        await message.reply("❌ Please reply to a PDF or ZIP file to add password.")
        return

    filename = reply.document.file_name
    if not (filename.lower().endswith(".pdf") or filename.lower().endswith(".zip")):
        await message.reply("❌ Unsupported file type! Only PDF and ZIP are allowed.")
        return

    file_path = await reply.download(file_name=TEMP_DIR)
    WAITING_PASSWORD[message.chat.id] = {"file_path": file_path, "file_name": filename, "action": "addpass"}
    await message.reply(f"📌 File `{filename}` received. Please reply with the password you want to set.")

# --- /removepass command ---
@Client.on_message(filters.command("removepass") & filters.reply)
async def removepass_interactive(client: Client, message: Message):
    reply = message.reply_to_message
    if not reply.document:
        await message.reply("❌ Please reply to a PDF or ZIP file to remove password.")
        return

    filename = reply.document.file_name
    if not (filename.lower().endswith(".pdf") or filename.lower().endswith(".zip")):
        await message.reply("❌ Unsupported file type! Only PDF and ZIP are allowed.")
        return

    file_path = await reply.download(file_name=TEMP_DIR)
    WAITING_PASSWORD[message.chat.id] = {"file_path": file_path, "file_name": filename, "action": "removepass"}
    await message.reply(f"📌 File `{filename}` received. Please reply with the password (if PDF) or leave empty to remove it.")

# --- Handle password reply ---
@Client.on_message(filters.text & filters.private)
async def handle_password(client: Client, message: Message):
    if message.chat.id not in WAITING_PASSWORD:
        return

    info = WAITING_PASSWORD.pop(message.chat.id)
    file_path = info["file_path"]
    filename = info["file_name"]
    action = info["action"]
    password = message.text.strip() if message.text.strip() else None
    output_file = os.path.join(TEMP_DIR, f"{'protected' if action=='addpass' else 'unprotected'}_{filename}")

    status_msg = await message.reply(f"⏳ Processing `{filename}`...")

    try:
        if filename.lower().endswith(".zip"):
            if action == "addpass":
                await add_zip_password(file_path, password, output_file)
            else:
                await remove_zip_password(file_path, output_file)
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📂 Break ZIP", callback_data=f"breakzip|{output_file}")]])
        else:  # PDF
            if action == "addpass":
                await add_pdf_password(file_path, password, output_file)
            else:
                await remove_pdf_password(file_path, output_file, password)
            keyboard = None

        await status_msg.edit(f"✅ Done! Sending `{filename}`...")
        await message.reply_document(output_file, caption=f"Action: {action}\nPassword: `{password}`" if password else f"Action: {action}", reply_markup=keyboard)
    except Exception as e:
        await status_msg.edit(f"❌ Error: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(output_file):
            os.remove(output_file)

# --- Break ZIP callback ---
@Client.on_callback_query(filters.regex(r"breakzip\|"))
async def break_zip_callback(client, callback_query: CallbackQuery):
    _, zip_path = callback_query.data.split("|")
    if not os.path.exists(zip_path):
        await callback_query.answer("File not found!", show_alert=True)
        return

    output_dir = zip_path + "_files"
    await callback_query.message.edit_text("📂 Extracting files from ZIP...")

    try:
        files = await extract_zip(zip_path, output_dir)
        for f in files:
            await callback_query.message.reply_document(f)
        await callback_query.message.edit_text("✅ All files sent individually!")
    except Exception as e:
        await callback_query.message.edit_text(f"❌ Error: {e}")
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)
        for f in files:
            if os.path.exists(f):
                os.remove(f)
        if os.path.exists(output_dir):
            os.rmdir(output_dir)
