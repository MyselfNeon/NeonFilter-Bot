import os
import shutil
import pyzipper
import pikepdf
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# ---------------- GLOBALS ----------------
PROCESSED_RESULTS = {}  # For sending results after ZIP
USER_ACTIONS = {}       # {chat_id: {"action": "addpass"|"removepass", "file_id": str, "file_name": str}}
TG_MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024


# ---------------- PROGRESS HELPER ----------------
async def send_progress(msg: Message, current, total, task_name="Processing"):
    percent = int(current / total * 100)
    bar_length = 20
    filled_length = int(bar_length * percent // 100)
    bar = "█" * filled_length + "─" * (bar_length - filled_length)
    text = f"{task_name} |{bar}| {percent}% ({current}/{total})"
    try:
        await msg.edit(text)
    except:
        pass


# ---------------- /removepass ----------------
@Client.on_message(filters.command("removepass") & filters.reply)
async def removepass_files(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply("⚠️ Reply to a PDF or ZIP file with `/removepass <password>`")

    args = message.text.split(" ", 1)
    password = args[1] if len(args) > 1 else None
    file_name = message.reply_to_message.document.file_name
    temp_msg = await message.reply("⏳ Downloading file...")

    try:
        file_path = await message.reply_to_message.download()
        await temp_msg.edit("⏳ File downloaded. Processing...")

        base_dir = "temp_removepass"
        extracted_dir = os.path.join(base_dir, "extracted")
        processed_dir = os.path.join(base_dir, "processed")
        os.makedirs(extracted_dir, exist_ok=True)
        os.makedirs(processed_dir, exist_ok=True)

        # ---------------- PDF ----------------
        if file_name.lower().endswith(".pdf"):
            out_path = os.path.join(processed_dir, "unlocked_" + file_name)
            try:
                with pikepdf.open(file_path, password=password) as pdf:
                    pdf.save(out_path)
                await temp_msg.edit("✅ PDF password removed successfully!")
                await message.reply_document(out_path)
            except pikepdf._qpdf.PasswordError:
                await temp_msg.edit("❌ Wrong PDF password or unable to unlock.")

        # ---------------- ZIP ----------------
        elif file_name.lower().endswith(".zip"):
            unlocked_files = []

            # Extract ZIP
            try:
                with pyzipper.AESZipFile(file_path) as zf:
                    if password:
                        zf.extractall(path=extracted_dir, pwd=password.encode())
                    else:
                        zf.extractall(path=extracted_dir)
            except RuntimeError:
                return await temp_msg.edit("❌ Wrong ZIP password or extraction failed.")
            except Exception as e:
                return await temp_msg.edit(f"❌ ZIP extraction error: {e}")

            # Process files inside ZIP
            all_files = []
            for root, _, files in os.walk(extracted_dir):
                for f in files:
                    all_files.append(os.path.join(root, f))

            total_files = len(all_files)
            for idx, f in enumerate(all_files, 1):
                rel_path = os.path.relpath(f, extracted_dir)
                dest_path = os.path.join(processed_dir, rel_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)

                # Unlock PDFs
                if f.lower().endswith(".pdf"):
                    try:
                        with pikepdf.open(f, password=password) as pdf:
                            pdf.save(dest_path)
                    except Exception:
                        shutil.copy(f, dest_path)
                else:
                    shutil.copy(f, dest_path)

                unlocked_files.append(dest_path)
                await send_progress(temp_msg, idx, total_files, "Removing passwords")

            # Save for callback
            PROCESSED_RESULTS[message.chat.id] = {"files": unlocked_files, "force_zip": False}
            buttons = [
                [InlineKeyboardButton("📂 Send as ZIP", callback_data="send_zip")],
                [InlineKeyboardButton("📄 Send files separately", callback_data="send_files")]
            ]
            await temp_msg.edit("✅ ZIP processed! Choose how to receive files:",
                                reply_markup=InlineKeyboardMarkup(buttons))

        else:
            await temp_msg.edit("⚠️ Only PDF and ZIP files are supported.")

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


# ---------------- /addpass ----------------
@Client.on_message(filters.command("addpass") & filters.reply)
async def addpass_files(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply("⚠️ Reply to a PDF or ZIP file to use `/addpass`.")

    USER_ACTIONS[message.chat.id] = {
        "action": "addpass",
        "file_name": message.reply_to_message.document.file_name,
        "file_id": message.reply_to_message.document.file_id
    }
    await message.reply("📝 Send me the password you want to add for this file.")


# ---------------- Handle user password input ----------------
@Client.on_message(filters.text)
async def process_user_password(client: Client, message: Message):
    if message.chat.id not in USER_ACTIONS:
        return

    action_data = USER_ACTIONS.pop(message.chat.id)
    password = message.text
    temp_msg = await message.reply("⏳ Downloading file for processing...")
    file_name = action_data["file_name"]
    file_path = await client.download_media(action_data["file_id"])

    base_dir = "temp_addpass"
    processed_dir = os.path.join(base_dir, "processed")
    extracted_dir = os.path.join(base_dir, "extracted")
    os.makedirs(processed_dir, exist_ok=True)
    os.makedirs(extracted_dir, exist_ok=True)

    try:
        # ---------------- PDF ----------------
        if file_name.lower().endswith(".pdf"):
            out_path = os.path.join(processed_dir, "protected_" + file_name)
            try:
                with pikepdf.open(file_path) as pdf:
                    pdf.save(out_path, encryption=pikepdf.Encryption(owner=password, user=password, R=4))
                await temp_msg.edit("✅ PDF password added successfully!")
                await message.reply_document(out_path)
            except Exception as e:
                await temp_msg.edit(f"❌ Error: {e}")

        # ---------------- ZIP ----------------
        elif file_name.lower().endswith(".zip"):
            # Extract existing ZIP
            with pyzipper.AESZipFile(file_path) as zf:
                zf.extractall(path=extracted_dir)

            all_files = []
            for root, _, files in os.walk(extracted_dir):
                for f in files:
                    all_files.append(os.path.join(root, f))

            total_files = len(all_files)
            new_zip_path = os.path.join(processed_dir, "protected_" + file_name)

            with pyzipper.AESZipFile(new_zip_path, "w", compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as newzip:
                for idx, f in enumerate(all_files, 1):
                    arcname = os.path.relpath(f, extracted_dir)

                    # Preserve internal PDF password
                    if f.lower().endswith(".pdf"):
                        temp_pdf_path = os.path.join(extracted_dir, "temp_" + os.path.basename(f))
                        try:
                            with pikepdf.open(f) as pdf:
                                pdf.save(temp_pdf_path)
                            newzip.write(temp_pdf_path, arcname=arcname)
                            os.remove(temp_pdf_path)
                        except:
                            newzip.write(f, arcname=arcname)
                    else:
                        newzip.write(f, arcname=arcname)

                    newzip.setpassword(password.encode())  # Encrypt ZIP
                    await send_progress(temp_msg, idx, total_files, "Adding password to ZIP")

            # Save processed files for callback
            PROCESSED_RESULTS[message.chat.id] = {"files": all_files, "force_zip": False}

            # Show inline buttons for sending
            buttons = [
                [InlineKeyboardButton("📂 Send as ZIP", callback_data="send_zip")],
                [InlineKeyboardButton("📄 Send files separately", callback_data="send_files")]
            ]
            await temp_msg.edit("✅ ZIP password added! Choose how to receive files:",
                                reply_markup=InlineKeyboardMarkup(buttons))

    finally:
        shutil.rmtree(base_dir, ignore_errors=True)
        if os.path.exists(file_path):
            os.remove(file_path)


# ---------------- CALLBACKS ----------------
@Client.on_callback_query(filters.regex("send_zip|send_files"))
async def handle_send_choice(client: Client, callback: CallbackQuery):
    chat_id = callback.message.chat.id
    if chat_id not in PROCESSED_RESULTS:
        return await callback.answer("⚠️ No processed files found.", show_alert=True)

    results = PROCESSED_RESULTS[chat_id]
    choice = callback.data

    if choice == "send_zip":
        new_zip = "result_files.zip"
        with pyzipper.AESZipFile(new_zip, "w", compression=pyzipper.ZIP_DEFLATED) as newzf:
            for f in results["files"]:
                arcname = os.path.relpath(f, os.path.dirname(f))
                newzf.write(f, arcname=arcname)
        await callback.message.reply_document(new_zip)
        os.remove(new_zip)

    elif choice == "send_files":
        for f in results["files"]:
            try:
                await callback.message.reply_document(f)
            except:
                pass

    # Cleanup
    shutil.rmtree("temp_removepass", ignore_errors=True)
    shutil.rmtree("temp_addpass", ignore_errors=True)
    del PROCESSED_RESULTS[chat_id]
    await callback.answer()
