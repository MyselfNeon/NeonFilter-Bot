from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
import os
import tempfile
import shutil
import asyncio
import time
import pikepdf
import pyzipper

# --- CONFIG ---
BOT = Client("PasswordBot")
user_waiting = {}  # {user_id: {"action": str, "file_msg": Message, "timeout_task": asyncio.Task}}
cache_dir = tempfile.mkdtemp()  # temporary folder for caching files

# --- HELPERS ---
def encrypt_pdf(input_path, output_path, password):
    with pikepdf.open(input_path) as pdf:
        pdf.save(output_path, encryption=pikepdf.Encryption(owner=password, user=password, R=4))

def decrypt_pdf(input_path, output_path, password):
    with pikepdf.open(input_path, password=password) as pdf:
        pdf.save(output_path)

def encrypt_zip(input_path, output_path, password):
    with pyzipper.AESZipFile(output_path, 'w', compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as zf:
        with pyzipper.AESZipFile(input_path, 'r') as old_zip:
            for file in old_zip.namelist():
                data = old_zip.read(file)
                zf.writestr(file, data, compress_type=pyzipper.ZIP_DEFLATED)
        zf.setpassword(password.encode())

def decrypt_zip(input_path, extract_path, password):
    with pyzipper.AESZipFile(input_path) as zf:
        zf.extractall(path=extract_path, pwd=password.encode())

async def schedule_cleanup(file_path, delay=600):
    await asyncio.sleep(delay)
    if os.path.exists(file_path):
        if os.path.isfile(file_path):
            os.remove(file_path)
        else:
            shutil.rmtree(file_path)

async def cancel_request_after_timeout(user_id, timeout, msg):
    await asyncio.sleep(timeout)
    if user_id in user_waiting:
        await msg.reply_text("⏰ Time's up! Request cancelled.")
        user_waiting.pop(user_id, None)

# --- HANDLERS ---
@BOT.on_message(filters.command("killpdf") & filters.reply)
async def killpdf(client, message):
    if not message.reply_to_message.document:
        await message.reply_text("Reply to a PDF or ZIP file!")
        return
    
    file_name = message.reply_to_message.document.file_name.lower()
    if not (file_name.endswith(".pdf") or file_name.endswith(".zip")):
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

    # Cancel previous timeout if exists
    if query.from_user.id in user_waiting:
        user_waiting[query.from_user.id]["timeout_task"].cancel()

    # Start timeout task
    timeout_task = asyncio.create_task(cancel_request_after_timeout(query.from_user.id, 30, query.message))
    user_waiting[query.from_user.id] = {"action": action, "file_msg": msg, "timeout_task": timeout_task}

    if action == "add":
        await query.message.reply_text("Send me the new password to set (30s to reply):", reply_markup=ForceReply())
    else:
        await query.message.reply_text("Send me the current password to remove (30s to reply):", reply_markup=ForceReply())

@BOT.on_message(filters.reply & filters.private)
async def handle_password(client, message):
    user_data = user_waiting.get(message.from_user.id)
    if not user_data:
        return

    # Cancel timeout task
    user_data["timeout_task"].cancel()

    action = user_data["action"]
    file_msg = user_data["file_msg"]
    password = message.text

    # Download file to cache
    file_path = await file_msg.download(file_name=os.path.join(cache_dir, file_msg.document.file_name))
    output_file = os.path.join(cache_dir, f"{os.path.splitext(file_path)[0]}_modified{os.path.splitext(file_path)[1]}")

    try:
        if file_path.lower().endswith(".pdf"):
            if action == "add":
                encrypt_pdf(file_path, output_file, password)
            else:
                decrypt_pdf(file_path, output_file, password)
            await message.reply_document(output_file, caption="✅ Processed PDF")

        elif file_path.lower().endswith(".zip"):
            extract_path = os.path.join(cache_dir, f"{os.path.splitext(file_msg.document.file_name)[0]}_extracted")
            os.makedirs(extract_path, exist_ok=True)
            if action == "add":
                encrypt_zip(file_path, output_file, password)
                await message.reply_document(output_file, caption="✅ Password added to ZIP")
            else:
                decrypt_zip(file_path, extract_path, password)
                # Post-decryption options
                markup = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📦 Send full ZIP", callback_data=f"sendzip|{extract_path}"),
                     InlineKeyboardButton("🗂 Send all files individually", callback_data=f"sendfiles|{extract_path}")]
                ])
                await message.reply_text("Choose how to receive the files:", reply_markup=markup)

        # Schedule cleanup after 10 minutes
        asyncio.create_task(schedule_cleanup(file_path))
        asyncio.create_task(schedule_cleanup(output_file))
    except Exception as e:
        await message.reply_text(f"❌ Failed: {e}")
    finally:
        user_waiting.pop(message.from_user.id, None)

@BOT.on_callback_query(filters.regex(r"send(zip|files)\|"))
async def send_after_unzip(client, query):
    action, path = query.data.split("|")
    if action == "sendzip":
        zip_path = shutil.make_archive(path, 'zip', path)
        await query.message.reply_document(zip_path, caption="✅ Here is the ZIP file")
        asyncio.create_task(schedule_cleanup(zip_path))
    elif action == "sendfiles":
        for file in os.listdir(path):
            file_path = os.path.join(path, file)
            if os.path.isfile(file_path):
                await query.message.reply_document(file_path)
    asyncio.create_task(schedule_cleanup(path))

# --- RUN BOT ---
BOT.run()
