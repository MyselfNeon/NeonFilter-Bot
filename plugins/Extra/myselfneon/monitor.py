import hashlib
import requests
import asyncio
from pyrogram import Client, filters
from info import BOT_TOKEN  # import only your bot token

# === CONFIG ===
CHAT_ID = -1002596933554
URL = "https://platinmods.com/forums/untested-android-apps.155/"
HASH_FILE = "last_hash.txt"

# this should use the existing client instead of creating new
# if you use multi_clients or something like NeonBot, replace "Client" with that name
bot = Client("NeonMonitor", bot_token=BOT_TOKEN)

# === PAGE CHECKER ===
def get_page_hash():
    try:
        response = requests.get(URL, timeout=10)
        response.raise_for_status()
        return hashlib.sha256(response.text.encode('utf-8')).hexdigest()
    except Exception as e:
        print(f"[Error fetching page] {e}")
        return None

async def check_page_change():
    current_hash = get_page_hash()
    if not current_hash:
        return

    try:
        with open(HASH_FILE, "r") as f:
            last_hash = f.read().strip()
    except FileNotFoundError:
        last_hash = ""

    if current_hash != last_hash:
        with open(HASH_FILE, "w") as f:
            f.write(current_hash)
        await bot.send_message(CHAT_ID, f"⚠️ **Platinmods Page Changed!**\n🔗 {URL}")
        print("[+] Change detected and notified!")
    else:
        print("[=] No change detected.")

# === COMMANDS ===
@bot.on_message(filters.command("helpmonitor"))
async def help_monitor(_, message):
    await message.reply_text(
        "**🕵️ Page Monitor Bot Help**\n\n"
        "/checkpage - Manually check the page for any changes\n"
        "/startmonitor - Start automatic monitoring (every 5 min)\n"
        "/stopmonitor - Stop automatic monitoring"
    )

@bot.on_message(filters.command("checkpage"))
async def manual_check(_, message):
    await check_page_change()
    await message.reply_text("✅ Page checked manually!")

monitor_task = None

@bot.on_message(filters.command("startmonitor"))
async def start_monitor(_, message):
    global monitor_task
    if monitor_task and not monitor_task.done():
        return await message.reply_text("🟢 Monitoring already running!")

    async def monitor_loop():
        while True:
            await check_page_change()
            await asyncio.sleep(300)  # 5 min

    monitor_task = asyncio.create_task(monitor_loop())
    await message.reply_text("🚀 Monitoring started (every 5 min)!")

@bot.on_message(filters.command("stopmonitor"))
async def stop_monitor(_, message):
    global monitor_task
    if monitor_task and not monitor_task.done():
        monitor_task.cancel()
        await message.reply_text("🛑 Monitoring stopped.")
    else:
        await message.reply_text("⚠️ Monitoring not running.")
