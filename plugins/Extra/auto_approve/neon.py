# plugins/info.py
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

# Your formatted info text
INFO_TEXT = """
👋 **Hello! I'm Neon** 🇮🇳

🧑‍🎓 **Student:** BAMS (Ayurvedic Medicine)  
💻 **Tech:** Web development & tech exploration  
🎮 **Hobbies:** Anime, memes, and learning new tech  
📫 **Contact:** @MyselfNeon
"""

# Commands that trigger this plugin
@Client.on_message(filters.command(["neon", "admin", "myselfneon", "developer"]))
async def send_info(client: Client, message: Message):
    # Inline buttons stacked vertically
    buttons = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🌐 Telegram", url="https://t.me/MyselfNeon")],
            [InlineKeyboardButton("💻 GitHub", url="https://github.com/MyselfNeon")],
            [InlineKeyboardButton("📸 Instagram", url="https://instagram.com/Neon.an_")]  # Optional
        ]
    )
    
    await message.reply_text(
        INFO_TEXT,
        reply_markup=buttons,
        parse_mode="markdown"  # Enables bold/italics
    )
