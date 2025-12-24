# ---------------------------------------------------
# File Name: CheckAlive.2.py
# Author: MyselfNeon
# Original Repo: https://github.com/MyselfNeon/NeonFilter-Bot
# GitHub: https://github.com/MyselfNeon/
# Telegram: https://t.me/MyelfNeon
# ---------------------------------------------------

import time
import random
from datetime import datetime
from pyrogram import Client, filters

# --- Configuration ---
CMD_PREFIXES = ["/", "."]
START_TIME = datetime.now()

PONG_REPLIES = [
    "⚡ Faster Than Your Wifi !",
    "🔥 Still Alive And Kicking !",
    "🍕 Powered By Vibes & Pizza !",
    "🚀 Zooming Through Cyberspace !!",
    "💡 Running Smooth As Butter !",
    "🎯 Sharp & On Point !"
]

# --- Alive Command ---
@Client.on_message(filters.command("alive", CMD_PREFIXES))
async def check_alive(_, message):
    alive_text = (
        "**__🟢 System Online !!\n"
        "🍀 Luck : Overflowing\n"
        "❤️‍🔥 Spirit : Unbreakable\n\n"
        "✌️ I'm Alive and Ready to Vibe\n"
        "🪬 Summon With /start Command ...__**"
    )
    await message.reply_text(alive_text)

# --- Ping Command ---
@Client.on_message(filters.command("ping", CMD_PREFIXES))
async def ping(_, message):
    # Measure response speed
    start_time = time.time()
    temp_msg = await message.reply_text("**🏓 __Pinging ...__**")
    end_time = time.time()

    elapsed_ms = (end_time - start_time) * 1000

    # Calculate uptime
    uptime = datetime.now() - START_TIME
    uptime_str = str(uptime).split('.')[0]  # hh:mm:ss format

    # Pick a random witty line
    witty_line = random.choice(PONG_REPLIES)

    # Build fun response
    ping_text = (
        f"**🏓 __Pong !!__**\n\n"
        f"⏱️ **__Ping:__** __{elapsed_ms:.2f} ms__\n"
        f"⏳ **__Uptime:__** __{uptime_str}__\n\n"
        f"**__{witty_line}__**\n"
        f"**__@neonfiles__**"
    )

    await temp_msg.edit(ping_text)

# MyselfNeon
# Don't Remove Credit 🥺
# Telegram Channel @NeonFiles
