# plugins/react_command.py
from pyrogram import Client, filters
import re
import random

# 👑 Only allow specific users (replace with your Telegram ID)
ALLOWED_USERS = [841851780]  # <-- your ID here

@Client.on_message(filters.command("react") & filters.user(ALLOWED_USERS))
async def react_command(client, message):
    """
    Usage:
    /react <post_link> <count> <emojis>

    Example:
    /react https://t.me/yy_channel/123 10 ❤️
    /react https://t.me/yy_channel/123 10 😎❤️🔥
    """
    try:
        # --- Parse user input ---
        parts = message.text.split(" ", 3)
        if len(parts) < 4:
            return await message.reply_text(
                "❌ **Usage:**\n"
                "`/react <post_link> <count> <emojis>`\n\n"
                "**Example:** `/react https://t.me/yy_channel/123 10 😎❤️🔥`"
            )

        post_link = parts[1]
        count = int(parts[2])
        emojis_str = parts[3].strip()

        # --- Extract emojis safely ---
        # Split each Unicode character manually (emoji-safe)
        emojis = [e for e in emojis_str if not e.isspace()]
        if not emojis:
            return await message.reply_text("⚠️ No valid emojis found!")

        # --- Extract chat username and message ID ---
        match = re.search(r"t\.me/([^/]+)/(\d+)", post_link)
        if not match:
            return await message.reply_text("⚠️ Invalid post link format!")

        chat_username = match.group(1)
        message_id = int(match.group(2))

        # --- Check if bot has access ---
        try:
            await client.get_chat(chat_username)
        except Exception:
            return await message.reply_text(
                f"⚠️ I can’t access @{chat_username}.\n"
                f"➡️ Add me as a **member or admin** in that channel first."
            )

        # --- Build reaction list ---
        if len(emojis) == 1:
            reaction_list = [emojis[0]] * count
        else:
            reaction_list = [random.choice(emojis) for _ in range(count)]

        # --- Send reactions ---
        await client.set_message_reaction(
            chat_id=f"@{chat_username}",
            message_id=message_id,
            reaction=reaction_list
        )

        # --- Clean up ---
        await message.delete()

        # --- Confirmation message ---
        await client.send_message(
            message.chat.id,
            f"✅ **Added {count} reactions** to "
            f"[this post](https://t.me/{chat_username}/{message_id}) 🎉\n"
            f"Used emojis: {' '.join(reaction_list)}",
            disable_web_page_preview=True
        )

    except Exception as e:
        await message.reply_text(f"❌ **Error:** `{e}`")
