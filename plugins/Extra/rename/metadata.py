import json
import os
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from pyromod.exceptions import ListenerTimeout
from config import Txt

# JSON storage path
METADATA_FILE = "metadata.json"

# Ensure file exists
if not os.path.exists(METADATA_FILE):
    with open(METADATA_FILE, "w") as f:
        json.dump({}, f)


def load_metadata():
    with open(METADATA_FILE, "r") as f:
        return json.load(f)


def save_metadata(data):
    with open(METADATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_user_metadata(user_id):
    data = load_metadata()
    return data.get(str(user_id), {"enabled": False, "code": ""})


def set_user_metadata(user_id, enabled=None, code=None):
    data = load_metadata()
    user = data.get(str(user_id), {"enabled": False, "code": ""})
    if enabled is not None:
        user["enabled"] = enabled
    if code is not None:
        user["code"] = code
    data[str(user_id)] = user
    save_metadata(data)


ON = [[InlineKeyboardButton('Metadata On ✅', callback_data='metadata_on')],
      [InlineKeyboardButton('Set Custom Metadata', callback_data='custom_metadata')]]

OFF = [[InlineKeyboardButton('Metadata Off ❌', callback_data='metadata_off')],
       [InlineKeyboardButton('Set Custom Metadata', callback_data='custom_metadata')]]


@Client.on_message(filters.private & filters.command('metadata'))
async def handle_metadata(bot: Client, message: Message):
    user_meta = get_user_metadata(message.from_user.id)
    kb = InlineKeyboardMarkup(ON if user_meta["enabled"] else OFF)

    await message.reply_text(
        f"**Your Current Metadata :-**\n\n➜ `{user_meta['code']}`",
        quote=True,
        reply_markup=kb
    )


@Client.on_callback_query(filters.regex(r'^(metadata_on|metadata_off|custom_metadata|back_metadata)$'))
async def query_metadata(bot: Client, query: CallbackQuery):
    user_id = query.from_user.id
    user_meta = get_user_metadata(user_id)
    data = query.data

    if data == "metadata_on":
        set_user_metadata(user_id, enabled=False)
        await query.message.edit(
            f"**Your Current Metadata :-**\n\n➜ `{user_meta['code']}`",
            reply_markup=InlineKeyboardMarkup(OFF)
        )
    elif data == "metadata_off":
        set_user_metadata(user_id, enabled=True)
        await query.message.edit(
            f"**Your Current Metadata :-**\n\n➜ `{user_meta['code']}`",
            reply_markup=InlineKeyboardMarkup(ON)
        )
    elif data == 'custom_metadata':
        await query.message.delete()
        try:
            metadata = await bot.ask(
                text=Txt.SEND_METADATA,
                chat_id=user_id,
                filters=filters.text,
                timeout=30,
                disable_web_page_preview=True
            )
            set_user_metadata(user_id, code=metadata.text)

            await bot.send_message(
                user_id,
                "**Your Metadata Code Set Successfully ✅**",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton('⬅️ Back', callback_data='back_metadata')]]
                )
            )
        except ListenerTimeout:
            await bot.send_message(user_id, "⚠️ Request Timed Out.\n\nRestart By Using /metadata")
    elif data == 'back_metadata':
        user_meta = get_user_metadata(user_id)
        kb = InlineKeyboardMarkup(ON if user_meta["enabled"] else OFF)
        await query.message.edit(
            f"**Your Current Metadata :-**\n\n➜ `{user_meta['code']}`",
            reply_markup=kb
)
