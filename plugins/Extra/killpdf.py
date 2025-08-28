import os
import shutil
import pyzipper
import pikepdf
import asyncio
import time
from pyrogram import Client, filters
from pyrogram.types import Message

# ---------------- GLOBALS ----------------
USER_ACTIONS = {}  # {(chat_id, user_id): {"action": str, "file_chat_id": int, "file_msg_id": int, "timestamp": float}}

# ---------------- COMMAND HANDLERS ----------------
@Client.on_message(filters.command("addpass") & filters.reply)
async def add_pass_handler(client: Client, message: Message):
    if not message.reply_to_message.document:
        return await message.reply("⚠️ Please reply to a PDF or ZIP file.")
    USER_ACTIONS[(message.chat.id, message.from_user.id)] = {
        "action": "addpass",
        "file_chat_id": message.chat.id,
        "file_msg_id": message.reply_to_message.id,
        "timestamp": time.time()
    }
    await message.reply("🔐 Please send me the password (just type it, no reply).")

@Client.on_message(filters.command("removepass") & filters.reply)
async def remove_pass_handler(client: Client, message: Message):
    if not message.reply_to_message.document:
        return await message.reply("⚠️ Please reply to a PDF or ZIP file.")
    USER_ACTIONS[(message.chat.id, message.from_user.id)] = {
        "action": "removepass",
        "file_chat_id": message.chat.id,
        "file_msg_id": message.reply_to_message.id,
        "timestamp": time.time()
    }
    await message.reply("🔓 Please send me the password (just type it, no reply).")

# ---------------- PASSWORD LISTENER ----------------
@Client.on_message(filters.text & ~filters.command(["addpass", "removepass"]))
async def password_listener(client: Client, message: Message):
    key = (message.chat.id, message.from_user.id)
    if key not in USER_ACTIONS:
        return

    action_data = USER_ACTIONS.pop(key)
    # Check timeout (2 min)
    if time.time() - action_data["timestamp"] > 120:
        return await message.reply("⌛ Session expired. Please send the command again.")

    password = message.text.strip()
    try:
        orig_msg = await client.get_messages(action_data["file_chat_id"], action_data["file_msg_id"])
        file_path = await orig_msg.download()

        if action_data["action"] == "addpass":
            await process_add_password(message, file_path, password)
        elif action_data["action"] == "removepass":
            await process_remove_password(message, file_path, password)

        os.remove(file_path)
    except Exception as e:
        await message.reply(f"❌ Error: {e}")

# ---------------- PDF & ZIP PROCESSING ----------------
async def process_add_password(message: Message, file_path: str, password: str):
    filename = os.path.basename(file_path)
    name, ext = os.path.splitext(filename)

    if ext.lower() == ".pdf":
        out_file = f"{name}_locked.pdf"
        try:
            with pikepdf.open(file_path) as pdf:
                pdf.save(out_file, encryption=pikepdf.Encryption(owner=password, user=password, R=4))
            await message.reply_document(out_file, caption=f"🔐 PDF protected successfully!\nPassword: `{password}`")
            os.remove(out_file)
        except Exception as e:
            await message.reply(f"❌ Failed to lock PDF: {e}")

    elif ext.lower() == ".zip":
        out_file = f"{name}_locked.zip"
        try:
            with pyzipper.AESZipFile(out_file, 'w', compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as zf:
                zf.setpassword(password.encode())
                zf.write(file_path, filename)
            await message.reply_document(out_file, caption=f"🔐 ZIP protected successfully!\nPassword: `{password}`")
            os.remove(out_file)
        except Exception as e:
            await message.reply(f"❌ Failed to lock ZIP: {e}")
    else:
        await message.reply("⚠️ Only PDF and ZIP files are supported.")

async def process_remove_password(message: Message, file_path: str, password: str):
    filename = os.path.basename(file_path)
    name, ext = os.path.splitext(filename)

    if ext.lower() == ".pdf":
        out_file = f"{name}_unlocked.pdf"
        try:
            with pikepdf.open(file_path, password=password) as pdf:
                pdf.save(out_file)
            await message.reply_document(out_file, caption="🔓 PDF unlocked successfully!")
            os.remove(out_file)
        except Exception as e:
            await message.reply(f"❌ Failed to unlock PDF: {e}")

    elif ext.lower() == ".zip":
        out_dir = f"{name}_unzipped"
        os.makedirs(out_dir, exist_ok=True)
        try:
            with pyzipper.AESZipFile(file_path) as zf:
                zf.pwd = password.encode()
                zf.extractall(out_dir)
            shutil.make_archive(out_dir, 'zip', out_dir)
            await message.reply_document(f"{out_dir}.zip", caption="🔓 ZIP extracted and re-packed!")
            shutil.rmtree(out_dir)
            os.remove(f"{out_dir}.zip")
        except Exception as e:
            await message.reply(f"❌ Failed to unlock ZIP: {e}")
    else:
        await message.reply("⚠️ Only PDF and ZIP files are supported.")
        
