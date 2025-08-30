import time
from pyrogram import Client, filters

# Command prefixes
CMD_PREFIXES = ["/", "."]

# ===========================
# 🔹 ALIVE COMMAND
# ===========================
@Client.on_message(filters.command("alive", CMD_PREFIXES))
async def check_alive(_, message):
    alive_text = (
        "**__Guess what? You're Super Lucky 🍀\n\n"
        "I'm alive and ready to Vibe ❤️‍🔥\n\n"
        "Hit /start and Let's Roll !!__**"
    )
    await message.reply_text(alive_text)


# ===========================
# 🔹 PING COMMAND
# ===========================
@Client.on_message(filters.command("ping", CMD_PREFIXES))
async def ping(_, message):
    start_time = time.time()
    temp_msg = await message.reply_text("...")
    end_time = time.time()

    elapsed_ms = (end_time - start_time) * 1000
    await temp_msg.edit(f"Pong!\n`{elapsed_ms:.3f} ms`")
    
