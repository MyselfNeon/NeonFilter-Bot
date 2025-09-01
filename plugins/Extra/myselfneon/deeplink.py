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

        # Example: Only handle "repolink"
        if param.lower() == "repolink":
            await message.reply_text(
                "<b><i>🍀 Rᴇᴘᴏsɪᴛᴏʀʏ Lɪɴᴋ 🍀\n\n"
                "Tʜᴇ Rᴇᴘᴏsɪᴛᴏʀʏ Is Cᴜʀʀᴇɴᴛʟʏ Pʀɪᴠᴀᴛᴇ Dᴜᴇ Tᴏ Sᴏᴍᴇ Oɴɢᴏɪɴɢ Wᴏʀᴋ. "
                "Hᴏᴡᴇᴠᴇʀ, Iғ Yᴏᴜ Aʀᴇ Iɴᴛᴇʀᴇsᴛᴇᴅ Iɴ Oᴜʀ Bᴏᴛ Aɴᴅ Iᴛs Fᴇᴀᴛᴜʀᴇs, "
                "I Wᴏᴜʟᴅ Bᴇ Hᴀᴘᴘʏ Tᴏ Gʀᴀɴᴛ Yᴏᴜ Aᴄᴄᴇss.\n\n"
                "Cᴏɴᴛᴀᴄᴛ : <a href='https://t.me/Talk2NeonBot'>@Tᴀʟᴋ𝟸NᴇᴏɴBᴏᴛ</a></i></b>"
            )
    except Exception:
        pass


# Dont remove Credits
# Developer Telegram @MyselfNeon
# Update channel - @NeonFiles
