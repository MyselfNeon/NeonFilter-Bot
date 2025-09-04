# plugins/modsfire.py

import os
import requests
import aiohttp
import aiofiles
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

MODSFIRE_API_TOKEN = os.getenv("MODSFIRE_API_TOKEN")
BASE_URL = "https://api.modsfire.com"

FILES_CACHE = {}
ACTIVE_UPLOADS = {}


# =====================
# Helpers
# =====================
def check_token():
    if not MODSFIRE_API_TOKEN:
        return False, "⚠️ ModsFire API token not set.\nPlease add `MODSFIRE_API_TOKEN` to your environment."
    return True, None


def make_progress_bar(current, total):
    percent = (current / total) * 100 if total else 0
    bar = "█" * int(percent / 5) + "░" * (20 - int(percent / 5))
    return f"[{bar}] {percent:.1f}%"


def human_size(bytes_size):
    # Convert bytes to KB, MB, GB
    for unit in ['B','KB','MB','GB','TB']:
        if bytes_size < 1024:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.2f} PB"


async def upload_with_progress(file_path, status_msg, chat_id):
    url = f"{BASE_URL}/files/upload"
    headers = {"Authorization": f"Bearer {MODSFIRE_API_TOKEN}"}

    file_size = os.path.getsize(file_path)
    uploaded = 0
    chunk_size = 1024 * 1024
    cancel_flag = {"stop": False}

    def gen_chunks():
        nonlocal uploaded
        with open(file_path, "rb") as f:
            while True:
                if cancel_flag["stop"]:
                    break
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                uploaded += len(chunk)
                yield chunk

    async def updater():
        while uploaded < file_size and not cancel_flag["stop"]:
            bar = make_progress_bar(uploaded, file_size)
            try:
                await status_msg.edit(
                    f"⬆️ Uploading to ModsFire...\n\n{bar}",
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("❌ Cancel", callback_data="cancel_upload")]]
                    ),
                )
            except Exception:
                pass
            await asyncio.sleep(2)

    loop = asyncio.get_event_loop()
    update_task = loop.create_task(updater())

    try:
        response = requests.post(
            url,
            headers=headers,
            files={"file": (os.path.basename(file_path), gen_chunks())},
        )
    finally:
        update_task.cancel()
        ACTIVE_UPLOADS.pop(chat_id, None)

    return response, cancel_flag


# =====================
# /mupload
# =====================
@Client.on_message(filters.command("mupload"))
async def mupload_handler(client, message):
    ok, err = check_token()
    if not ok:
        return await message.reply_text(err)

    if ACTIVE_UPLOADS.get(message.chat.id):
        return await message.reply_text("⚠️ You already have an upload task running. Please wait until it finishes.")

    ACTIVE_UPLOADS[message.chat.id] = True

    ask = await message.reply_text("📤 Send me a file or a direct download link to upload on **ModsFire**.")
    try:
        response = await client.listen(message.chat.id, timeout=120)
    except asyncio.TimeoutError:
        ACTIVE_UPLOADS.pop(message.chat.id, None)
        return await ask.edit("❌ Timeout: No file or link received.")

    if response.text and response.text.startswith("http"):
        file_url = response.text
        filename = file_url.split("/")[-1]
        file_path = f"downloads/{filename}"
        await ask.edit("📥 Downloading file...")

        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as resp:
                if resp.status != 200:
                    ACTIVE_UPLOADS.pop(message.chat.id, None)
                    return await ask.edit("❌ Failed to download file.")
                os.makedirs("downloads", exist_ok=True)
                async with aiofiles.open(file_path, "wb") as f:
                    await f.write(await resp.read())

    elif response.document:
        file_path = f"downloads/{response.document.file_name}"
        await ask.edit("📥 Downloading file from Telegram...")
        await response.download(file_path)
    else:
        ACTIVE_UPLOADS.pop(message.chat.id, None)
        return await ask.edit("❌ Please send a valid file or direct URL.")

    await ask.edit("⬆️ Starting upload...", reply_markup=InlineKeyboardMarkup(
        [[InlineKeyboardButton("❌ Cancel", callback_data="cancel_upload")]]
    ))

    try:
        resp, flag = await upload_with_progress(file_path, ask, message.chat.id)

        if flag["stop"]:
            return await ask.edit("❌ Upload cancelled.")

        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "success":
                link = data["data"]["file"]["url"]
                uploaded_by = message.from_user.username or message.from_user.first_name
                account_user = (requests.get(f"{BASE_URL}/user", headers={"Authorization": f"Bearer {MODSFIRE_API_TOKEN}"}).json().get("data", {}).get("username", "Unknown"))
                file_size = human_size(os.path.getsize(file_path))
                await ask.edit(
                    f"✅ Success Upload\n\n"
                    f"• File Name: {os.path.basename(file_path)}\n"
                    f"• Size: {file_size}\n"
                    f"• Uploaded By: @{uploaded_by}\n"
                    f"• Uploaded To Account: {account_user}\n\n🔗 [Open File]({link})"
                )
            else:
                await ask.edit(f"❌ Upload failed: {data}")
        else:
            await ask.edit(f"❌ API Error: {resp.text}")

    except Exception as e:
        await ask.edit(f"⚠️ Error: {e}")

    finally:
        ACTIVE_UPLOADS.pop(message.chat.id, None)
        if os.path.exists(file_path):
            os.remove(file_path)


