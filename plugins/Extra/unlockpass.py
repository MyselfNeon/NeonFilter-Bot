import os
import shutil
import pyzipper   # instead of zipfile
import pikepdf
from pyrogram import Client, filters
from pyrogram.types import Message


@Client.on_message(filters.command("unlock") & filters.reply)
async def unlock_files(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply("⚠️ Reply to a **PDF or ZIP file** with `/unlock <password>`")

    file_name = message.reply_to_message.document.file_name
    args = message.text.split(" ", 1)
    if len(args) < 2:
        return await message.reply("❌ Please provide the password. Example:\n`/unlock mypassword`")
    password = args[1]

    try:
        # Download file
        file_path = await message.reply_to_message.download()
        base_dir = "temp_unlock"
        extracted_dir = os.path.join(base_dir, "extracted")
        unlocked_dir = os.path.join(base_dir, "unlocked")

        os.makedirs(extracted_dir, exist_ok=True)
        os.makedirs(unlocked_dir, exist_ok=True)

        if file_name.endswith(".pdf"):
            # Unlock single PDF
            unlocked_path = os.path.join(unlocked_dir, "unlocked_" + file_name)
            try:
                with pikepdf.open(file_path, password=password) as pdf:
                    pdf.save(unlocked_path)
                await message.reply_document(unlocked_path, caption="✅ PDF unlocked successfully!")
            except pikepdf._qpdf.PasswordError:
                await message.reply("❌ Wrong password or unable to unlock the PDF.")

        elif file_name.endswith(".zip"):
            # Extract ZIP with pyzipper (supports AES + ZipCrypto)
            try:
                with pyzipper.AESZipFile(file_path) as zf:
                    zf.pwd = password.encode("utf-8")
                    zf.extractall(extracted_dir)
            except Exception as e:
                return await message.reply(f"❌ ZIP extraction failed: {e}")

            # Process extracted files
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
                            shutil.copy(src_path, dest_path)  # keep original if not unlockable
                    else:
                        shutil.copy(src_path, dest_path)

            # Repack into new ZIP
            new_zip = "unlocked_files.zip"
            with pyzipper.AESZipFile(new_zip, "w", compression=pyzipper.ZIP_DEFLATED) as newzf:
                for root, _, files in os.walk(unlocked_dir):
                    for f in files:
                        file_full_path = os.path.join(root, f)
                        arcname = os.path.relpath(file_full_path, unlocked_dir)
                        newzf.write(file_full_path, arcname=arcname)

            await message.reply_document(new_zip, caption="✅ ZIP extracted & PDFs unlocked successfully!")

        else:
            await message.reply("⚠️ Only PDF and ZIP files are supported.")

    except Exception as e:
        await message.reply(f"⚠️ Error: {e}")

    finally:
        shutil.rmtree(base_dir, ignore_errors=True)
        if os.path.exists(file_path):
            os.remove(file_path)
