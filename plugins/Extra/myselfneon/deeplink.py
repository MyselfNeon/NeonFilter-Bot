from pyrogram import Client, filters
from pyrogram.types import Message

# ===========================
# 🔹 COMMAND PREFIXES
# ===========================
CMD_PREFIXES = ["/", "."]

# ===========================
# 🔹 DEEPLINK HANDLER
# This only responds when a start parameter is provided
# Example: https://t.me/ZeroFilterBot?start=Anurag
# ===========================
@Client.on_message(filters.private & filters.command("start", CMD_PREFIXES))
async def deeplink_start(client: Client, message: Message):
    
    # Only trigger if there's a parameter in /start
    if len(message.command) > 1:
        param = message.command[1]

        # Hardcoded mapping for "Anurag"
        if param.lower() == "anurag":
            await message.reply_text("Neo Anurah")
            
    # If no parameter, do nothing to avoid interfering with main /start
