import os
import shutil
import pyzipper
import pikepdf
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Temporary storage for processed files & actions
PROCESSED_RESULTS = {}  # {chat_id: {"files": [paths], "force_zip": bool}}
USER_ACTIONS = {}       # {chat_id: {"action": "addpass"/"removepass", "file_id": str, "file_name": str}}

TG_MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB


# ====================== STEP 1: COMMAND (ASK FOR PASSWORD) ======================
@Client.on_message(filters.command(["addpass", "removepass"]) & filters.reply)
async def ask_password(_: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply("⚠️ Reply to a **PDF or ZIP file** with `/addpass` or `/removepass`")

    file_id = message.reply_to_message.id
    file_name = message.reply_to_message.document.file_name
    action = message.text.split()[0].lstrip("/")

    USER_ACTIONS[message.chat.id] = {
        "action": action,
        "file_id": file_id,
        "file_name": file_name
    }

    await message.reply("🔑 Please reply with the password for this file.")


# ====================== STEP 2: PASSWORD REPLY ======================
@Client.on_message(filters.reply)
async def process_password(client: Client, message: Message):
    chat_id = message.chat.id
    if chat_id not in USER_ACTIONS:
        return  # ignore normal replies

    action_data = USER_ACTIONS[chat_id]
    password = message.text.strip()

    # Ensure this reply is to the same file
    if not message.reply_to_message or message.reply_to_message.id != action_data["file_id"]:
        return await message.reply("⚠️ Please reply to the same file message with the password.")

    file_name = action_data["file_name"]
    action = action_data["action"]

    status = await message.reply("⏳ Processing...")

    try:
        file_path = await message.reply_to_message.download()

        if action == "removepass":
            # ========== REMOVE PASSWORD ==========
            base_dir = "temp_unlock"
            extracted_dir = os.path.join(base_dir, "extracted")
            unlocked_dir = os.path.join(base_dir, "unlocked")
            os.makedirs(extracted_dir, exist_ok=True)
            os.makedirs(unlocked_dir, exist_ok=True)

            if file_name.lower().endswith(".pdf"):
                unlocked_path = os.path.join(unlocked_dir, "unlocked_" + file_name)
                try:
                    with pikepdf.open(file_path, password=password) as pdf:
                        pdf.save(unlocked_path)
                    if os.path.getsize(unlocked_path) > TG_MAX_FILE_SIZE:
                        return await status.edit("❌ File too large for Telegram (2GB limit).")
                    await status.delete()
                    await message.reply_document(unlocked_path, caption="✅ PDF password removed successfully!")
                except pikepdf._qpdf.PasswordError:
                    await status.edit("❌ Wrong PDF password or unable to remove.")

            elif file_name.lower().endswith(".zip"):
                unlocked_files = []
                too_large = False
                try:
                    with pyzipper.AESZipFile(file_path) as zf:
                        zf.extractall(path=extracted_dir, pwd=password.encode("utf-8"))
                except Exception:
                    return await status.edit("❌ Wrong ZIP password or extraction failed.")

                for root, _, files in os.walk(extracted_dir):
                    for f in files:
                        src_path = os.path.join(root, f)
                        rel_path = os.path.relpath(src_path, extracted_dir)
                        dest_path = os.path.join(unlocked_dir, rel_path)
                        os.makedirs(os.path.dirname(dest_path), exist_ok=True)

                        if f.lower().endswith(".pdf"):
                            try:
                                with pikepdf.open(src_path, password=password) as pdf:
                                    pdf.save(dest_path)
                            except Exception:
                                shutil.copy(src_path, dest_path)
                        else:
                            shutil.copy(src_path, dest_path)

                        unlocked_files.append(dest_path)
                        if os.path.getsize(dest_path) > TG_MAX_FILE_SIZE:
                            too_large = True

                PROCESSED_RESULTS[chat_id] = {"files": unlocked_files, "force_zip": too_large}

                buttons = [[InlineKeyboardButton("📂 Send as ZIP", callback_data="send_zip")]]
                if not too_large:
                    buttons.append([InlineKeyboardButton("📄 Send files separately", callback_data="send_files")])

                await status.edit("✅ ZIP processed! Choose how to receive files:",
                                  reply_markup=InlineKeyboardMarkup(buttons))
            else:
                await status.edit("⚠️ Only PDF and ZIP files are supported.")

        elif action == "addpass":
            # ========== ADD PASSWORD ==========
            base_dir = "temp_addpass"
            os.makedirs(base_dir, exist_ok=True)

            if file_name.lower().endswith(".pdf"):
                protected_path = os.path.join(base_dir, "protected_" + file_name)
                with pikepdf.open(file_path) as pdf:
                    pdf.save(protected_path, encryption=pikepdf.Encryption(owner=password, user=password, R=4))
                await status.delete()
                await message.reply_document(protected_path, caption=f"🔐 PDF protected successfully!\nPassword: `{password}`")

            elif file_name.lower().endswith(".zip"):
                protected_path = os.path.join(base_dir, "protected_" + file_name)
                with pyzipper.AESZipFile(protected_path, "w", compression=pyzipper.ZIP_DEFLATED,
                                         encryption=pyzipper.WZ_AES) as zf:
                    with pyzipper.AESZipFile(file_path) as original_zip:
                        for f in original_zip.namelist():
                            data = original_zip.read(f)
                            zf.writestr(f, data, pwd=password.encode("utf-8"))
                await status.delete()
                await message.reply_document(protected_path, caption=f"🔐 ZIP protected successfully!\nPassword: `{password}`")
            else:
                await status.edit("⚠️ Only PDF and ZIP files are supported.")

    except Exception as e:
        await status.edit(f"⚠️ Error: {e}")

    finally:
        # cleanup
        if os.path.exists(file_path):
            os.remove(file_path)
        USER_ACTIONS.pop(chat_id, None)


# ====================== CALLBACK HANDLER ======================
@Client.on_callback_query(filters.regex("send_zip|send_files"))
async def handle_send_choice(client: Client, callback: CallbackQuery):
    chat_id = callback.message.chat.id
    if chat_id not in PROCESSED_RESULTS:
        return await callback.answer("⚠️ No processed files found.", show_alert=True)

    results = PROCESSED_RESULTS[chat_id]
    choice = callback.data

    if choice == "send_zip":
        new_zip = "unlocked_files.zip"
        with pyzipper.AESZipFile(new_zip, "w", compression=pyzipper.ZIP_DEFLATED) as newzf:
            for f in results["files"]:
                arcname = os.path.relpath(f, "temp_unlock/unlocked")
                newzf.write(f, arcname=arcname)
        await callback.message.reply_document(new_zip, caption="📂 Here’s your ZIP without password!")
        os.remove(new_zip)

    elif choice == "send_files":
        if results.get("force_zip"):
            return await callback.answer("⚠️ Some files exceed 2GB. ZIP is required.", show_alert=True)
        for f in results["files"]:
            try:
                await callback.message.reply_document(f)
            except:
                pass

    shutil.rmtree("temp_unlock", ignore_errors=True)
    del PROCESSED_RESULTS[chat_id]
    await callback.answer()
    
