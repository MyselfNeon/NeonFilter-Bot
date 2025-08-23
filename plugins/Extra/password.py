import random, os
from info import OWNER_LNK
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Security tips to display with password
SECURITY_TIPS = [
    "Always Use Unique Passwords For Each Account !!",
    "Combine Letters, Numbers & Symbols For Max Strength !!",
    "Change Your Passwords Regularly For Safety !!",
    "Avoid Using Personal Info in Your Passwords !!",
    "Consider Using a Password Manager For Convenience !!"
]

# Function to generate a password
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
    # Determine length if user provided it
    if len(update.command) > 1:
        try:
            length = int(update.text.split(" ", 1)[1])
        except ValueError:
            length = None
    else:
        length = None

    password_str, length, tip = generate_password(length)
    
    txt = (
        f"<b><i><blockquote>Yᴏᴜʀ Sᴇᴄᴜʀᴇ Pᴀssᴡᴏʀᴅ 🔐</blockquote></i></b>\n\n"
        f"<b><i>🔓 Lᴇɴɢᴛʜ :</i></b> {length}\n"
        f"<b><i>🔑 Pᴀssᴡᴏʀᴅ :</i></b> <code>{password_str}</code>\n\n"
        f"<i><b><blockquote>{tip}</blockquote></b></i>\n\n"
        f"<b><i>⚠️ Cᴜsᴛᴏᴍ Lᴇɴɢᴛʜ :</b></i>\n<code>/genpw 20</code> <i>to Set Custom Length.</i>"
    )

    # Buttons: Update Owner Link on left, Refresh on right
    btn = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("🌐 Owner Link", url=OWNER_LNK),
            InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{length}")
        ]]
    )
    
    await update.reply_text(text=txt, reply_markup=btn, parse_mode=enums.ParseMode.HTML)

# Callback handler for refresh button
@Client.on_callback_query(filters.regex(r"refresh_(\d+)"))
async def refresh_password(bot, query: CallbackQuery):
    length = int(query.data.split("_")[1])
    password_str, length, tip = generate_password(length)
    
    txt = (
        f"<b><i><blockquote>Yᴏᴜʀ Sᴇᴄᴜʀᴇ Pᴀssᴡᴏʀᴅ 🔐</blockquote></i></b>\n\n"
        f"<b><i>🔓 Lᴇɴɢᴛʜ :</i></b> {length}\n"
        f"<b><i>🔑 Pᴀssᴡᴏʀᴅ :</i></b> <code>{password_str}</code>\n\n"
        f"<i><b><blockquote>{tip}</blockquote></b></i>\n\n"
        f"<b><i>⚠️ Cᴜsᴛᴏᴍ Lᴇɴɢᴛʜ :</b></i>\n<code>/genpw 20</code> <i>to Set Custom Length.</i>"
    )
    
    # Keep same buttons: Owner link left, Refresh right
    btn = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("🌐 Owner Link", url=OWNER_LNK),
            InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{length}")
        ]]
    )
    
    await query.message.edit_text(text=txt, reply_markup=btn, parse_mode=enums.ParseMode.HTML)
    await query.answer("Password refreshed 🔄")
