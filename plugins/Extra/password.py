import random, os
from info import CHNL_LNK
from pyrogram import Client, filters, enums 
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Security tips to display with password
SECURITY_TIPS = [
    "🔒 Always use unique passwords for each account!",
    "🛡️ Combine letters, numbers & symbols for max strength!",
    "⚡ Change your passwords regularly for safety!",
    "💡 Avoid using personal info in your passwords!",
    "📝 Consider using a password manager for convenience!"
]

@Client.on_message(filters.command(["genpassword", "genpw"]))
async def password(bot, update):
    message = await update.reply_text("`✨ Generating your secure password... 🛠️`")
    
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
        f"🔑 <b>Your Secure Password</b> 🔑\n\n"
        f"<b>Length:</b> {length}\n"
        f"<b>Password:</b> <code>{password}</code>\n\n"
        f"<i>{tip}</i>\n\n"
        f"<b>Example:</b> `/genpw 20` to set custom length."
    )
    
    # Button
    btn = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🌐 Updates Channel", url=CHNL_LNK)]]
    )
    
    await message.edit_text(text=txt, reply_markup=btn, parse_mode=enums.ParseMode.HTML)
