from pyrogram import Client, filters
from pyrogram.types import Message

# ===========================
# 🔹 ISOLATED DEEPLINK HANDLER
# Only responds to /start with a parameter
# ===========================
@Client.on_message(filters.private & filters.regex(r"^/start (\w+)"))
async def isolated_deeplink(client: Client, message: Message):
    try:
        # Extract the parameter after /start
        param = message.text.split(" ", 1)[1]

        # Example: Only handle "Anurag"
        if param.lower() == "anurag":
            await message.reply_text("Neo Anurah")
            
        # Else: do nothing, totally isolated
    except Exception:
        # Ignore any errors to prevent crashing
        pass
