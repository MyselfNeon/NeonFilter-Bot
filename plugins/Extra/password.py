# ---------------------------------------------------
# File Name: Password.2.py
# Author: MyselfNeon
# Original Repo: https://github.com/MyselfNeon/NeonFilter-Bot
# GitHub: https://github.com/MyselfNeon/
# Telegram: https://t.me/MyelfNeon
# ---------------------------------------------------

import secrets
import string
import math
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import ADMINS

# In-memory settings storage. 
USER_SETTINGS = {}

DEFAULT_SETTINGS = {
    'length': 14,
    'upper': True,
    'digits': True,
    'symbols': True,
    'ambiguous': False # Key is 'ambiguous'
}

# --- HELPER FUNCTIONS ---
def get_settings(user_id):
    if user_id not in USER_SETTINGS:
        USER_SETTINGS[user_id] = DEFAULT_SETTINGS.copy()
    return USER_SETTINGS[user_id]

def calculate_entropy(password, pool_size):
    if not password: return 0
    return len(password) * math.log2(pool_size)

def get_strength_bar(entropy):
    if entropy < 28: return "🟥⬜️⬜️⬜️⬜️ (Very Weak)"
    elif entropy < 36: return "🟥🟥⬜️⬜️⬜️ (Weak)"
    elif entropy < 60: return "🟨🟨🟨⬜️⬜️ (Medium)"
    elif entropy < 128: return "🟩🟩🟩🟩⬜️ (Strong)"
    else: return "🟩🟩🟩🟩🟩 (Unbreakable)"

def generate_secure_password(settings):
    # Always start with lowercase
    chars = string.ascii_lowercase
    pool_size = 26

    if settings['upper']:
        chars += string.ascii_uppercase
        pool_size += 26
    if settings['digits']:
        chars += string.digits
        pool_size += 10
    if settings['symbols']:
        chars += "!@#$%^&*()_+-=[]{}|;:,.<>?/`~"
        pool_size += 30
    
    # Remove ambiguous characters if requested
    if settings['ambiguous']:
        ambiguous_chars = "1lI0O" 
        table = str.maketrans('', '', ambiguous_chars)
        chars = chars.translate(table)
        pool_size = max(1, pool_size - len(ambiguous_chars))

    # Safety net: if pool is somehow empty, revert to lowercase
    if not chars:
        chars = string.ascii_lowercase
        pool_size = 26

    password = "".join(secrets.choice(chars) for _ in range(settings['length']))
    return password, pool_size

def build_keyboard(user_id, settings):
    s_upper = "✅" if settings['upper'] else "❌"
    s_digits = "✅" if settings['digits'] else "❌"
    s_symbols = "✅" if settings['symbols'] else "❌"
    s_ambig = "🚫" if settings['ambiguous'] else "👁️"

    keyboard = [
        [
            InlineKeyboardButton(f"A-Z {s_upper}", callback_data=f"pw_toggle_upper_{user_id}"),
            InlineKeyboardButton(f"0-9 {s_digits}", callback_data=f"pw_toggle_digits_{user_id}"),
            InlineKeyboardButton(f"@#$ {s_symbols}", callback_data=f"pw_toggle_symbols_{user_id}")
        ],
        [
            # FIXED: callback_data now uses 'ambiguous' to match the dict key
            InlineKeyboardButton(f"No Confusing Chars {s_ambig}", callback_data=f"pw_toggle_ambiguous_{user_id}")
        ],
        [
            InlineKeyboardButton("➖", callback_data=f"pw_len_down_{user_id}"),
            InlineKeyboardButton(f"📏 Length: {settings['length']}", callback_data="pw_noop"),
            InlineKeyboardButton("➕", callback_data=f"pw_len_up_{user_id}")
        ],
        [
            InlineKeyboardButton("🔄 Gᴇɴᴇʀᴀᴛᴇ Nᴇᴡ", callback_data=f"pw_refresh_{user_id}")
        ],
        [
            InlineKeyboardButton("🗑️ Cʟᴏsᴇ", callback_data=f"pw_close_{user_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- HANDLERS --- 
@Client.on_message(filters.command(["genpw", "pw"]))
async def password_command(bot, message):
    user_id = message.from_user.id
    settings = get_settings(user_id)
    
    password, pool_size = generate_secure_password(settings)
    entropy = calculate_entropy(password, pool_size)
    strength_text = get_strength_bar(entropy)

    txt = (
        f"<b>🔐 Sᴇᴄᴜʀᴇ Pᴀssᴡᴏʀᴅ Gᴇɴᴇʀᴀᴛᴏʀ</b>\n\n"
        f"<code>{password}</code>\n\n"
        f"📊 <b>Sᴛʀᴇɴɢᴛʜ:</b> {strength_text}\n"
        f"🔢 <b>Eɴᴛʀᴏᴘʏ:</b> {int(entropy)} bits\n"
        f"👇 <i>Customize your settings below:</i>"
    )

    await message.reply_text(
        text=txt,
        reply_markup=build_keyboard(user_id, settings),
        parse_mode=enums.ParseMode.HTML
    )

@Client.on_callback_query(filters.regex(r"^pw_"))
async def password_callback(bot, query: CallbackQuery):
    data = query.data.split("_")
    action = data[1]
    
    if action == "noop":
        await query.answer("Use + or - to change length.")
        return

    try:
        owner_id = int(data[-1])
    except ValueError:
        await query.answer("Error: Invalid data.", show_alert=True)
        return

    if query.from_user.id != owner_id:
        await query.answer("⚠️ This is not your control panel.", show_alert=True)
        return

    settings = get_settings(owner_id)

    if action == "refresh":
        pass 
    
    elif action == "close":
        await query.message.delete()
        return

    elif action == "toggle":
        setting_key = data[2] 
        # This will now correctly find 'ambiguous', 'upper', etc.
        if setting_key in settings:
            settings[setting_key] = not settings[setting_key]
        else:
            await query.answer(f"Error: Unknown setting {setting_key}", show_alert=True)
            return

    elif action == "len":
        direction = data[2]
        if direction == "up" and settings['length'] < 64:
            settings['length'] += 1
        elif direction == "down" and settings['length'] > 4:
            settings['length'] -= 1
        else:
            await query.answer("Limit reached (4-64 chars)")
            return

    USER_SETTINGS[owner_id] = settings

    password, pool_size = generate_secure_password(settings)
    entropy = calculate_entropy(password, pool_size)
    strength_text = get_strength_bar(entropy)

    txt = (
        f"<b>🔐 Sᴇᴄᴜʀᴇ Pᴀssᴡᴏʀᴅ Gᴇɴᴇʀᴀᴛᴏʀ</b>\n\n"
        f"<code>{password}</code>\n\n"
        f"📊 <b>Sᴛʀᴇɴɢᴛʜ:</b> {strength_text}\n"
        f"🔢 <b>Eɴᴛʀᴏᴘʏ:</b> {int(entropy)} bits\n"
        f"👇 <i>Customize your settings below:</i>"
    )

    try:
        await query.message.edit_text(
            text=txt,
            reply_markup=build_keyboard(owner_id, settings),
            parse_mode=enums.ParseMode.HTML
        )
    except Exception:
        pass
        
# MyselfNeon
# Don't Remove Credit 🥺
# Telegram Channel @NeonFiles
