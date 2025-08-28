import os
import shutil
import pyzipper
import pikepdf
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# ---------------- GLOBALS ----------------
PROCESSED_RESULTS = {}  # {chat_id: {"files": [...], "force_zip": bool, "original_zip_name": str}}
TG_MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB


def get_temp_dir(chat_id, purpose):
    """Create a unique temp directory for each user and purpose."""
    path = os.path.join("temp", f"{purpose}_{chat_id}")
    os.makedirs(path, exist_ok=True)
    return path


# ====================== ADD PASSWORD ======================
@Client.on_message(filters.command("addpass") & filters.reply)
async def add_password(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply("⚠️ Reply to a **PDF or ZIP file** with `/addpass <password>`")

    file_name = message.reply_to_message.document.file_name
    args = message.text.split(" ", 1)
    password = args[1] if len(args) > 1 else None
    if not password:
        return await message.reply("⚠️ Please provide a password.\nUsage: `/addpass yourpassword`")

    status = await message.reply("⏳ Adding password...")
    temp_dir = get_temp_dir(message.chat.id, "addpass")

    try:
        file_path = await message.reply_to_message.download(temp_dir)

        # PDF
        if file_name.lower().endswith(".pdf"):
            protected_path = os.path.join(temp_dir, file_name)
            with pikepdf.open(file_path) as pdf:
                pdf.save(protected_path, encryption=pikepdf.Encryption(owner=password, user=password, R=4))
            await status.delete()
            await message.reply_document(
                protected_path,
                caption=f"🔐 File protected successfully!\nPassword: `{password}`"
            )

        # ZIP
        elif file_name.lower().endswith(".zip"):
            protected_path = os.path.join(temp_dir, file_name)
            with pyzipper.AESZipFile(protected_path, "w", compression=pyzipper.ZIP_DEFLATED,
                                     encryption=pyzipper.WZ_AES) as zf:
                zf.setpassword(password.encode("utf-8"))
                with pyzipper.AESZipFile(file_path) as original_zip:
                    for f in original_zip.namelist():
                        zf.writestr(f, original_zip.read(f))
            await status.delete()
            await message.reply_document(
                protected_path,
                caption=f"🔐 File protected successfully!\nPassword: `{password}`"
            )
        else:
            await status.edit("⚠️ Only PDF and ZIP files are supported.")

    except Exception as e:
        await status.edit(f"⚠️ Error: {e}")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ====================== REMOVE PASSWORD ======================
@Client.on_message(filters.command("removepass") & filters.reply)
async def remove_password(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply("⚠️ Reply to a **PDF or ZIP file** with `/removepass <password>`")

    file_name = message.reply_to_message.document.file_name
    args = message.text.split(" ", 1)
    password = args[1] if len(args) > 1 else None

    status = await message.reply("⏳ Removing password...")
    temp_dir = get_temp_dir(message.chat.id, "unlock")

    try:
        file_path = await message.reply_to_message.download(temp_dir)

        # PDF
        if file_name.lower().endswith(".pdf"):
            unlocked_path = os.path.join(temp_dir, file_name)
            try:
                with pikepdf.open(file_path, password=password) as pdf:
                    pdf.save(unlocked_path)
                if os.path.getsize(unlocked_path) > TG_MAX_FILE_SIZE:
                    return await status.edit("❌ File too large for Telegram (2GB limit).")
                await status.delete()
                await message.reply_document(
                    unlocked_path,
                    caption=f"🔓 File unlocked successfully!\nFilename: `{file_name}`"
                )
            except pikepdf.PasswordError:
                await status.edit("❌ Wrong PDF password or unable to remove.")

        # ZIP
        elif file_name.lower().endswith(".zip"):
            extracted_dir = os.path.join(temp_dir, "extracted")
            os.makedirs(extracted_dir, exist_ok=True)

            try:
                with pyzipper.AESZipFile(file_path) as zf:
                    if password:
                        zf.extractall(path=extracted_dir, pwd=password.encode("utf-8"))
                    else:
                        zf.extractall(path=extracted_dir)
            except Exception:
                return await status.edit("❌ Wrong ZIP password or extraction failed.")

            # Prepare files for sending
            unlocked_files = []
            too_large = False
            for root, _, files in os.walk(extracted_dir):
                for f in files:
                    src = os.path.join(root, f)
                    unlocked_files.append(src)
                    if os.path.getsize(src) > TG_MAX_FILE_SIZE:
                        too_large = True

            # Save processed result
            PROCESSED_RESULTS[message.chat.id] = {
                "files": unlocked_files,
                "force_zip": too_large,
                "original_zip_name": file_name
            }

            buttons = []
            if too_large:
                buttons.append([InlineKeyboardButton("📂 Send as ZIP", callback_data="send_zip")])
                await status.edit("⚠️ Some files exceed 2GB, must send as ZIP.",
                                  reply_markup=InlineKeyboardMarkup(buttons))
            else:
                buttons.append([InlineKeyboardButton("📂 Send as ZIP", callback_data="send_zip")])
                buttons.append([InlineKeyboardButton("📄 Send files separately", callback_data="send_files")])
                await status.edit("✅ ZIP unlocked successfully! Choose how to receive files:",
                                  reply_markup=InlineKeyboardMarkup(buttons))
        else:
            await status.edit("⚠️ Only PDF and ZIP files are supported.")

    except Exception as e:
        await status.edit(f"⚠️ Error: {e}")


# ====================== CALLBACK HANDLER ======================
@Client.on_callback_query(filters.regex("send_zip|send_files"))
async def handle_send_choice(client: Client, callback: CallbackQuery):
    chat_id = callback.message.chat.id
    if chat_id not in PROCESSED_RESULTS:
        return await callback.answer("⚠️ No processed files found.", show_alert=True)

    results = PROCESSED_RESULTS[chat_id]
    choice = callback.data
    temp_dir = get_temp_dir(chat_id, "unlock")  # isolated temp folder

    try:
        if choice == "send_zip":
            zip_name = results.get("original_zip_name", "unlocked_files.zip")
            zip_path = os.path.join(temp_dir, zip_name)
            with pyzipper.AESZipFile(zip_path, "w", compression=pyzipper.ZIP_DEFLATED) as newzip:
                for f in results["files"]:
                    newzip.write(f, arcname=os.path.basename(f))

            await callback.message.reply_document(
                zip_path,
                caption=f"🔓 Here’s your unlocked ZIP!\nFilename: `{zip_name}`"
            )
            os.remove(zip_path)

        elif choice == "send_files":
            if results.get("force_zip"):
                return await callback.answer("⚠️ Some files exceed 2GB. ZIP is required.", show_alert=True)
            for f in results["files"]:
                try:
                    await callback.message.reply_document(
                        f,
                        caption=f"🔓 File unlocked successfully!\nFilename: `{os.path.basename(f)}`"
                    )
                except Exception:
                    pass

    finally:
        # Clean up everything
        shutil.rmtree(temp_dir, ignore_errors=True)
        del PROCESSED_RESULTS[chat_id]
        await callback.answer()
        
