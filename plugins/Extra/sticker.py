from pyrogram import Client, filters

@Client.on_message(filters.command("sticker") & filters.private)
async def sticker_handler(bot, message):
    """
    Unified command:
    1️⃣ /sticker <file_id> [file_id2 ...] → Sends back provided stickers.
    2️⃣ /sticker → Prompts user to send a sticker and returns its file_id and unique_id.
    """
    # If command includes arguments (sticker IDs)
    if len(message.command) > 1:
        sticker_ids = message.text.split()[1:]  # all arguments after command
        for sid in sticker_ids:
            try:
                await bot.send_sticker(message.chat.id, sid)
            except Exception as e:
                await message.reply_text(f"**❌ Failed to send sticker `{sid}`!**\nError: `{e}`")
        return

    # No arguments → ask user to send a sticker
    try:
        s_msg = await bot.ask(chat_id=message.from_user.id, text="**🌐 Please send a sticker to get its ID**")
        if s_msg.sticker:
            await s_msg.reply_text(
                f"**⁉️ Sticker ID:**\n`{s_msg.sticker.file_id}`\n\n"
                f"**🆔 Unique ID:**\n`{s_msg.sticker.file_unique_id}`"
            )
        else:
            await s_msg.reply_text("**❌ That is not a sticker. Please send a valid sticker.**")
    except Exception as e:
        await message.reply_text(f"**❌ Error:** {e}")
