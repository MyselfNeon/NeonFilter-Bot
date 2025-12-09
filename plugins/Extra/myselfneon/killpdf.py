import os
import shutil
import time
import math
import asyncio
import uuid
import pyzipper
import pikepdf
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

PROCESSED_RESULTS = {} 
TG_MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024

def humanbytes(size):
    if not size:
        return "0 B"
    power = 2**10
    n = 0
    dic_powerN = {0: ' ', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + dic_powerN[n] + 'B'

async def progress(current, total, message: Message, start_time, status_text):
    try:
        now = time.time()
        diff = now - start_time
        
        if round(diff % 5.00) == 0 or current == total:
            percentage = current * 100 / total
            speed = current / diff if diff > 0 else 0
            elapsed_time = round(diff) * 1000
            time_to_completion = round((total - current) / speed) * 1000 if speed > 0 else 0
            estimated_total_time = elapsed_time + time_to_completion

            elapsed_str = time.strftime('%H:%M:%S', time.gmtime(elapsed_time / 1000))
            eta_str = time.strftime('%H:%M:%S', time.gmtime(estimated_total_time / 1000))

            progress_bar = "[{0}{1}] \n**__{2}%__**".format(
                ''.join(["⬢" for i in range(math.floor(percentage / 10))]),
                ''.join(["⬡" for i in range(10 - math.floor(percentage / 10))]),
                round(percentage, 2)
            )

            tmp = f"{status_text}\n{progress_bar}\n"
            tmp += f"**__📦 Size:__** {humanbytes(current)} / {humanbytes(total)}\n"
            tmp += f"**__🚀 Speed:__** {humanbytes(speed)}/s\n"
            tmp += f"**__⏳ Time:__** {elapsed_str} / {eta_str}"

            await message.edit(tmp)
    except Exception:
        pass

def _cpu_remove_pdf(input_path, output_path, password):
    try:
        with pikepdf.open(input_path, password=password) as pdf:
            pdf.save(output_path)
        return True, None
    except pikepdf.PasswordError:
        return False, "Wrong Password"
    except Exception as e:
        return False, str(e)

def _cpu_remove_zip(input_path, extract_path, password):
    try:
        with pyzipper.AESZipFile(input_path) as zf:
            if password:
                zf.extractall(path=extract_path, pwd=password.encode("utf-8"))
            else:
                zf.extractall(path=extract_path)
        return True, None
    except RuntimeError:
        return False, "Wrong Password or Corrupt ZIP"
    except Exception as e:
        return False, str(e)

def _cpu_add_pass(input_path, output_path, password, is_zip):
    try:
        if not is_zip:
            with pikepdf.open(input_path) as pdf:
                pdf.save(output_path, encryption=pikepdf.Encryption(owner=password, user=password, R=4))
        else:
            with pyzipper.AESZipFile(output_path, "w", compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as zf:
                zf.setpassword(password.encode("utf-8"))
                with pyzipper.AESZipFile(input_path) as original:
                    for f in original.namelist():
                        zf.writestr(f, original.read(f))
        return True, None
    except Exception as e:
        return False, str(e)

# --- Removepass Command ---
@Client.on_message(filters.command("removepass"))
async def remove_password(client: Client, message: Message):
    target = message.reply_to_message
    
    # Explicitly check if reply exists AND if it is a document
    if not target or not target.document:
        usage_text = """**__⚠️ Error: You must reply to a File.__**
        
**__Usage:__**
**__01. Reply to a PDF or ZIP file__**
**__02. Type:__** `/delpass`
**__03. If it has a password:__** `/delpass password`"""
        return await message.reply(usage_text)

    file_name = target.document.file_name
    args = message.text.split(" ", 1)
    password = args[1] if len(args) > 1 else None

    task_id = str(uuid.uuid4())
    base_dir = f"temp_{task_id}"
    os.makedirs(base_dir, exist_ok=True)
    
    status = await message.reply("**__⏳ Downloading ...__**")
    start_time = time.time()

    try:
        file_path = os.path.join(base_dir, file_name)
        await target.download(
            file_path,
            progress=progress,
            progress_args=(status, start_time, "**__📥 Downloading File ...__**")
        )

        await status.edit("**__🔐 Decrypting (This may take a Moment) ...__**")

        if file_name.lower().endswith(".pdf"):
            unlocked_path = os.path.join(base_dir, f"Unlocked_{file_name}")
            
            success, error = await asyncio.to_thread(_cpu_remove_pdf, file_path, unlocked_path, password)
            
            if not success:
                return await status.edit(f"**__❌ Error:__** \n`{error}`")

            if os.path.getsize(unlocked_path) > TG_MAX_FILE_SIZE:
                return await status.edit("**__❌ File Too Large (2GB Limit).__**")

            await message.reply_document(
                unlocked_path,
                caption="**__✅ File Unlocked Successfully__**\n**__🔥 Powered By @NeonFiles__**",
                progress=progress,
                progress_args=(status, time.time(), "**__📤 Uploading ...__**")
            )
            await status.delete()

        elif file_name.lower().endswith(".zip"):
            extracted_dir = os.path.join(base_dir, "extracted")
            os.makedirs(extracted_dir, exist_ok=True)

            success, error = await asyncio.to_thread(_cpu_remove_zip, file_path, extracted_dir, password)
            
            if not success:
                return await status.edit(f"**__❌ Error:__** \n`{error}`")

            unlocked_files = []
            files_too_large = False
            for root, _, files in os.walk(extracted_dir):
                for f in files:
                    full_path = os.path.join(root, f)
                    unlocked_files.append(full_path)
                    if os.path.getsize(full_path) > TG_MAX_FILE_SIZE:
                        files_too_large = True

            PROCESSED_RESULTS[task_id] = {
                "files": unlocked_files, 
                "base_dir": base_dir,
                "extract_dir": extracted_dir
            }

            buttons = []
            if files_too_large:
                buttons.append([InlineKeyboardButton("📂 Send as ZIP", callback_data=f"zip_{task_id}")])
                msg_text = "**__⚠️ Some files are >2GB. Must send as ZIP.__**"
            else:
                buttons.append([InlineKeyboardButton("📂 Send as ZIP", callback_data=f"zip_{task_id}")])
                buttons.append([InlineKeyboardButton("📄 Send Files", callback_data=f"files_{task_id}")])
                msg_text = f"**__✅ ZIP Unlocked! ({len(unlocked_files)} files)__**\n**__Choose delivery method:__**"

            await status.edit(msg_text, reply_markup=InlineKeyboardMarkup(buttons))
            return 

        else:
            await status.edit("**__⚠️ Only PDF and ZIP supported.__**")

    except Exception as e:
        await status.edit(f"**__🚫 Error:__** \n`{e}`")
        shutil.rmtree(base_dir, ignore_errors=True)

    if not file_name.lower().endswith(".zip"):
        shutil.rmtree(base_dir, ignore_errors=True)

# --- Addpass Command ---
@Client.on_message(filters.command("addpass"))
async def add_password(client: Client, message: Message):
    target = message.reply_to_message
    
    if not target or not target.document:
        usage_text = """**__⚠️ Error: You must reply to a file.__**

**__Usage:__**
**__1. Reply to a PDF or ZIP file__**
**__2. Type:__** `/addpass password`
**__Example:__** `/addpass 123456`"""
        return await message.reply(usage_text)

    args = message.text.split(" ", 1)
    password = args[1] if len(args) > 1 else None
    
    if not password:
        return await message.reply("**__⚠️ Error: Password missing.__**\n\n**__Usage:__** `/addpass password`")

    file_name = target.document.file_name
    
    task_id = str(uuid.uuid4())
    base_dir = f"temp_{task_id}"
    os.makedirs(base_dir, exist_ok=True)
    
    status = await message.reply("**__⏳ Downloading ...__**")
    start_time = time.time()

    try:
        file_path = os.path.join(base_dir, file_name)
        await target.download(
            file_path,
            progress=progress,
            progress_args=(status, start_time, "**__📥 Downloading ...__**")
        )

        output_path = os.path.join(base_dir, f"Protected_{file_name}")
        await status.edit("**__🔐 Encrypting ...__**")

        is_zip = file_name.lower().endswith(".zip")
        is_pdf = file_name.lower().endswith(".pdf")

        if not (is_zip or is_pdf):
             return await status.edit("**__⚠️ Only PDF and ZIP supported.__**")

        success, error = await asyncio.to_thread(_cpu_add_pass, file_path, output_path, password, is_zip)

        if not success:
             return await status.edit(f"**__❌ Encryption Error:__** \n`{error}`")

        await message.reply_document(
            output_path,
            caption=f"**__🔐 Protected Successfully__**\n**__🔑 Pass:__** `{password}`\n**__🔥 Powered By @NeonFiles__**",
            progress=progress,
            progress_args=(status, time.time(), "**__📤 Uploading ...__**")
        )
        await status.delete()

    except Exception as e:
        await status.edit(f"**__🚫 Error:__** \n`{e}`")

    finally:
        shutil.rmtree(base_dir, ignore_errors=True)

@Client.on_callback_query(filters.regex(r"^(zip|files)_"))
async def handle_send_choice(client: Client, callback: CallbackQuery):
    action, task_id = callback.data.split("_")

    if task_id not in PROCESSED_RESULTS:
        return await callback.answer("⚠️ Session expired.", show_alert=True)

    data = PROCESSED_RESULTS[task_id]
    files = data["files"]
    base_dir = data["base_dir"]
    extract_dir = data["extract_dir"]

    if action == "zip":
        new_zip = os.path.join(base_dir, "Unlocked_Files.zip")
        await callback.message.edit("**__📦 Re-Zipping Files ...__**")
        
        def _repack():
            with pyzipper.AESZipFile(new_zip, "w", compression=pyzipper.ZIP_DEFLATED) as newzf:
                for f in files:
                    arcname = os.path.relpath(f, extract_dir)
                    newzf.write(f, arcname=arcname)
        
        await asyncio.to_thread(_repack)
        
        await callback.message.reply_document(
            new_zip, 
            caption="**__📂 Your Unlocked ZIP__**\n**__🔥 Powered By @NeonFiles__**",
            progress=progress,
            progress_args=(callback.message, time.time(), "**__📤 Uploading ZIP ...__**")
        )

    elif action == "files":
        await callback.message.edit("**__📄 Sending Files one by one ...__**")
        for f in files:
            try:
                await callback.message.reply_document(f, caption="**__✅ Unlocked__**")
                await asyncio.sleep(0.8) 
            except Exception:
                pass
    
    await callback.message.delete()
    shutil.rmtree(base_dir, ignore_errors=True)
    del PROCESSED_RESULTS[task_id]
