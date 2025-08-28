import os
import zipfile
import shutil
import pikepdf
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# rarfile for RAR support
try:
    import rarfile
    RAR_AVAILABLE = True
except ImportError:
    RAR_AVAILABLE = False


# Store processed files temporarily for callback handling
PROCESSED_RESULTS = {}  # {chat_id: {"files": [paths], "force_zip": bool}}

# Telegram max upload size (2 GB = 2 * 1024 * 1024 * 1024 bytes)
TG_MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024


@Client.on_message(filters.command("unlock") & filters.reply)
async def unlock_files(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply("⚠️ Reply to a **PDF, ZIP, or RAR file** with `/unlock [password]`")

    file_name = message.reply_to_message.document.file_name
    args = message.text.split(" ", 1)
    password = args[1] if len(args) > 1 else None  # optional password

    try:
        # Download file
        file_path = await message.reply_to_message.download()
        base_dir = "temp_unlock"
        extracted_dir = os.path.join(base_dir, "extracted")
        unlocked_dir = os.path.join(base_dir, "unlocked")

        os.makedirs(base_dir, exist_ok=True)
        os.makedirs(unlocked_dir, exist_ok=True)

        if file_name.endswith(".pdf"):
            unlocked_path = os.path.join(unlocked_dir, "unlocked_" + file_name)
            try:
                if password:
                    with pikepdf.open(file_path, password=password) as pdf:
                        pdf.save(unlocked_path)
                else:
                    with pikepdf.open(file_path) as pdf:
                        pdf.save(unlocked_path)

                if os.path.getsize(unlocked_path) > TG_MAX_FILE_SIZE:
                    return await message.reply("❌ Unlocked file is larger than Telegram's 2GB limit. Please split it manually.")

                await message.reply_document(unlocked_path, caption="✅ PDF unlocked successfully!")
            except pikepdf._qpdf.PasswordError:
                await message.reply("❌ PDF is password-protected. Please provide the correct password.")

        elif file_name.endswith(".zip") or file_name.endswith(".rar"):
            os.makedirs(extracted_dir, exist_ok=True)
            extracted_ok = False

            if file_name.endswith(".zip"):
                try:
                    with zipfile.ZipFile(file_path) as zf:
                        if password:
                            zf.extractall(path=extracted_dir, pwd=password.encode("utf-8"))
                        else:
                            zf.extractall(path=extracted_dir)
                    extracted_ok = True
                except RuntimeError:
                    return await message.reply("❌ Wrong ZIP password or extraction failed.")

            elif file_name.endswith(".rar"):
                if not RAR_AVAILABLE:
                    return await message.reply("⚠️ RAR support not available. Install `rarfile` & unrar/unar.")
                try:
                    with rarfile.RarFile(file_path) as rf:
                        if password:
                            rf.extractall(path=extracted_dir, pwd=password)
                        else:
                            rf.extractall(path=extracted_dir)
                    extracted_ok = True
                except rarfile.PasswordRequired:
                    return await message.reply("❌ RAR file needs a password. Provide it like:\n/unlock mypassword")
                except Exception:
                    return await message.reply("⚠️ Could not extract RAR.")

            if not extracted_ok:
                return await message.reply("⚠️ Could not extract archive.")

            unlocked_files = []
            too_large = False

            # Walk through all files (nested too)
            for root, _, files in os.walk(extracted_dir):
                for f in files:
                    src_path = os.path.join(root, f)
                    rel_path = os.path.relpath(src_path, extracted_dir)
                    dest_path = os.path.join(unlocked_dir, rel_path)

                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

                    if f.endswith(".pdf"):
                        try:
                            if password:
                                with pikepdf.open(src_path, password=password) as pdf:
                                    pdf.save(dest_path)
                            else:
                                with pikepdf.open(src_path) as pdf:
                                    pdf.save(dest_path)
                        except pikepdf._qpdf.PasswordError:
                            shutil.copy(src_path, dest_path)  # keep original if not unlockable
                    else:
                        shutil.copy(src_path, dest_path)

                    unlocked_files.append(dest_path)

                    # Check size limit
                    if os.path.getsize(dest_path) > TG_MAX_FILE_SIZE:
                        too_large = True

            # Save for later user choice
            PROCESSED_RESULTS[message.chat.id] = {"files": unlocked_files, "force_zip": too_large}

            if too_large:
                await message.reply(
                    "⚠️ Some files exceed 2GB, they cannot be sent individually.\n📂 Sending as ZIP is required.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📂 Send as ZIP", callback_data="send_zip")]
                    ])
                )
            else:
                await message.reply(
                    "✅ Archive processed! Choose how to receive files:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📂 Send as ZIP", callback_data="send_zip")],
                        [InlineKeyboardButton("📄 Send files separately", callback_data="send_files")]
                    ])
                )

        else:
            await message.reply("⚠️ Only PDF, ZIP, and RAR files are supported.")

    except Exception as e:
        await message.reply(f"⚠️ Error: {e}")

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@Client.on_callback_query(filters.regex("send_zip|send_files"))
async def handle_send_choice(client: Client, callback: CallbackQuery):
    chat_id = callback.message.chat.id
    if chat_id not in PROCESSED_RESULTS:
        return await callback.answer("⚠️ No processed files found.", show_alert=True)

    choice = callback.data
    results = PROCESSED_RESULTS[chat_id]

    if choice == "send_zip":
        new_zip = "unlocked_files.zip"
        with zipfile.ZipFile(new_zip, "w", zipfile.ZIP_DEFLATED) as newzf:
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
                await callback.message.reply_document(f)
            except:
                pass

    # Cleanup after sending
    shutil.rmtree("temp_unlock", ignore_errors=True)
    del PROCESSED_RESULTS[chat_id]

    await callback.answer()
