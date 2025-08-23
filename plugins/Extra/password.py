import random, os
from info import CHNL_LNK
from pyrogram import Client, filters, enums 
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Security tips to display with password
SECURITY_TIPS = [
    "<b><i>Always Use Unique Passwords For Each Account !!</b></i>",
    "<b><i>Combine Letters, Numbers & Symbols For Max Strength !!</b></i>",
    "<b><i>Change Your Passwords Regularly For Safety !!</b></i>",
    "<b><i>Avoid Using Personal Info in Your Passwords !!</b></i>",
    "<b><i>Consider Using a Password Manager For Convenience !!</b></i>"
]

@Client.on_message(filters.command(["genpassword", "genpw"]))
async def password(bot, update):
    message = await update.reply_text("**✨ __Generating your secure password__**")
    
    # Base character sets
    letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    digits = "0123456789"
    symbols = "!@#$%^&*()_+-=[]{}|;:,.<>?/`~"
    
    # Default lengths if not specified
    default_lengths = ["8", "10", "12", "14", "16"]
    
    # Determine password length
    if len(update.command) > 1:
        try:
            length = int(update.text.split(" ", 1)[1])
            if length < 4:
                length = 8  # Minimum length
        except ValueError:
            length = int(random.choice(default_lengths))
    else:
        length = int(random.choice(default_lengths))
    
    # Create password (random mix of letters, digits, symbols)
    all_chars = letters + digits + symbols
    password = "".join(random.sample(all_chars * 3, length))
    
    # Choose a random security tip
    tip = random.choice(SECURITY_TIPS)
    
    # Stylish message
    txt = (
        f"<b><i>Yᴏᴜʀ Sᴇᴄᴜʀᴇ Pᴀssᴡᴏʀᴅ 🔐</i></b>\n\n"
        f"<b><i>🔓 Lᴇɴɢᴛʜ :</i></b> {length}\n"
        f"<b><i>🔑 Pᴀssᴡᴏʀᴅ :</i></b> <code>{password}</code>\n\n"
        f"<i>{tip}</i>\n\n"
        f"<b><i>⚠️ Cᴜsᴛᴏᴍ Lᴇɴɢᴛʜ :</b></i>\n`/genpw 20` <i>to Set Custom Length.</i>"
    )
    
    # Button
    btn = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🌐 Uᴘᴅᴀᴛᴇ Cʜᴀɴɴᴇʟ", url=CHNL_LNK)]]
    )
    
    await message.edit_text(text=txt, reply_markup=btn, parse_mode=enums.ParseMode.HTML)
