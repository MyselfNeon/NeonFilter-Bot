# plugins/live_stats.py
import psutil
import platform
import os
import time
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_START_TIME = datetime.utcnow()  # Track bot uptime

# ------------------ HELPERS ------------------
def get_size(bytes, suffix="B"):
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f}{unit}{suffix}"
        bytes /= factor

def get_bot_uptime():
    delta = datetime.utcnow() - BOT_START_TIME
    days = delta.days
    hours, rem = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{days}d {hours}h {minutes}m {seconds}s"

def progress_bar(percent, length=12):
    filled = int(length * percent / 100)
    empty = length - filled
    return "■" * filled + "□" * empty + f" {percent:.1f}%"

# ------------------ STATS SECTIONS ------------------
def bot_stats_text():
    cpu_percent = psutil.cpu_percent(interval=0.5)
    cpu_freq = psutil.cpu_freq()
    cores = psutil.cpu_count(logical=False)
    threads = psutil.cpu_count(logical=True)
    load1, load5, load15 = psutil.getloadavg()
    
    ram = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage("/")
    net = psutil.net_io_counters()

    uptime = get_bot_uptime()

    text = f"""
⌬ CPU
┠ Usage : {progress_bar(cpu_percent)}
┠ Freq : {cpu_freq.current:.2f} MHz
┠ P-Cores : {cores} | V-Cores : {threads} | Total : {cores+threads-cores}
┖ Load : {load1:.2f}, {load5:.2f}, {load15:.2f} (1m,5m,15m)

⌬ RAM
┠ Used : {progress_bar(ram.percent)}
┖ Free : {get_size(ram.available)} / Total : {get_size(ram.total)}

⌬ SWAP
┠ Used : {progress_bar(swap.percent)}
┖ Free : {get_size(swap.free)} / Total : {get_size(swap.total)}

⌬ DISK
┠ Used : {progress_bar(disk.percent)}
┖ Free : {get_size(disk.free)} / Total : {get_size(disk.total)}

⌬ NETWORK
┠ Upload : {get_size(net.bytes_sent)}
┖ Download : {get_size(net.bytes_recv)}
┖ Total I/O : {get_size(net.bytes_sent + net.bytes_recv)}

⌬ BOT
┖ Uptime : {uptime}
"""
    return text

def og_stats_text():
    uname = platform.uname()
    return f"""
⌬ OS SYSTEM
┠ OS : {uname.system} {uname.release}
┠ Version : {platform.version()}
┖ Arch : {uname.machine}
"""

def bot_limits_text():
    return f"""
⌬ BOT LIMITATIONS
┠ Direct Limit : ∞ GB
┠ Torrent Limit : ∞ GB
┠ GDrive Limit : ∞ GB
┠ YT-DLP Limit : ∞ GB
┖ Playlist Limit : ∞
┖ Mega Limit : ∞ GB
┖ Clone Limit : ∞ GB
┖ Leech Limit : ∞ GB
"""

# ------------------ BUTTONS ------------------
def main_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Bot Stats", callback_data="stats_bot"),
            InlineKeyboardButton("OG Stats", callback_data="stats_og"),
            InlineKeyboardButton("Bot Limits", callback_data="stats_limits")
        ]
    ])

def section_buttons(section):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Refresh", callback_data=f"refresh_{section}"),
            InlineKeyboardButton("Back", callback_data="back_stats_main")
        ]
    ])

# ------------------ COMMAND ------------------
@Client.on_message(filters.command("statsg") & filters.private)
async def stats_command(client, message):
    await message.reply_text("Select a section:", reply_markup=main_buttons())

# ------------------ CALLBACK ------------------
@Client.on_callback_query()
async def stats_callback(client, callback_query):
    data = callback_query.data

    # Show sections
    if data == "stats_bot":
        await callback_query.message.edit_text(bot_stats_text(), reply_markup=section_buttons("bot"))
        await callback_query.answer()
    elif data == "stats_og":
        await callback_query.message.edit_text(og_stats_text(), reply_markup=section_buttons("og"))
        await callback_query.answer()
    elif data == "stats_limits":
        await callback_query.message.edit_text(bot_limits_text(), reply_markup=section_buttons("limits"))
        await callback_query.answer()

    # Refresh sections
    elif data.startswith("refresh_"):
        section = data.split("_")[1]
        if section == "bot":
            await callback_query.message.edit_text(bot_stats_text(), reply_markup=section_buttons("bot"))
        elif section == "og":
            await callback_query.message.edit_text(og_stats_text(), reply_markup=section_buttons("og"))
        elif section == "limits":
            await callback_query.message.edit_text(bot_limits_text(), reply_markup=section_buttons("limits"))
        await callback_query.answer("Refreshed ✅", show_alert=False)

    # Back to main menu
    elif data == "back_stats_main":
        await callback_query.message.edit_text("Select a section:", reply_markup=main_buttons())
        await callback_query.answer()
      
