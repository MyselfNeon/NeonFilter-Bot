# ---------------------------------------------------
# File Name: Kill-PDF.py
# Author: MyselfNeon
# Original Repo: https://github.com/MyselfNeon/NeonFilter-Bot
# GitHub: https://github.com/MyselfNeon/
# Telegram: https://t.me/MyelfNeon
# ---------------------------------------------------

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

# --- Configuration ---
PROCESSED_RESULTS = {} 
TG_MAX_FILE_SIZE = 2097152000 # 2GB limit in bytes
MAX_CONCURRENT_TASKS = 3  # Prevent server freeze by limiting parallel CPU tasks
CPU_SEMAPHORE = asyncio.Semaphore(MAX_CONCURRENT_TASKS)

# --- Helpers ---
def humanbytes(size):
    if not size: return "0 B"
    power = 2**10
    n = 0
    dic_powerN = {0: ' ', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + dic_powerN[n] + 'B'

async def progress(current, total, message, start_time, status_text):
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
            
            # Visual Progress Bar
            filled = math.floor(percentage / 10)
            bar = "▰" * filled + "▱" * (10 - filled)
            
            tmp = f"{status_text}\n"
            tmp += f"**{bar}** | `{round(percentage, 2)}%`\n\n"
            tmp += f"**💾 Size:** `{humanbytes(current)} / {humanbytes(total)}`\n"
            tmp += f"**🚀 Speed:** `{humanbytes(speed)}/s`\n"
            tmp += f"**⏳ Time:** `{elapsed_str} / {eta_str}`"
            
            await message.edit(tmp)
    except Exception:
        pass

def get_args(message: Message):
    # Returns (password, new_filename)
    args = message.text.split(" ")
    if len(args) < 2:
        return None, None
    
    password = args[1]
    new_name = None
    
    if len(args) > 2:
        # User provided a custom name: /addpass 123 newname.pdf
        new_name = " ".join(args[2:])
        
    return password, new_name

# --- CPU Bound Tasks ---
def _cpu_remove_pdf(input_path, output_path, password):
    try:
        # Check if file is encrypted first
        try:
            pdf = pikepdf.open(input_path)
            # If it opens without password, just save it (removes owner restrictions)
            pdf.save(output_path)
            return True, None
        except pikepdf.PasswordError:
            pass # Needs password
            
        with pikepdf.open(input_path, password=password) as pdf:
            pdf.save(output_path)
        return True, None
    except pikepdf.PasswordError:
        return False, "Wrong Password"
    except Exception as e:
        return False, str(e)

def _cpu_scan_zip(input_path):
    # Security check: Get total uncompressed size before extracting
    try:
        with pyzipper.AESZipFile(input_path) as zf:
            total_size = sum(info.file_size for info in zf.infolist())
        return total_size
    except Exception:
        return 0

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
                # R=6 is AES-256 (Stronger encryption)
                pdf.save(output_path, encryption=pikepdf.Encryption(owner=password, user=password, R=6))
        else:
            with pyzipper.AESZipFile(output_path, "w", compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as zf:
                zf.setpassword(password.encode("utf-8"))
                with pyzipper.AESZipFile(input_path) as original:
                    for f in original.namelist():
                        zf.writestr(f, original.read(f))
        return True, None
    except Exception as e:
        return False, str(e)

# --- Commands ---

@Client.on_message(filters.command("removepass"))
async def remove_password(client: Client, message: Message):
    target = message.reply_to_message
    if not target or not target.document:
        return await message.reply("**⚠️ Reply to a PDF or ZIP file.**\n\n**Usage:** `/delpass [password]`")

    file_name = target.document.file_name
    args = message.text.split(" ", 1)
    password = args[1] if len(args) > 1 else None

    # Wait for slot in queue
    msg = await message.reply("**__⏳ Waiting for queue slot...__**")
    async with CPU_SEMAPHORE:
        task_id = str(uuid.uuid4())
        base_dir = f"temp_{task_id}"
        os.makedirs(base_dir, exist_ok=True)
        start_time = time.time()
        
        try:
            file_path = os.path.join(base_dir, file_name)
            await target.download(
                file_path,
                progress=progress,
                progress_args=(msg, start_time, "**__📥 Downloading...__**")
            )

            await msg.edit("**__🔐 Decrypting...__**")

            # PDF Handling
            if file_name.lower().endswith(".pdf"):
                unlocked_path = os.path.join(base_dir, f"Unlocked_{file_name}")
                success, error = await asyncio.to_thread(_cpu_remove_pdf, file_path, unlocked_path, password)
                
                if not success:
                    shutil.rmtree(base_dir, ignore_errors=True)
                    return await msg.edit(f"**__❌ Error:__** `{error}`")

                await message.reply_document(
                    unlocked_path,
                    caption="**__✅ File Unlocked Successfully__**",
                    progress=progress,
                    progress_args=(msg, time.time(), "**__📤 Uploading...__**")
                )
                await msg.delete()
                shutil.rmtree(base_dir, ignore_errors=True)

            # ZIP Handling
            elif file_name.lower().endswith(".zip"):
                extracted_dir = os.path.join(base_dir, "extracted")
                os.makedirs(extracted_dir, exist_ok=True)

                # Security Check: Size
                total_size = await asyncio.to_thread(_cpu_scan_zip, file_path)
                if total_size > TG_MAX_FILE_SIZE:
                    shutil.rmtree(base_dir, ignore_errors=True)
                    return await msg.edit("**❌ Archive too large! Extracted size exceeds 2GB.**")

                success, error = await asyncio.to_thread(_cpu_remove_zip, file_path, extracted_dir, password)
                
                if not success:
                    shutil.rmtree(base_dir, ignore_errors=True)
                    return await msg.edit(f"**__❌ Error:__** `{error}`")

                unlocked_files = []
                for root, _, files in os.walk(extracted_dir):
                    for f in files:
                        unlocked_files.append(os.path.join(root, f))

                PROCESSED_RESULTS[task_id] = {
                    "files": unlocked_files, 
                    "base_dir": base_dir,
                    "extract_dir": extracted_dir
                }

                buttons = [
                    [InlineKeyboardButton("📂 Send as ZIP", callback_data=f"zip_{task_id}")],
                    [InlineKeyboardButton(f"📄 Send {len(unlocked_files)} Files", callback_data=f"files_{task_id}")],
                    [InlineKeyboardButton("❌ Close", callback_data=f"close_{task_id}")]
                ]
                
                await msg.edit(
                    f"**__✅ ZIP Unlocked!__**\n**__📂 Files:__** `{len(unlocked_files)}`\n**__💾 Size:__** `{humanbytes(total_size)}`",
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
                
            else:
                await msg.edit("**__⚠️ Only PDF and ZIP supported.__**")
                shutil.rmtree(base_dir, ignore_errors=True)

        except Exception as e:
            await msg.edit(f"**__🚫 Error:__** `{e}`")
            shutil.rmtree(base_dir, ignore_errors=True)

@Client.on_message(filters.command("addpass"))
async def add_password(client: Client, message: Message):
    target = message.reply_to_message
    if not target or not target.document:
        return await message.reply("**⚠️ Reply to a file.**\n\n**Usage:** `/addpass <password> [new_name]`")

    password, new_name = get_args(message)
    if not password:
        return await message.reply("**⚠️ Password missing.**\nUse: `/addpass <password>`")

    # Wait for slot
    msg = await message.reply("**__⏳ Waiting for queue slot...__**")
    
    async with CPU_SEMAPHORE:
        task_id = str(uuid.uuid4())
        base_dir = f"temp_{task_id}"
        os.makedirs(base_dir, exist_ok=True)
        start_time = time.time()

        try:
            file_name = target.document.file_name
            file_path = os.path.join(base_dir, file_name)
            
            await target.download(
                file_path,
                progress=progress,
                progress_args=(msg, start_time, "**__📥 Downloading...__**")
            )

            # Determine Output Name
            if new_name:
                # Ensure extension matches
                ext = os.path.splitext(file_name)[1]
                if not new_name.endswith(ext):
                    new_name += ext
                output_name = new_name
            else:
                output_name = f"Protected_{file_name}"
            
            output_path = os.path.join(base_dir, output_name)
            await msg.edit("**__🔐 Encrypting (AES-256)...__**")

            is_zip = file_name.lower().endswith(".zip")
            is_pdf = file_name.lower().endswith(".pdf")

            if not (is_zip or is_pdf):
                shutil.rmtree(base_dir, ignore_errors=True)
                return await msg.edit("**__⚠️ Only PDF and ZIP supported.__**")

            success, error = await asyncio.to_thread(_cpu_add_pass, file_path, output_path, password, is_zip)

            if not success:
                shutil.rmtree(base_dir, ignore_errors=True)
                return await msg.edit(f"**__❌ Encryption Error:__** `{error}`")

            await message.reply_document(
                output_path,
                caption=f"**__🔐 Protected Successfully__**\n**__🔑 Pass:__** ||`{password}`||\n**__📁 Name:__** `{output_name}`",
                progress=progress,
                progress_args=(msg, time.time(), "**__📤 Uploading...__**")
            )
            await msg.delete()

        except Exception as e:
            await msg.edit(f"**__🚫 Error:__** `{e}`")
        finally:
            shutil.rmtree(base_dir, ignore_errors=True)

@Client.on_callback_query(filters.regex(r"^(zip|files|close)_"))
async def handle_send_choice(client: Client, callback: CallbackQuery):
    action, task_id = callback.data.split("_")

    if action == "close":
        if task_id in PROCESSED_RESULTS:
            shutil.rmtree(PROCESSED_RESULTS[task_id]["base_dir"], ignore_errors=True)
            del PROCESSED_RESULTS[task_id]
        await callback.message.delete()
        return

    if task_id not in PROCESSED_RESULTS:
        return await callback.answer("⚠️ Session expired or files deleted.", show_alert=True)

    data = PROCESSED_RESULTS[task_id]
    files = data["files"]
    base_dir = data["base_dir"]
    extract_dir = data["extract_dir"]

    try:
        if action == "zip":
            new_zip = os.path.join(base_dir, "Unlocked_Files.zip")
            await callback.message.edit("**__📦 Packing Files...__**")
            
            def _repack():
                with pyzipper.AESZipFile(new_zip, "w", compression=pyzipper.ZIP_DEFLATED) as newzf:
                    for f in files:
                        # Keep folder structure relative to extract dir
                        arcname = os.path.relpath(f, extract_dir)
                        newzf.write(f, arcname=arcname)
            
            await asyncio.to_thread(_repack)
            await callback.message.reply_document(
                new_zip, 
                caption="**__📂 Unlocked ZIP__**",
                progress=progress,
                progress_args=(callback.message, time.time(), "**__📤 Uploading ZIP...__**")
            )

        elif action == "files":
            await callback.message.edit(f"**__📄 Sending {len(files)} files...__**")
            for f in files:
                try:
                    # Ignore Thumbs.db or hidden system files
                    if os.path.basename(f).startswith("."): continue
                    
                    await callback.message.reply_document(f)
                    await asyncio.sleep(1) # Floodwait prevention
                except Exception:
                    pass
    
    except Exception as e:
        await callback.message.reply(f"**Error:** {e}")
    finally:
        await callback.message.delete()
        shutil.rmtree(base_dir, ignore_errors=True)
        if task_id in PROCESSED_RESULTS:
            del PROCESSED_RESULTS[task_id]

# MyselfNeon
# Don't Remove Credit 🥺
# Telegram Channel @NeonFiles
