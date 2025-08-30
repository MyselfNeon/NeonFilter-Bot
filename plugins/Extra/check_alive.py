import time
from pyrogram import Client, filters

CMD = ["/", "."]

# -----------------------
# ALIVE COMMAND
# -----------------------
@Client.on_message(filters.command("alive", CMD))
async def check_alive(_, message):
    await message.reply_text(
        "**__Guess what? You're Super Lucky 🍀 \n\nI'm alive and ready to Vibe ❤️‍🔥 \n\nHit /start and Let's Roll !!__**"
    )

# -----------------------
# PING COMMAND
# -----------------------
@Client.on_message(filters.command("ping", CMD))
async def ping(_, message):
    start_t = time.time()
    rm = await message.reply_text("Calculating ping...")
    end_t = time.time()
    time_taken_s = (end_t - start_t) * 1000
    await rm.edit(f"Pong!\nResponse Time: {time_taken_s:.3f} ms")

# -----------------------
# START COMMAND (DEEPLINK)
# -----------------------
@Client.on_message(filters.command("start", CMD))
async def start_command(_, message):
    # Check if the user passed a parameter
    if len(message.command) > 1:
        param = message.command[1]  # Grab the parameter
        if param.lower() == "anurag":
            await message.reply_text("Hello Anurag! Welcome 👋")
        else:
            await message.reply_text(f"You passed: {param}")
    else:
        await message.reply_text(
            "Hi there! Use a deeplink to send me a parameter.\nExample: https://t.me/YourBot?start=Anurag"
    )
        
