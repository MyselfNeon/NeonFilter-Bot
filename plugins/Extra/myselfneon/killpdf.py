#Pass remover and adder.py
import os
import shutil
import pyzipper
import pikepdf
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# TEMPORARY STORAGE FOR PROCESSED FILES
PROCESSED_RESULTS = {}  # {chat_id: {"files": [paths], "force_zip": bool}}

# TELEGRAM MAX UPLOAD SIZE (2 GB)
TG_MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024


# ====================== REMOVE PASSWORD COMMAND ======================
@Client.on_message(filters.command("removepass") & filters.reply)
async def remove_password(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply("**⚠️ __Reply To A <u>PDF or ZIP File</u> With__** `/removepass <password>`")

    file_name = message.reply_to_message.document.file_name
    args = message.text.split(" ", 1)
    password = args[1] if len(args) > 1 else None

    status = await message.reply("⏳ **__Rᴇᴍᴏᴠɪɴɢ Pᴀssᴡᴏʀᴅ__ 🔓 ...**")

    try:
        # DOWNLOAD FILE
        file_path = await message.reply_to_message.download()
        base_dir = "temp_unlock"
        extracted_dir = os.path.join(base_dir, "extracted")
        unlocked_dir = os.path.join(base_dir, "unlocked")
        os.makedirs(extracted_dir, exist_ok=True)
        os.makedirs(unlocked_dir, exist_ok=True)

        # HANDLE PDF
        if file_name.lower().endswith(".pdf"):
            unlocked_path = os.path.join(unlocked_dir, file_name)
            try:
                with pikepdf.open(file_path, password=password) as pdf:
                    pdf.save(unlocked_path)
                if os.path.getsize(unlocked_path) > TG_MAX_FILE_SIZE:
                    return await status.edit("❌ **__File Too Large For Telegram (2GB Limit)__**")
                await status.delete()
                await message.reply_document(
                    unlocked_path,
                    caption="**✅ __File Unlocked Successfully__**"
                )
            except pikepdf.PasswordError:
                await status.edit("❌ **__Wrong PDF Password Or Unable To Remove__**")

        # HANDLE ZIP
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
                        return await status.edit("❌ **__Wrong ZIP Password Or Extraction Failed__**")
            except Exception as e:
                return await status.edit(f"❌ **__ZIP Extraction Error: {e}__**")

            # PROCESS EXTRACTED FILES
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

            # SAVE FOR CALLBACK
            PROCESSED_RESULTS[message.chat.id] = {"files": unlocked_files, "force_zip": too_large}

            buttons = []
            if too_large:
                buttons.append([InlineKeyboardButton("📂 Sᴇɴᴅ ZIP", callback_data="send_zip")])
                await status.edit("⚠️ **__Some Files Exceed 2GB, Must Send As ZIP__**",
                                  reply_markup=InlineKeyboardMarkup(buttons))
            else:
                buttons.append([InlineKeyboardButton("📂 Sᴇɴᴅ ZIP", callback_data="send_zip")])
                buttons.append([InlineKeyboardButton("📄 Sᴇɴᴅ Fɪʟᴇs", callback_data="send_files")])
                await status.edit("**✅ __ZIP Unlocked Successfully\nChoose How To Receive Files__**",
                                  reply_markup=InlineKeyboardMarkup(buttons))

        else:
            await status.edit("⚠️ **__Only Pdf And Zip Files Are Supported__**")

    except Exception as e:
        await status.edit(f"🚫 **__Error:** \n{e}__")

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


# ====================== ADD PASSWORD COMMAND ======================
@Client.on_message(filters.command("addpass") & filters.reply)
async def add_password(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply("⚠️ **__Reply To A <u>PDF or ZIP File</u> With__** `/addpass <password>`")

    file_name = message.reply_to_message.document.file_name
    args = message.text.split(" ", 1)
    password = args[1] if len(args) > 1 else None
    if not password:
        return await message.reply("⚠️ **__Please Provide A Password.\n\nUsage__**: `/addpass yourpassword`")

    status = await message.reply("**⏳ __Aᴅᴅɪɴɢ Pᴀssᴡᴏʀᴅ__ 🔐 ...**")

    try:
        file_path = await message.reply_to_message.download()
        base_dir = "temp_addpass"
        os.makedirs(base_dir, exist_ok=True)

        # PDF CASE
        if file_name.lower().endswith(".pdf"):
            protected_path = os.path.join(base_dir, file_name)
            with pikepdf.open(file_path) as pdf:
                pdf.save(protected_path, encryption=pikepdf.Encryption(owner=password, user=password, R=4))
            await status.delete()
            await message.reply_document(
                protected_path,
                caption=f"🔐 **__File Protected Successfully\n🔑 Password__**: `{password}`\n\n**🔥 __Powered By @NeonFiles__**"
            )

        # ZIP CASE
        elif file_name.lower().endswith(".zip"):
            protected_path = os.path.join(base_dir, file_name)
            with pyzipper.AESZipFile(protected_path, "w", compression=pyzipper.ZIP_DEFLATED,
                                     encryption=pyzipper.WZ_AES) as zf:
                zf.setpassword(password.encode("utf-8"))   # SET PASSWORD ONCE
                with pyzipper.AESZipFile(file_path) as original_zip:
                    for f in original_zip.namelist():
                        data = original_zip.read(f)
                        zf.writestr(f, data)  # NO PWD ARG HERE
            await status.delete()
            await message.reply_document(
                protected_path,
                caption=f"🔐 **__File Protected Successfully\n🔑 Password__**: `{password}`\n\n**🔥 __Powered By @NeonFiles__**"
            )

        else:
            await status.edit("⚠️ **__Only PDF And ZIP Files Are Supported__**")

    except Exception as e:
        await status.edit(f"🚫 **__Error:** \n{e}__")

    finally:
        shutil.rmtree(base_dir, ignore_errors=True)
        if os.path.exists(file_path):
            os.remove(file_path)


# ====================== CALLBACK HANDLER ======================
@Client.on_callback_query(filters.regex("send_zip|send_files"))
async def handle_send_choice(client: Client, callback: CallbackQuery):
    chat_id = callback.message.chat.id
    if chat_id not in PROCESSED_RESULTS:
        return await callback.answer("⚠️ **__No Processed Files Found__**", show_alert=True)

    results = PROCESSED_RESULTS[chat_id]
    choice = callback.data

    if choice == "send_zip":
        new_zip = "Unlocked Files.zip"
        with pyzipper.AESZipFile(new_zip, "w", compression=pyzipper.ZIP_DEFLATED) as newzf:
            for f in results["files"]:
                arcname = os.path.relpath(f, "temp_unlock/unlocked")
                newzf.write(f, arcname=arcname)
        await callback.message.reply_document(new_zip, caption="📂 **__Here’s Your Unlocked ZIP__\n\n🔥 __Powered By @NeonFiles__**")
        os.remove(new_zip)

    elif choice == "send_files":
        if results.get("force_zip"):
            return await callback.answer("⚠️ **__Some Files Exceed 2GB. ZIP Is Required__**", show_alert=True)
        for f in results["files"]:
            try:
                await callback.message.reply_document(f, caption="**__File Unlocked Successfully__ ✅**")
            except:
                pass

    shutil.rmtree("temp_unlock", ignore_errors=True)
    del PROCESSED_RESULTS[chat_id]
    await callback.answer()
  
# ====================== PASSWORD HELP COMMAND ======================
@Client.on_message(filters.command("passhelp"))
async def password_help(client: Client, message: Message):
    help_text = """
<blockquote>**🔐 𝐏𝐀𝐒𝐒𝐖𝐎𝐑𝐃 𝐌𝐀𝐍𝐀𝐆𝐄𝐑 🔐**</blockquote>

**🔓 __Remove Password__**
__• /removepass \n- **Reply To any PDF or ZIP Files
• If ZIP Contains Large Files (>2GB) It \n  Will Send As A New Zip__**
\n**🔐 __Add Password__**
__• /addpass \n- **Reply To any PDF or ZIP Files
• Adds Password Protection To A PDF \n  ProvideFile. Give A Password First__**

<blockquote>**⚠️ __Nᴏᴛᴇs__**</blockquote>
**__- Only PDF and ZIP Are Supported
- Large Files (>2GB) May Require ZIP\n   Packaging To Send Via Telegram__**

**🔥 __Powered By @NeonFiles__ 🔥**
"""
    await message.reply(help_text)
    
