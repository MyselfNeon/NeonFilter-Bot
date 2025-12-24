# ---------------------------------------------------
# File Name: ShareText.2.py
# Author: MyselfNeon
# Original Repo: https://github.com/MyselfNeon/NeonFilter-Bot
# GitHub: https://github.com/MyselfNeon/
# Telegram: https://t.me/MyelfNeon
# ---------------------------------------------------

# --- Imports ---
import urllib.parse
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import CHNL_LNK

# --- Helpers ---
def generate_share_link(text: str):
    """Encodes text safely for Telegram Share URLs"""
    encoded = urllib.parse.quote(text)
    return f"https://t.me/share/url?url={encoded}"

# --- Handlers ---
@Client.on_message(filters.command(["sharetext"]))
async def share_text(client: Client, message: Message):
    input_text = None

    # 1️⃣ Case: Argument (/share Hello)
    if len(message.command) > 1:
        input_text = message.text.split(maxsplit=1)[1]

    # 2️⃣ Case: Reply (Reply to message with /share)
    elif message.reply_to_message:
        if message.reply_to_message.text:
            input_text = message.reply_to_message.text
        elif message.reply_to_message.caption:
            input_text = message.reply_to_message.caption

    # 3️⃣ Case: Interactive (Ask user)
    else:
        try:
            ask_msg = await client.ask(
                message.chat.id, 
                "**__Now Send Me Your Text__ 😄**", 
                timeout=30
            )
            if ask_msg.text or ask_msg.caption:
                input_text = ask_msg.text or ask_msg.caption
            else:
                # Notice: If user sends media or nothing
                return await ask_msg.reply_text(
                    text=(
                        "**__Notice:__**\n\n"
                        "**01. Send Any Text Messages.**\n"
                        "**02. No Media Support**\n\n"
                        "**Join Update Channel**"
                    ),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Updates Channel", url=CHNL_LNK)]
                    ])
                )
        except Exception as e:
            return await message.reply_text(f"**Error:** {e}")

    # Output
    if input_text:
        share_url = generate_share_link(input_text)
        
        # Smart Buttons: Share + New QR Code Feature
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 ꜱʜᴀʀᴇ ɴᴏᴡ", url=share_url)],
            [InlineKeyboardButton("📱 ɢᴇᴛ ǫʀ ᴄᴏᴅᴇ", callback_data=f"gen_qr|{share_url}")]
        ])

        await message.reply_text(
            text=f"**__Here is Your Sharing Text__ 👇**\n\n{share_url}",
            reply_markup=buttons,
            disable_web_page_preview=True
        )

@Client.on_callback_query(filters.regex("^gen_qr"))
async def qr_handler(client: Client, query: CallbackQuery):
    """Generates a QR code when the button is clicked"""
    try:
        # Extract the share URL from the button data
        share_url = query.data.split("|")[1]
        
        # Use simple API to generate QR
        qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={share_url}"
        
        await query.message.reply_photo(
            photo=qr_api,
            caption="**📱 Here is your QR Code**\n__Scan this to share the text!__",
            quote=True
        )
        await query.answer()
    except Exception as e:
        await query.answer("Failed to generate QR or text too long", show_alert=True)

# MyselfNeon
# Don't Remove Credit 🥺
# Telegram Channel @NeonFiles
