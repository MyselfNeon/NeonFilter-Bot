from pyrogram import Client, filters

@Client.on_message(filters.command("stickerid") & filters.private)
async def sticker_to_id(bot, message):
    """
    Ask user to send a sticker and reply with its file_id and unique_id
    """
    try:
        s_msg = await bot.ask(chat_id=message.from_user.id, text="**🌐 Now Send Me Your Sticker**")
        if s_msg.sticker:
            await s_msg.reply_text(
                f"**⁉️ --Sticker ID--**\n`{s_msg.sticker.file_id}`\n\n"
                f"**🆔 --Unique ID--**\n`{s_msg.sticker.file_unique_id}`"
            )
        else:
            await s_msg.reply_text("**❌ Oops! Not a sticker file.**")
    except Exception as e:
        await message.reply_text(f"**❌ Error:** {e}")


@Client.on_message(filters.command("getsticker") & filters.private)
async def id_to_sticker(bot, message):
    """
    Send a sticker back if user provides its file_id
    """
    if len(message.command) < 2:
        return await message.reply_text(
            "**❌ Please provide a Sticker File ID after the command!**\n\n"
            "Example:\n/getsticker CAACAgUAAxkBAAIxhWjR-PZ10lV7aYzUWqeFLvecHT-iAAIEAAPBJDExieUdbguzyBAeBA"
        )
    
    sticker_id = message.text.split(None, 1)[1].strip()
    
    try:
        await bot.send_sticker(message.chat.id, sticker_id)
    except Exception as e:
        await message.reply_text(f"**❌ Failed to send sticker!**\nError: `{e}`")
        
