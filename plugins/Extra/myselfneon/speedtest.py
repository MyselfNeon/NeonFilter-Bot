# ============================================================
# 🚀 SPEEDTEST PLUGIN BY NEON
# Full Detailed Version (with Client Info, Server Info, & Share)
# ============================================================

import asyncio
import math
from time import time
from speedtest import Speedtest
from pyrogram import Client, filters
from pyrogram.types import Message

from info import API_ID, API_HASH, BOT_TOKEN

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
    status = await message.reply_text("⚡ <b>Running Speedtest...</b>\nPlease wait a few seconds!")

    try:
        test = Speedtest()
        test.get_best_server()
        test.download()
        test.upload()
        test.results.share()

        result = test.results.dict()
        uptime = get_readable_time(time() - BOT_START_TIME)

        # Full HTML formatted result
        result_text = f"""
╭─《 🚀 SPEEDTEST INFO 》
├ <b>Upload:</b> <code>{speed_convert(result['upload'], False)}</code>
├ <b>Download:</b> <code>{speed_convert(result['download'], False)}</code>
├ <b>Ping:</b> <code>{result['ping']} ms</code>
├ <b>Time:</b> <code>{result['timestamp']}</code>
├ <b>Data Sent:</b> <code>{get_readable_file_size(int(result['bytes_sent']))}</code>
╰ <b>Data Received:</b> <code>{get_readable_file_size(int(result['bytes_received']))}</code>

╭─《 🌐 SPEEDTEST SERVER 》
├ <b>Name:</b> <code>{result['server']['name']}</code>
├ <b>Country:</b> <code>{result['server']['country']}, {result['server']['cc']}</code>
├ <b>Sponsor:</b> <code>{result['server']['sponsor']}</code>
├ <b>Latency:</b> <code>{result['server']['latency']}</code>
├ <b>Latitude:</b> <code>{result['server']['lat']}</code>
╰ <b>Longitude:</b> <code>{result['server']['lon']}</code>

╭─《 👤 CLIENT DETAILS 》
├ <b>IP Address:</b> <code>{result['client']['ip']}</code>
├ <b>Latitude:</b> <code>{result['client']['lat']}</code>
├ <b>Longitude:</b> <code>{result['client']['lon']}</code>
├ <b>Country:</b> <code>{result['client']['country']}</code>
├ <b>ISP:</b> <code>{result['client']['isp']}</code>
├ <b>ISP Rating:</b> <code>{result['client']['isprating']}</code>
╰ <b>Powered by Team SPY ⚡</b>

<b>Bot Uptime:</b> <code>{uptime}</code>
"""

        try:
            await status.delete()
            await message.reply_photo(photo=result.get('share'), caption=result_text)
        except Exception:
            await status.delete()
            await message.reply_text(result_text)

    except Exception as e:
        await status.edit_text(f"❌ <b>Speedtest Failed!</b>\n\n<code>{e}</code>")

# -------------------
# Credits
# -------------------
# 👨‍💻 Developer: @MyselfNeon
# 📢 Channel: @NeonFiles