# =====================
# /mstats
# =====================
@Client.on_message(filters.command("mstats"))
async def mstats_handler(client, message):
    ok, err = check_token()
    if not ok:
        return await message.reply_text(err)

    url = f"{BASE_URL}/files"
    headers = {"Authorization": f"Bearer {MODSFIRE_API_TOKEN}"}
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        total_files = len(data.get("data", []))
        await message.reply_text(f"📊 You have **{total_files} files** on ModsFire.")
    else:
        await message.reply_text(f"❌ Error: {resp.text}")


# =====================
# /mfiles
# =====================
@Client.on_message(filters.command("mfiles"))
async def mfiles_handler(client, message):
    ok, err = check_token()
    if not ok:
        return await message.reply_text(err)

    url = f"{BASE_URL}/files"
    headers = {"Authorization": f"Bearer {MODSFIRE_API_TOKEN}"}
    resp = requests.get(url, headers=headers)

    if resp.status_code == 200:
        data = resp.json()
        files = data.get("data", [])
        if not files:
            return await message.reply_text("📂 No files found.")

        FILES_CACHE[message.chat.id] = files
        text = "📂 **Your Files on ModsFire:**\n\n"
        for i, f in enumerate(files, 1):
            size = human_size(f.get("size", 0))
            text += f"{i}. {f['name']} ({size})\n"
        text += "\nUse `/del <number>` to delete a file."
        await message.reply_text(text)
    else:
        await message.reply_text(f"❌ Error: {resp.text}")


# =====================
# /del
# =====================
@Client.on_message(filters.command("del"))
async def delete_file_handler(client, message):
    ok, err = check_token()
    if not ok:
        return await message.reply_text(err)

    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.reply_text("❌ Usage: `/del <number>`")

    num = int(parts[1])
    files = FILES_CACHE.get(message.chat.id)
    if not files or num < 1 or num > len(files):
        return await message.reply_text("❌ Invalid file number. Use `/mfiles` first.")

    file_id = files[num - 1]["id"]
    file_name = files[num - 1]["name"]

    await message.reply_text(
        f"⚠️ Are you sure you want to delete **{file_name}**?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes", callback_data=f"confirm_del:{file_id}"),
             InlineKeyboardButton("❌ No", callback_data="cancel_del")]
        ])
    )


@Client.on_callback_query(filters.regex(r"confirm_del:(.*)"))
async def confirm_delete(client, callback_query):
    file_id = callback_query.data.split(":")[1]
    url = f"{BASE_URL}/files/{file_id}"
    headers = {"Authorization": f"Bearer {MODSFIRE_API_TOKEN}"}
    resp = requests.delete(url, headers=headers)

    if resp.status_code == 200:
        await callback_query.message.edit("✅ File deleted successfully.")
    else:
        await callback_query.message.edit(f"❌ Error: {resp.text}")


@Client.on_callback_query(filters.regex("cancel_del"))
async def cancel_delete(client, callback_query):
    await callback_query.message.edit("❌ Deletion cancelled.")


# =====================
# /muser
# =====================
@Client.on_message(filters.command("muser"))
async def muser_handler(client, message):
    ok, err = check_token()
    if not ok:
        return await message.reply_text(err)

    url = f"{BASE_URL}/user"
    headers = {"Authorization": f"Bearer {MODSFIRE_API_TOKEN}"}
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        data = resp.json().get("data", {})
        text = (
            f"👤 **User Info**\n\n"
            f"Username: `{data.get('username')}`\n"
            f"Email: `{data.get('email')}`\n"
            f"Plan: `{data.get('plan')}`\n"
            f"Storage Used: `{data.get('used_storage')} / {data.get('max_storage')}`"
        )
        await message.reply_text(text)
    else:
        await message.reply_text(f"❌ Error: {resp.text}")


# =====================
# /mhelp
# =====================
@Client.on_message(filters.command("mhelp"))
async def mhelp_handler(client, message):
    text = (
        "🛠 **ModsFire Bot Commands**\n\n"
        "📂 **File Upload & Management**\n"
        "• `/mupload` → Upload a file or URL to ModsFire (with progress + cancel).\n"
        "• `/mfiles` → List all your uploaded files with size and numbers.\n"
        "• `/del <number>` → Delete a file by its number (with confirmation).\n\n"
        "📊 **Account Info & Stats**\n"
        "• `/mstats` → Show total uploaded file count.\n"
        "• `/muser` → Show your ModsFire account details.\n\n"
        "ℹ️ Use `/mfiles` first before `/del <number>`."
    )
    await message.reply_text(text)


# =====================
# Cancel Upload Button
# =====================
@Client.on_callback_query(filters.regex("cancel_upload"))
async def cancel_upload(client, callback_query):
    ACTIVE_UPLOADS.pop(callback_query.message.chat.id, None)
    await callback_query.message.edit("❌ Upload cancelled.")
  s
