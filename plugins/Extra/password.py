import random
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

OWNER_TG_ID = 841851780  # Your Telegram ID

# Security tips
SECURITY_TIPS = [
    "Always Use Unique Passwords For Each Account !!",
    "Combine Letters, Numbers & Symbols For Max Strength !!",
    "Change Your Passwords Regularly For Safety !!",
    "Avoid Using Personal Info in Your Passwords !!",
    "Consider Using a Password Manager For Convenience !!"
]

# In-memory dictionary to store user custom lengths
user_lengths = {}

# Function to generate password
def generate_password(length=None):
    letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    digits = "0123456789"
    symbols = "!@#$%^&*()_+-=[]{}|;:,.<>?/`~"

    default_lengths = [8, 10, 12, 14, 16]
    if length is None:
        length = random.choice(default_lengths)
    elif length < 4:
        length = 8

    all_chars = letters + digits + symbols
    password = "".join(random.sample(all_chars * 3, length))
    tip = random.choice(SECURITY_TIPS)
    return password, length, tip

# Command handler
@Client.on_message(filters.command(["genpassword", "genpw"]))
async def password(bot, update):
    user_id = update.from_user.id

    # Determine length
    length = None
    if len(update.command) > 1:
        try:
            length = int(update.text.split(" ", 1)[1])
            user_lengths[user_id] = length  # Save custom length for this user
        except ValueError:
            pass
    elif user_id in user_lengths:
        length = user_lengths[user_id]  # Use stored custom length

    password_str, length, tip = generate_password(length)

    txt = (
        f"<b><i><blockquote>Yᴏᴜʀ Sᴇᴄᴜʀᴇ Pᴀssᴡᴏʀᴅ 🔐</blockquote></i></b>\n\n"
        f"<b><i>🔓 Lᴇɴɢᴛʜ :</i></b> {length}\n"
        f"<b><i>🔑 Pᴀssᴡᴏʀᴅ :</i></b> <code>{password_str}</code>\n\n"
        f"<i><b><blockquote>{tip}</blockquote></b></i>\n\n"
        f"<b><i>⚠️ Cᴜsᴛᴏᴍ Lᴇɴɢᴛʜ :</b></i>\n<code>/genpw 20</code> <i>to Set Custom Length.</i>"
    )

    # Buttons: Telegram account left, Refresh right
    btn = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("🛐 Dᴇᴠᴇʟᴏᴘᴇʀ", url="https://t.me/MyselfNeon"),
            InlineKeyboardButton("🔄 Rᴇғʀᴇsʜ", callback_data=f"refresh_{user_id}")
        ]]
    )

    await update.reply_text(text=txt, reply_markup=btn, parse_mode=enums.ParseMode.HTML)

# Callback handler
@Client.on_callback_query(filters.regex(r"refresh_(\d+)"))
async def refresh_password(bot, query: CallbackQuery):
    user_id = int(query.data.split("_")[1])
    length = user_lengths.get(user_id, None)  # Retrieve saved length if exists

    password_str, length, tip = generate_password(length)

    txt = (
        f"<b><i><blockquote>Yᴏᴜʀ Sᴇᴄᴜʀᴇ Pᴀssᴡᴏʀᴅ 🔐</blockquote></i></b>\n\n"
        f"<b><i>🔓 Lᴇɴɢᴛʜ :</i></b> {length}\n"
        f"<b><i>🔑 Pᴀssᴡᴏʀᴅ :</i></b> <code>{password_str}</code>\n\n"
        f"<i><b><blockquote>{tip}</blockquote></b></i>\n\n"
        f"<b><i>⚠️ Cᴜsᴛᴏᴍ Lᴇɴɢᴛʜ :</b></i>\n<code>/genpw 20</code> <i>to Set Custom Length.</i>"
    )

    # Keep buttons same
    btn = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("🛐 Dᴇᴠᴇʟᴏᴘᴇʀ", url="https://t.me/MyselfNeon"),
            InlineKeyboardButton("🔄 Rᴇғʀᴇsʜ", callback_data=f"refresh_{user_id}")
        ]]
    )

    await query.message.edit_text(text=txt, reply_markup=btn, parse_mode=enums.ParseMode.HTML)
    await query.answer("Password refreshed 🔄")
