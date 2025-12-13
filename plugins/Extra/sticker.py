# Sticker_Tools.py
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

@Client.on_message(filters.command(["sticker", "id"]))
async def sticker_tool(bot: Client, message: Message):
    """
    Advanced Sticker Tool:
    1. Reply to a sticker -> Get comprehensive details (ID, Set, Emoji, etc).
    2. /sticker <file_id> -> Send the sticker by ID.
    3. /sticker -> Interactive mode (Waits for you to send one).
    """

    # -----------------------------------------------
    # 1️⃣ Mode: Reply to a sticker
    # -----------------------------------------------
    if message.reply_to_message and message.reply_to_message.sticker:
        await send_sticker_details(message.reply_to_message, message)
        return

    # -----------------------------------------------
    # 2️⃣ Mode: Arguments provided (Send Sticker by ID)
    # -----------------------------------------------
    if len(message.command) > 1:
        ids = message.text.split()[1:]
        sent_count = 0
        
        status_msg = await message.reply_text("🔄 **Processing Request...**")
        
        for sid in ids:
            try:
                await bot.send_sticker(message.chat.id, sid)
                sent_count += 1
                await asyncio.sleep(0.3) # Prevent FloodWait
            except Exception as e:
                await message.reply_text(f"❌ **Failed to send:** `{sid}`\n**Reason:** {e}")
        
        await status_msg.delete()
        return

    # -----------------------------------------------
    # 3️⃣ Mode: Interactive (Ask User)
    # -----------------------------------------------
    try:
        # Prompt the user
        ask_msg = await bot.ask(
            message.chat.id, 
            "**👋 Send me a Sticker now!**\n\n__I will analyze it and give you the IDs.__",
            timeout=60,
            filters=filters.sticker
        )
        
        # Process the response
        await send_sticker_details(ask_msg, ask_msg)
        
    except asyncio.TimeoutError:
        await message.reply_text("❌ **Time up!** Run the command again.")
    except Exception as e:
        await message.reply_text(f"❌ **Error:** {e}")


async def send_sticker_details(sticker_message: Message, reply_target: Message):
    """Helper to format and send sticker info."""
    st = sticker_message.sticker
    
    # 1. Determine Type
    type_str = "🖼 Static (WEBP)"
    if st.is_animated: type_str = "🎞 Animated (TGS)"
    elif st.is_video: type_str = "📹 Video (WEBM)"
    
    # 2. Pack Info & Buttons
    pack_info = "None"
    reply_markup = None
    
    if st.set_name:
        pack_info = f"[{st.set_name}](https://t.me/addstickers/{st.set_name})"
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("📂 View Sticker Pack", url=f"https://t.me/addstickers/{st.set_name}")]
        ])

    # 3. Construct Message
    text = (
        f"**🔍 STICKER DETAILS**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📛 **Pack:** {pack_info}\n"
        f"😀 **Emoji:** {st.emoji}\n"
        f"⚙️ **Type:** {type_str}\n"
        f"📏 **Size:** `{st.width}x{st.height}`\n\n"
        f"🆔 **File ID:**\n`{st.file_id}`\n\n"
        f"🧩 **Unique ID:**\n`{st.file_unique_id}`"
    )
    
    await reply_target.reply_text(
        text, 
        reply_markup=reply_markup, 
        disable_web_page_preview=True,
        quote=True
            )
