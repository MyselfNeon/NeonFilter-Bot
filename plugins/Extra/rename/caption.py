
from pyrogram import Client, filters 
from database.users_chats_db import db
from info import RENAME_MODE

@Client.on_message(filters.private & filters.command('set_caption'))
async def add_caption(client, message):
    if RENAME_MODE == False:
        return 
    caption = await client.ask(message.chat.id, "**__Give me a Caption to Set__ 😇**\n\n**__Available Filling__** :-\n<blockquote>**📂 __File Name__**: `{filename}`\n\n**💾 __Size__**: `{filesize}`\n\n**⏰ __Duration__**: `{duration}`</blockquote>**")
    await db.set_caption(message.from_user.id, caption=caption.text)
    await message.reply_text("__**Your Caption is Successfully Saved ✅**__")

    
@Client.on_message(filters.private & filters.command('del_caption'))
async def delete_caption(client, message):
    if RENAME_MODE == False:
        return 
    caption = await db.get_caption(message.from_user.id)  
    if not caption:
       return await message.reply_text("🥹 **__Sorry !! No Caption found...__** 🥹")
    await db.set_caption(message.from_user.id, caption=None)
    await message.reply_text("**__Your Caption is Successfully Deleted__** ❌")
                                       
@Client.on_message(filters.private & filters.command('see_caption'))
async def see_caption(client, message):
    if RENAME_MODE == False:
        return 
    caption = await db.get_caption(message.from_user.id)  
    if caption:
       await message.reply_text(f"**Your Caption:-**\n\n`{caption}`")
    else:
       await message.reply_text("🥹 **__Sorry !! No Caption found...__** 🥹")
