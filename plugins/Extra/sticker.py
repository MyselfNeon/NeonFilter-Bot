from pyrogram import Client, filters

@Client.on_message(filters.command("stickerid") & filters.private)
async def stickerid(bot, message):
    s_msg = await bot.ask(chat_id = message.from_user.id, text = "**__Now Send Me Your Sticker__ 🤓**")
    if s_msg.sticker:
        await s_msg.reply_text(f"**__Sticker ID is__** \n`{s_msg.sticker.file_id}` \n\n **__Unique ID is__** \n\n`{s_msg.sticker.file_unique_id}`")
    else: 
        await s_msg.reply_text("**__Oops !! Not a sticker File__ ❌**")
