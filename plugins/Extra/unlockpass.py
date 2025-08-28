import os
import shutil
import pyzipper
import pikepdf
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Temporary storage for processed files
PROCESSED_RESULTS = {}  # {chat_id: {"files": [paths], "force_zip": bool, "original_zip": str, "task": asyncio.Task}}

# Telegram max upload size (2 GB)
TG_MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024
AUTO_DELETE_MINUTES = 10
MAX_PDFS = 50  # max PDFs per ZIP
MAX_FILE_SIZE_WARN = 500 * 1024 * 1024  # warn if PDF >500MB

# Helper to generate progress bar
def progress_bar(current, total, length=20):
    filled = int(current / total * length)
    empty = length - filled
    return "▰" * filled + "▱" * empty

async def auto_cleanup(chat_id):
    """Automatically delete temp files after timeout"""
    await asyncio.sleep(AUTO_DELETE_MINUTES * 60)
    if chat_id in PROCESSED_RESULTS:
        shutil.rmtree("temp_unlock", ignore_errors=True)
        del PROCESSED_RESULTS[chat_id]

@Client.on_message(filters.command("unlock") & filters.reply)
async def unlock_files(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply("⚠️ Reply to a **PDF or ZIP file** with `/unlock <password>`")

    file_name = message.reply_to_message.document.file_name
    args = message.text.split(" ", 1)
    if len(args) < 2:
        return await message.reply("❌ Usage: /unlock <password>")

    password = args[1]

    # Per-user temp quota
    if message.chat.id in PROCESSED_RESULTS:
        return await message.reply("⚠️ You already have a processing task. Wait until it finishes or times out.")

    try:
        file_path = await message.reply_to_message.download()
        base_dir = "temp_unlock"
        extracted_dir = os.path.join(base_dir, "extracted")
        unlocked_dir = os.path.join(base_dir, "unlocked")
        os.makedirs(extracted_dir, exist_ok=True)
        os.makedirs(unlocked_dir, exist_ok=True)

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

        elif file_name.endswith(".zip"):
            unlocked_files = []
            too_large = False
            # Extract ZIP
            try:
                with pyzipper.AESZipFile(file_path) as zf:
                    if zf.needs_password():
                        zf.pwd = password.encode("utf-8")
                    zf.extractall(extracted_dir)
            except RuntimeError:
                return await message.reply("❌ Wrong ZIP password or extraction failed.")
            except Exception as e:
                return await message.reply(f"❌ ZIP extraction error: {e}")

            # Gather PDFs only
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
            status_msg = await message.reply(f"🔓 Unlocking PDFs... 0/{total_pdfs} unlocked\nProgress: {progress_bar(0, total_pdfs)}")

            # Unlock PDFs
            for idx, pdf_path in enumerate(pdf_list, start=1):
                rel_path = os.path.relpath(pdf_path, extracted_dir)
                dest_path = os.path.join(unlocked_dir, rel_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                try:
                    with pikepdf.open(pdf_path, password=password) as pdf:
                        pdf.save(dest_path)
                except Exception:
                    shutil.copy(pdf_path, dest_path)

                unlocked_files.append(dest_path)
                if os.path.getsize(dest_path) > TG_MAX_FILE_SIZE:
                    too_large = True

                # Update progress
                await status_msg.edit_text(
                    f"🔓 Unlocking PDFs... {idx}/{total_pdfs} unlocked\nProgress: {progress_bar(idx, total_pdfs)}"
                )

            # Schedule auto-cleanup
            task = asyncio.create_task(auto_cleanup(message.chat.id))
            PROCESSED_RESULTS[message.chat.id] = {
                "files": unlocked_files,
                "force_zip": too_large,
                "original_zip": file_name,
                "task": task
            }

            # Inline buttons
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

    # Cancel auto-cleanup
    if "task" in results and not results["task"].done():
        results["task"].cancel()

    if choice == "send_zip":
        new_zip = f"unlocked_{results.get('original_zip', 'files')}"
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
