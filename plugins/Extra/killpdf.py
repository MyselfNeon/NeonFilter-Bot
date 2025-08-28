import os
import shutil
import pyzipper
import pikepdf
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Temporary storage for processed files
PROCESSED_RESULTS = {}  # {chat_id: {"files": [paths], "force_zip": bool}}

# Telegram max upload size (2 GB)
TG_MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024


# ====================== REMOVE PASSWORD COMMAND ======================
@Client.on_message(filters.command("removepass") & filters.reply)
async def remove_password(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply("⚠️ Reply to a **PDF or ZIP file** with `/removepass <password>`")

    file_name = message.reply_to_message.document.file_name
    args = message.text.split(" ", 1)
    password = args[1] if len(args) > 1 else None

    status = await message.reply("⏳ Removing password...")

    try:
        # Download file
        file_path = await message.reply_to_message.download()
        base_dir = "temp_unlock"
        extracted_dir = os.path.join(base_dir, "extracted")
        unlocked_dir = os.path.join(base_dir, "unlocked")
        os.makedirs(extracted_dir, exist_ok=True)
        os.makedirs(unlocked_dir, exist_ok=True)

        # Handle PDF
        if file_name.lower().endswith(".pdf"):
            unlocked_path = os.path.join(unlocked_dir, file_name)
            try:
                with pikepdf.open(file_path, password=password) as pdf:
                    pdf.save(unlocked_path)
                if os.path.getsize(unlocked_path) > TG_MAX_FILE_SIZE:
                    return await status.edit("❌ File too large for Telegram (2GB limit).")
                await status.delete()
                await message.reply_document(
                    unlocked_path,
                    caption="✅ File unlocked successfully!"
                )
            except pikepdf.PasswordError:
                await status.edit("❌ Wrong PDF password or unable to remove.")

        # Handle ZIP
        elif file_name.lower().endswith(".zip"):
            unlocked_files = []
            too_large = False

            try:
                with pyzipper.AESZipFile(file_path) as zf:
                    try:
                        if password:
                            zf.extractall(path=extracted_dir, pwd=password.encode("utf-8"))
                        else:
                            zf.extractall(path=extracted_dir)
                    except RuntimeError:
                        return await status.edit("❌ Wrong ZIP password or extraction failed.")
            except Exception as e:
                return await status.edit(f"❌ ZIP extraction error: {e}")

            # Process extracted files
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

            # Save for callback
            PROCESSED_RESULTS[message.chat.id] = {"files": unlocked_files, "force_zip": too_large}

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

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


# ====================== ADD PASSWORD COMMAND ======================
@Client.on_message(filters.command("addpass") & filters.reply)
async def add_password(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply("⚠️ Reply to a **PDF or ZIP file** with `/addpass <password>`")

    file_name = message.reply_to_message.document.file_name
    args = message.text.split(" ", 1)
    password = args[1] if len(args) > 1 else None
    if not password:
        return await message.reply("⚠️ Please provide a password.\n\nUsage: `/addpass yourpassword`")

    status = await message.reply("⏳ Adding password...")

    try:
        file_path = await message.reply_to_message.download()
        base_dir = "temp_addpass"
        os.makedirs(base_dir, exist_ok=True)

        # PDF case
        if file_name.lower().endswith(".pdf"):
            protected_path = os.path.join(base_dir, file_name)
            with pikepdf.open(file_path) as pdf:
                pdf.save(protected_path, encryption=pikepdf.Encryption(owner=password, user=password, R=4))
            await status.delete()
            await message.reply_document(
                protected_path,
                caption=f"🔐 File protected successfully!\nPassword: `{password}`"
            )

        # ZIP case
        elif file_name.lower().endswith(".zip"):
            protected_path = os.path.join(base_dir, file_name)
            with pyzipper.AESZipFile(protected_path, "w", compression=pyzipper.ZIP_DEFLATED,
                                     encryption=pyzipper.WZ_AES) as zf:
                zf.setpassword(password.encode("utf-8"))   # set password once
                with pyzipper.AESZipFile(file_path) as original_zip:
                    for f in original_zip.namelist():
                        data = original_zip.read(f)
                        zf.writestr(f, data)  # no pwd arg here
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
        shutil.rmtree(base_dir, ignore_errors=True)
        if os.path.exists(file_path):
            os.remove(file_path)


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
        await callback.message.reply_document(new_zip, caption="📂 Here’s your unlocked ZIP!")
        os.remove(new_zip)

    elif choice == "send_files":
        if results.get("force_zip"):
            return await callback.answer("⚠️ Some files exceed 2GB. ZIP is required.", show_alert=True)
        for f in results["files"]:
            try:
                await callback.message.reply_document(f, caption="✅ File unlocked successfully!")
            except:
                pass

    shutil.rmtree("temp_unlock", ignore_errors=True)
    del PROCESSED_RESULTS[chat_id]
    await callback.answer()
    
