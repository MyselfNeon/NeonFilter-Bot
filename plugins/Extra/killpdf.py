import os
import shutil
import pyzipper
import pikepdf
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Store processed files temporarily for callback handling
PROCESSED_RESULTS = {}  # {chat_id: {"files": [paths], "force_zip": bool}}

# Telegram max upload size (2 GB)
TG_MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024


@Client.on_message(filters.command("unlock") & filters.reply)
async def unlock_files(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply("⚠️ Reply to a **PDF or ZIP file** with `/unlock <password>`")

    file_name = message.reply_to_message.document.file_name
    args = message.text.split(" ", 1)

    # Check if password is provided
    if len(args) < 2:
        return await message.reply("❌ Usage: /unlock <password>")

    password = args[1]

    try:
        # Download file
        file_path = await message.reply_to_message.download()
        base_dir = "temp_unlock"
        extracted_dir = os.path.join(base_dir, "extracted")
        unlocked_dir = os.path.join(base_dir, "unlocked")

        os.makedirs(extracted_dir, exist_ok=True)
        os.makedirs(unlocked_dir, exist_ok=True)

        # Single PDF
        if file_name.endswith(".pdf"):
            unlocked_path = os.path.join(unlocked_dir, "unlocked_" + file_name)
            try:
                with pikepdf.open(file_path, password=password) as pdf:
                    pdf.save(unlocked_path)
                if os.path.getsize(unlocked_path) > TG_MAX_FILE_SIZE:
                    return await message.reply("❌ File too large for Telegram (2GB limit).")
                await message.reply_document(unlocked_path, caption="✅ PDF unlocked successfully!")
            except pikepdf._qpdf.PasswordError:
                await message.reply("❌ Wrong PDF password or unable to unlock.")

        # ZIP archive
        elif file_name.endswith(".zip"):
            unlocked_files = []
            too_large = False

            os.makedirs(extracted_dir, exist_ok=True)

            # Extract ZIP (with password if required)
            try:
                with pyzipper.AESZipFile(file_path) as zf:
                    if zf.needs_password():
                        zf.pwd = password.encode("utf-8")
                    zf.extractall(extracted_dir)
            except RuntimeError:
                return await message.reply("❌ Wrong ZIP password or extraction failed.")
            except Exception as e:
                return await message.reply(f"❌ ZIP extraction error: {e}")

            # Walk through all files
            for root, _, files in os.walk(extracted_dir):
                for f in files:
                    src_path = os.path.join(root, f)
                    rel_path = os.path.relpath(src_path, extracted_dir)
                    dest_path = os.path.join(unlocked_dir, rel_path)
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

                    if f.endswith(".pdf"):
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

            # Decide what keyboard to show
            if too_large:
                await message.reply(
                    "⚠️ Some files exceed 2GB, must send as ZIP.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📂 Send as ZIP", callback_data="send_zip")]
                    ])
                )
            else:
                await message.reply(
                    "✅ ZIP processed! Choose how to receive files:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📂 Send as ZIP", callback_data="send_zip")],
                        [InlineKeyboardButton("📄 Send files separately", callback_data="send_files")]
                    ])
                )

        else:
            await message.reply("⚠️ Only PDF and ZIP files are supported.")

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
                await callback.message.reply_document(f)
            except:
                pass

    # Cleanup
    shutil.rmtree("temp_unlock", ignore_errors=True)
    del PROCESSED_RESULTS[chat_id]
    await callback.answer()
