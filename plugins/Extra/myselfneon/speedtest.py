# ============================================================
# 🚀 SPEEDTEST PLUGIN BY NEON
# Simple, Fast & Clean — Made in the Style of Telegraph.py 😎
# ============================================================

import asyncio
import math
from time import time
from speedtest import Speedtest
from pyrogram import Client, filters
from pyrogram.types import Message

from info import API_ID, API_HASH, BOT_TOKEN  # Import bot creds

# -------------------
# Constants
# -------------------
SIZE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
BOT_START_TIME = time()

# -------------------
# Helpers
# -------------------
def get_readable_time(seconds: int) -> str:
    result = ''
    days, remainder = divmod(seconds, 86400)
    if days:
        result += f'{days}d'
    hours, remainder = divmod(remainder, 3600)
    if hours:
        result += f'{hours}h'
    minutes, seconds = divmod(remainder, 60)
    if minutes:
        result += f'{minutes}m'
    result += f'{seconds}s'
    return result

def get_readable_file_size(size_in_bytes) -> str:
    if size_in_bytes is None:
        return '0B'
    index = 0
    while size_in_bytes >= 1024:
        size_in_bytes /= 1024
        index += 1
    try:
        return f'{round(size_in_bytes, 2)}{SIZE_UNITS[index]}'
    except IndexError:
        return 'File too large'

def speed_convert(size, byte=True):
    if not byte:
        size = size / 8
    power = 2 ** 10
    zero = 0
    units = {0: "B/s", 1: "KB/s", 2: "MB/s", 3: "GB/s", 4: "TB/s"}
    while size > power:
        size /= power
        zero += 1
    return f"{round(size, 2)} {units[zero]}"

# -------------------
# /speedtest command
# -------------------
@Client.on_message(filters.command("speedtest"))
async def run_speedtest(bot: Client, message: Message):
    status = await message.reply_text("⚡ **Running Speedtest... Please Wait!**")

    try:
        test = Speedtest()
        test.get_best_server()
        test.download()
        test.upload()
        test.results.share()

        result = test.results.dict()
        uptime = get_readable_time(time() - BOT_START_TIME)

        # Format result message
        result_text = f"""
╭─《 🚀 SPEEDTEST RESULTS 》
├ **Upload:** `{speed_convert(result['upload'], False)}`
├ **Download:** `{speed_convert(result['download'], False)}`
├ **Ping:** `{result['ping']} ms`
├ **Time:** `{result['timestamp']}`
├ **Data Sent:** `{get_readable_file_size(int(result['bytes_sent']))}`
╰ **Data Received:** `{get_readable_file_size(int(result['bytes_received']))}`

╭─《 🌐 SERVER INFO 》
├ **Name:** `{result['server']['name']}`
├ **Country:** `{result['server']['country']}, {result['server']['cc']}`
├ **Sponsor:** `{result['server']['sponsor']}`
├ **Latency:** `{result['server']['latency']}`
╰ **Coordinates:** `{result['server']['lat']}, {result['server']['lon']}`

╭─《 ⚙️ BOT STATUS 》
╰ **Uptime:** `{uptime}`
"""

        try:
            await status.delete()
            await message.reply_photo(photo=result.get('share'), caption=result_text)
        except Exception:
            await status.delete()
            await message.reply_text(result_text)

    except Exception as e:
        await status.edit_text(f"❌ **Speedtest Failed!**\n\n`{e}`")

# -------------------
# Credits
# -------------------
# Developer: @MyselfNeon
# Update Channel: @NeonFiles
