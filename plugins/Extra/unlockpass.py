import os
import shutil
import pyzipper
import pikepdf
import asyncio
import time
import hashlib
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# -------------------------------
# TEMP STORAGE
# -------------------------------
PROCESSED_RESULTS = {}  # chat_id: {"files": [...], "force_zip": bool, "original_zip": str, "task": asyncio.Task}
UNLOCKED_HASHES = set()  # SHA256 of unlocked PDFs

TG_MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024
AUTO_DELETE_MINUTES = 10
MAX_PDFS = 50
MAX_FILE_SIZE_WARN = 500 * 1024 * 1024

# -------------------------------
# HELPERS
# -------------------------------
def progress_bar(current, total, length=20):
    filled = int(current / total * length)
    empty = length - filled
    return "▰" * filled + "▱" * empty

def sha256(file_path):
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()

async def auto_cleanup(chat_id):
    await asyncio.sleep(AUTO_DELETE_MINUTES * 60)
    if chat_id in PROCESSED_RESULTS:
        shutil.rmtree("temp_files", ignore_errors=True)
        del PROCESSED_RESULTS[chat_id]

# -------------------------------
# UNLOCK COMMAND
# -------------------------------
@Client.on_message(filters.command("unlock") & filters.reply)
async def unlock_files(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply("⚠️ Reply to a **PDF or ZIP file** with `/unlock <password>`")

    file_name = message.reply_to_message.document.file_name
    args = message.text.split(" ", 1)
    if len(args) < 2:
        return await message.reply("❌ Usage: /unlock <password>")

    password = args[1]
    if message.chat.id in PROCESSED_RESULTS:
        return await message.reply("⚠️ You already have a processing task. Wait until it finishes or times out.")

    try:
        file_path = await message.reply_to_message.download()
        base_dir = "temp_files"
        extracted_dir = os.path.join(base_dir, "extracted")
        unlocked_dir = os.path.join(base_dir, "unlocked")
        os.makedirs(extracted_dir, exist_ok=True)
        os.makedirs(unlocked_dir, exist_ok=True)

        # ---------------- PDF ----------------
        if file_name.endswith(".pdf"):
            file_hash = sha256(file_path)
            if file_hash in UNLOCKED_HASHES:
                return await message.reply("⚡ PDF already unlocked before. Skipping.")
            unlocked_path = os.path.join(unlocked_dir, "unlocked_" + file_name)
            try:
                with pikepdf.open(file_path, password=password) as pdf:
                    pdf.save(unlocked_path)
                UNLOCKED_HASHES.add(file_hash)
                if os.path.getsize(unlocked_path) > TG_MAX_FILE_SIZE:
                    return await message.reply("❌ File too large for Telegram (2GB limit).")
                await message.reply_document(unlocked_path, caption="✅ PDF unlocked successfully!")
            except pikepdf._qpdf.PasswordError:
                await message.reply("❌ Wrong PDF password or unable to unlock.")

        # ---------------- ZIP ----------------
        elif file_name.endswith(".zip"):
            unlocked_files = []
            too_large = False

            try:
                with pyzipper.AESZipFile(file_path) as zf:
                    if zf.needs_password():
                        zf.pwd = password.encode("utf-8")
                    zf.extractall(extracted_dir)
            except RuntimeError:
                return await message.reply("❌ Wrong ZIP password or extraction failed.")
            except Exception as e:
                return await message.reply(f"❌ ZIP extraction error: {e}")

            pdf_list = []
            for root, _, files in os.walk(extracted_dir):
                for f in files:
                    if f.endswith(".pdf"):
                        pdf_list.append(os.path.join(root, f))

            if len(pdf_list) == 0:
                return await message.reply("⚠️ No PDFs found in this ZIP.")
            if len(pdf_list) > MAX_PDFS:
                return await message.reply(f"⚠️ Too many PDFs ({len(pdf_list)}) in ZIP. Max allowed: {MAX_PDFS}.")

            total_pdfs = len(pdf_list)
            start_time = time.time()
            status_msg = await message.reply(f"🔓 Unlocking PDFs... 0/{total_pdfs} unlocked\nProgress: {progress_bar(0, total_pdfs)} 0%")

            for idx, pdf_path in enumerate(pdf_list, start=1):
                rel_path = os.path.relpath(pdf_path, extracted_dir)
                dest_path = os.path.join(unlocked_dir, rel_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)

                file_hash = sha256(pdf_path)
                if file_hash in UNLOCKED_HASHES:
                    unlocked_files.append(dest_path)
                else:
                    try:
                        with pikepdf.open(pdf_path, password=password) as pdf:
                            pdf.save(dest_path)
                        UNLOCKED_HASHES.add(file_hash)
                    except Exception:
                        shutil.copy(pdf_path, dest_path)
                    unlocked_files.append(dest_path)

                if os.path.getsize(dest_path) > TG_MAX_FILE_SIZE:
                    too_large = True

                elapsed = time.time() - start_time
                avg_time = elapsed / idx
                remaining = avg_time * (total_pdfs - idx)
                percent = int(idx / total_pdfs * 100)
                await status_msg.edit_text(
                    f"🔓 Unlocking PDFs... {idx}/{total_pdfs} unlocked\n"
                    f"Progress: {progress_bar(idx, total_pdfs)} {percent}%\n"
                    f"⏳ ETA: {int(remaining)}s"
                )

            task = asyncio.create_task(auto_cleanup(message.chat.id))
            PROCESSED_RESULTS[message.chat.id] = {
                "files": unlocked_files,
                "force_zip": too_large,
                "original_zip": file_name,
                "task": task
            }

            buttons = []
            if too_large:
                buttons.append([InlineKeyboardButton("📂 Get Unlocked ZIP", callback_data="send_zip")])
            else:
                buttons.append([
                    InlineKeyboardButton("📂 Get Unlocked ZIP", callback_data="send_zip"),
                    InlineKeyboardButton("📄 Get Unlocked PDFs", callback_data="send_files")
                ])
            await status_msg.edit_text(f"✅ All PDFs processed! Choose how to receive:", reply_markup=InlineKeyboardMarkup(buttons))

        else:
            await message.reply("⚠️ Only PDF and ZIP files are supported.")

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

# -------------------------------
# NEWPASS COMMAND
# -------------------------------
@Client.on_message(filters.command("newpass") & filters.reply)
async def add_password(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply("⚠️ Reply to a **PDF or ZIP file** with `/newpass <newpassword>`")

    args = message.text.split(" ", 1)
    if len(args) < 2:
        return await message.reply("❌ Usage: /newpass <newpassword>")

    new_pass = args[1]
    file_path = await message.reply_to_message.download()
    file_name = message.reply_to_message.document.file_name
    base_dir = "temp_newpass"
    output_dir = os.path.join(base_dir, "output")
    os.makedirs(output_dir, exist_ok=True)

    try:
        if file_name.endswith(".pdf"):
            out_file = os.path.join(output_dir, "protected_" + file_name)
            with pikepdf.open(file_path) as pdf:
                pdf.save(out_file, encryption=pikepdf.Encryption(owner=new_pass, user=new_pass, R=4))
            await message.reply_document(out_file, caption=f"✅ PDF is now protected with password: `{new_pass}`")

        elif file_name.endswith(".zip"):
            extracted_dir = os.path.join(base_dir, "extracted")
            os.makedirs(extracted_dir, exist_ok=True)
            with pyzipper.AESZipFile(file_path) as zf:
                zf.extractall(extracted_dir)
            new_zip_path = os.path.join(output_dir, f"protected_{file_name}")
            with pyzipper.AESZipFile(new_zip_path, "w", compression=pyzipper.ZIP_DEFLATED) as newzf:
                newzf.setpassword(new_pass.encode("utf-8"))
                for root, _, files in os.walk(extracted_dir):
                    for f in files:
                        full_path = os.path.join(root, f)
                        arcname = os.path.relpath(full_path, extracted_dir)
                        newzf.write(full_path, arcname=arcname)
            await message.reply_document(new_zip_path, caption=f"✅ ZIP is now protected with password: `{new_pass}`")

        else:
            await message.reply("⚠️ Only PDF and ZIP files are supported.")

    finally:
        shutil.rmtree(base_dir, ignore_errors=True)
        if os.path.exists(file_path):
            os.remove(file_path)
