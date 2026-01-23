from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.users_chats_db import db
from info import RENAME_MODE

@Client.on_message(filters.private & filters.command('metadata'))
async def metadata_settings(client, message):
    if RENAME_MODE == False:
        return 
        
    # Case 1: No text provided (/metadata) -> Show ON/OFF Buttons
    if len(message.command) == 1:
        # Fetch current status (True/False)
        status = await db.get_metadata_mode(message.from_user.id)
        
        buttons = [
            [
                InlineKeyboardButton(f"ON {'✅' if status else ''}", callback_data="metadata_on"),
                InlineKeyboardButton(f"OFF {'✅' if not status else ''}", callback_data="metadata_off")
            ]
        ]
        
        await message.reply_text(
            "**⚙️ Metadata Settings**\n\n"
            "**Turn Metadata ON or OFF.**\n"
            "When ON, your custom tag will be applied to all renamed files.",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # Case 2: Text provided (/metadata Neon) -> Save the Tag
    tag_text = message.text.split(" ", 1)[1]
    await db.set_metadata_tag(message.from_user.id, tag_text)
    await message.reply_text(f"**✅ Set `{tag_text}` as your metadata tag!**")


@Client.on_callback_query(filters.regex(r'^metadata_(on|off)$'))
async def metadata_callback(client, callback_query):
    # Determine user selection
    mode = callback_query.data.split("_")[1]
    status = True if mode == 'on' else False
    
    # Update Database
    await db.set_metadata_mode(callback_query.from_user.id, status)
    
    # Refresh Buttons to show new ✅
    buttons = [
        [
            InlineKeyboardButton(f"ON {'✅' if status else ''}", callback_data="metadata_on"),
            InlineKeyboardButton(f"OFF {'✅' if not status else ''}", callback_data="metadata_off")
        ]
    ]
    
    await callback_query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(buttons))