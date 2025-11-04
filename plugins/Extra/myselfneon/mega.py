# Mega Tunnel Plugin (Pyrogram)
# Requirements: pyrogram, mega.py, requests
# pip install pyrogram mega.py requests

"""
BotFather Commands:
/cmega - connect to MEGA (usage: /cmega email:password)
/rupload - remote upload from URL (usage: /rupload <direct_download_url>)
/listfiles - list number of files in MEGA
/rename - rename a file (usage: /rename oldname | newname)
/getlink - get public share link for a file (usage: /getlink <filename>)
/logout - logout and remove stored MEGA credentials
"""

import os
import json
import tempfile
import asyncio
import requests
from mega import Mega
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

SESSIONS_FILE = "mega_sessions.json"


def load_sessions():
    if os.path.exists(SESSIONS_FILE):
        with open(SESSIONS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_sessions(sessions):
    with open(SESSIONS_FILE, "w") as f:
        json.dump(sessions, f)


async def login_mega_for_user(user_id):
    sessions = load_sessions()
    if str(user_id) not in sessions:
        raise ValueError("No MEGA credentials found. Use /cmega first.")
    creds = sessions[str(user_id)]
    email = creds.get("email")
    password = creds.get("password")

    def do_login():
        mega = Mega()
        return mega.login(email, password)

    return await asyncio.to_thread(do_login)


@Client.on_message(filters.command("cmega") & filters.private)
async def connect_cmd(_, msg):
    if len(msg.command) < 2:
        return await msg.reply_text("Usage: /cmega email:password")

    arg = msg.text.split(None, 1)[1].strip()
    if ":" not in arg:
        return await msg.reply_text("Send credentials as: email:password")

    email, password = arg.split(":", 1)
    info = await msg.reply_text("🔐 Logging into MEGA...")

    def try_login():
        try:
            mega = Mega()
            m = mega.login(email.strip(), password.strip())
            user = m.get_user()
            return True, user
        except Exception as e:
            return False, str(e)

    ok, result = await asyncio.to_thread(try_login)
    if ok:
        sessions = load_sessions()
        sessions[str(msg.from_user.id)] = {"email": email.strip(), "password": password.strip()}
        save_sessions(sessions)
        await info.edit_text(f"✅ Connected to MEGA as: {result.get('name', 'Unknown')}")
    else:
        await info.edit_text(f"❌ Failed to login: {result}")


@Client.on_message(filters.command("logout") & filters.private)
async def logout_cmd(_, msg):
    sessions = load_sessions()
    if str(msg.from_user.id) in sessions:
        sessions.pop(str(msg.from_user.id))
        save_sessions(sessions)
        await msg.reply_text("✅ Logged out and removed stored credentials.")
    else:
        await msg.reply_text("⚠️ No stored MEGA credentials found.")


@Client.on_message(filters.command("rupload") & filters.private)
async def remote_upload_cmd(_, msg):
    if len(msg.command) < 2:
        return await msg.reply_text("Usage: /rupload <direct_download_url>")

    url = msg.text.split(None, 1)[1].strip()
    info = await msg.reply_text("📥 Downloading file...")

    try:
        m = await login_mega_for_user(msg.from_user.id)
    except Exception as e:
        return await info.edit_text(f"❌ {e}")

    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            temp_fd, temp_path = tempfile.mkstemp()
            os.close(temp_fd)

            downloaded = 0
            with open(temp_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            pct = int(downloaded * 100 / total)
                            await info.edit_text(f"📥 Downloading... {pct}%")

        await info.edit_text("☁️ Uploading to MEGA...")

        def do_upload():
            return m.upload(temp_path)

        uploaded = await asyncio.to_thread(do_upload)
        link = m.get_link(uploaded)
        os.remove(temp_path)

        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Open Link", url=link)]])
        await info.edit_text(f"✅ Uploaded!\n{link}", reply_markup=kb)

    except Exception as e:
        await info.edit_text(f"⚠️ Error: {e}")


@Client.on_message(filters.command("listfiles") & filters.private)
async def listfiles_cmd(_, msg):
    try:
        m = await login_mega_for_user(msg.from_user.id)
    except Exception as e:
        return await msg.reply_text(str(e))

    def count_files():
        files = m.get_files()
        return sum(1 for v in files.values() if isinstance(v, dict) and v.get("t") == 0)

    count = await asyncio.to_thread(count_files)
    await msg.reply_text(f"📂 You have {count} files in your MEGA account.")


@Client.on_message(filters.command("rename") & filters.private)
async def rename_cmd(_, msg):
    if len(msg.command) < 2 or "|" not in msg.text:
        return await msg.reply_text("Usage: /rename oldname | newname")

    old, new = [x.strip() for x in msg.text.split(" ", 1)[1].split("|", 1)]
    try:
        m = await login_mega_for_user(msg.from_user.id)
    except Exception as e:
        return await msg.reply_text(str(e))

    file = m.find(old)
    if not file:
        return await msg.reply_text("❌ File not found.")

    def do_rename():
        return m.rename(file, new)

    await asyncio.to_thread(do_rename)
    await msg.reply_text(f"✅ Renamed `{old}` ➜ `{new}`")


@Client.on_message(filters.command("getlink") & filters.private)
async def getlink_cmd(_, msg):
    if len(msg.command) < 2:
        return await msg.reply_text("Usage: /getlink <filename>")

    name = msg.text.split(None, 1)[1].strip()
    try:
        m = await login_mega_for_user(msg.from_user.id)
    except Exception as e:
        return await msg.reply_text(str(e))

    file = m.find(name)
    if not file:
        return await msg.reply_text("❌ File not found.")

    def make_link():
        return m.get_link(file)

    link = await asyncio.to_thread(make_link)
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Open Link", url=link)]])
    await msg.reply_text(f"✅ Public link:\n{link}", reply_markup=kb)
