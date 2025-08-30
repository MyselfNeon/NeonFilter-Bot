# plugins/stats_emoji_dashboard.py
import psutil
import platform
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_START_TIME = datetime.utcnow()

def get_size(bytes, suffix="B"):
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f}{unit}{suffix}"
        bytes /= factor

def get_uptime(start_time):
    delta = datetime.utcnow() - start_time
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days}d {hours}h {minutes}m {seconds}s"

def emoji_bar(percent, length=12, full='🟩', empty='⬛'):
    filled = int(length * percent / 100)
    empty_blocks = length - filled
    return f"{full*filled}{empty*empty_blocks} {percent:.1f}%"

# ------------------ STATS SECTIONS ------------------
def bot_stats_text():
    cpu_percent = psutil.cpu_percent(interval=0.5)
    cpu_per_core = psutil.cpu_percent(interval=0.5, percpu=True)
    cpu_freq = psutil.cpu_freq()
    cores = psutil.cpu_count(logical=False)
    threads = psutil.cpu_count(logical=True)
    load1, load5, load15 = psutil.getloadavg()
    svmem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage("/")
    net_io = psutil.net_io_counters()
    uptime = get_uptime(BOT_START_TIME)

    core_bars = "\n".join([f"Core {i+1}: {emoji_bar(p)}" for i, p in enumerate(cpu_per_core)])
    
    return f"""
⌬ **BOT STATISTICS**
┠ CPU Usage : {emoji_bar(cpu_percent)}
{core_bars}
┠ Freq : {cpu_freq.current:.2f} MHz
┖ Load : {load1:.2f}, {load5:.2f}, {load15:.2f} (1m,5m,15m)

⌬ **RAM**
┠ Used : {emoji_bar(svmem.percent, full='🟦')}
┖ Swap : {emoji_bar(swap.percent, full='🟦')}

⌬ **DISK**
┖ Usage : {emoji_bar(disk.percent, full='🟧')}

⌬ **NETWORK**
┠ Upload ⬆️ : {get_size(net_io.bytes_sent)}
┖ Download ⬇️ : {get_size(net_io.bytes_recv)}

⌬ **UPTIME**
┖ {uptime}
"""

def og_stats_text():
    uname = platform.uname()
    return f"""
⌬ **OG STATS**
┠ OS : {uname.system} {uname.release}
┠ Version : {platform.version()}
┖ Architecture : {uname.machine}
"""

def bot_limits_text():
    return f"""
⌬ **BOT LIMITATIONS**
┠ Direct Limit : ∞ GB
┠ Torrent Limit : ∞ GB
┠ GDrive Limit : ∞ GB
┠ YT-DLP Limit : ∞ GB
┖ Leech Limit : ∞ GB
┖ Playlist Limit : ∞
┖ Mega Limit : ∞ GB
┖ Clone Limit : ∞ GB
"""

# ------------------ BUTTONS ------------------
def main_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Bot Stats 📊", callback_data="show_bot_stats"),
            InlineKeyboardButton("OG Stats 🖥️", callback_data="show_og_stats"),
            InlineKeyboardButton("Bot Limits ⚡", callback_data="show_bot_limits")
        ]
    ])

def section_buttons(section):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Refresh 🔄", callback_data=f"refresh_{section}"),
            InlineKeyboardButton("Back ⬅️", callback_data="back_to_main")
        ]
    ])

# ------------------ COMMAND ------------------
@Client.on_message(filters.command("statsg") & filters.private)
async def stats_command(client, message):
    await message.reply_text("Select a section to view:", reply_markup=main_buttons())

# ------------------ CALLBACK ------------------
@Client.on_callback_query()
async def stats_callback(client, callback_query):
    data = callback_query.data

    # Show sections
    if data == "show_bot_stats":
        await callback_query.message.edit_text(bot_stats_text(), reply_markup=section_buttons("bot_stats"))
        await callback_query.answer()
    elif data == "show_og_stats":
        await callback_query.message.edit_text(og_stats_text(), reply_markup=section_buttons("og_stats"))
        await callback_query.answer()
    elif data == "show_bot_limits":
        await callback_query.message.edit_text(bot_limits_text(), reply_markup=section_buttons("bot_limits"))
        await callback_query.answer()

    # Refresh sections
    elif data.startswith("refresh_"):
        section = data.split("_")[1]
        if section == "bot_stats":
            await callback_query.message.edit_text(bot_stats_text(), reply_markup=section_buttons("bot_stats"))
        elif section == "og_stats":
            await callback_query.message.edit_text(og_stats_text(), reply_markup=section_buttons("og_stats"))
        elif section == "bot_limits":
            await callback_query.message.edit_text(bot_limits_text(), reply_markup=section_buttons("bot_limits"))
        await callback_query.answer("Refreshed ✅", show_alert=False)

    # Back to main menu
    elif data == "back_to_main":
        await callback_query.message.edit_text("Select a section to view:", reply_markup=main_buttons())
        await callback_query.answer()
      
