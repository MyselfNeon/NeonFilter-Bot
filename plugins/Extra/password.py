import random
from info import CHNL_LNK
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message

# Security tips to display with password
SECURITY_TIPS = [
    "Always Use Unique Passwords For Each Account !!",
    "Combine Letters, Numbers & Symbols For Max Strength !!",
    "Change Your Passwords Regularly For Safety !!",
    "Avoid Using Personal Info in Your Passwords !!",
    "Consider Using a Password Manager For Convenience !!"
]

# Password generator function
async def generate_password(length: int) -> str:
    letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    digits = "0123456789"
    symbols = "!@#$%^&*()_+-=[]{}|;:,.<>?/`~"
    all_chars = letters + digits + symbols
    return "".join(random.sample(all_chars * 3, length))

# Main /genpassword command
@Client.on_message(filters.command(["genpassword", "genpw"]))
async def password(bot: Client, update: Message):
    message = await update.reply_text("**✨ __Generating your secure password__**")
    
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
    
    # Generate password and pick a random security tip
    pw = await generate_password(length)
    tip = random.choice(SECURITY_TIPS)
    
    # Stylish message
    txt = (
        f"<b><i><blockquote>Yᴏᴜʀ Sᴇᴄᴜʀᴇ Pᴀssᴡᴏʀᴅ 🔐</blockquote></i></b>\n\n"
        f"<b><i>🔓 Lᴇɴɢᴛʜ :</i></b> {length}\n"
        f"<b><i>🔑 Pᴀssᴡᴏʀᴅ :</i></b> <code>{pw}</code>\n\n"
        f"<i><b><blockquote>{tip}</blockquote></b></i>\n\n"
        f"<b><i>⚠️ Cᴜsᴛᴏᴍ Lᴇɴɢᴛʜ :</b></i>\n<code>/genpw 20</code> <i>to Set Custom Length.</i>"
    )
    
    btn = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("🛐 Oᴡɴᴇʀ", callback_data="OWNER_LNK"),
            InlineKeyboardButton("🔄 Rᴇғʀᴇsʜ", callback_data="refresh")
        ]]
    )
    
    await message.edit_text(text=txt, reply_markup=btn, parse_mode=enums.ParseMode.HTML)

# Handle button clicks
@Client.on_callback_query()
async def button_handler(bot: Client, query: CallbackQuery):
    if query.data == "home":
        # Show a simple home message
        await query.message.edit_text(
            "🏠 Welcome! Use the commands below:\n\n"
            "/genpw - Generate a secure password\n"
            "/start - Start the bot"
        )
    elif query.data == "refresh":
        # Regenerate password in the same message
        # Determine a default random length between 8-16
        length = random.choice([8, 10, 12, 14, 16])
        pw = await generate_password(length)
        tip = random.choice(SECURITY_TIPS)
        txt = (
            f"<b><i><blockquote>Yᴏᴜʀ Sᴇᴄᴜʀᴇ Pᴀssᴡᴏʀᴅ 🔐</blockquote></i></b>\n\n"
            f"<b><i>🔓 Lᴇɴɢᴛʜ :</i></b> {length}\n"
            f"<b><i>🔑 Pᴀssᴡᴏʀᴅ :</i></b> <code>{pw}</code>\n\n"
            f"<i><b><blockquote>{tip}</blockquote></b></i>\n\n"
            f"<b><i>⚠️ Cᴜsᴛᴏᴍ Lᴇɴɢᴛʜ :</b></i>\n<code>/genpw 23</code> <i>to Set Custom Length.</i>"
        )
        await query.message.edit_text(
            text=txt,
            reply_markup=query.message.reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    # Always answer callback query to remove "loading" state
    await query.answer()
