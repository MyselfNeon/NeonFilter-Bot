from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import PeerIdInvalid

# 🟢 Whois Command
@Client.on_message(filters.command("whois"))
async def whois(client: Client, message: Message):
    try:
        # Case: Only /whois → show error/help
        if len(message.command) == 1 and not message.reply_to_message:
            return await message.reply_text(
                "❌ Wrong usage!\n\nUse:\n"
                "`/whois <username | user_id>` or reply to a user.\n\n"
                "For details: `/whoishelp`"
            )

        # Determine target user
        if message.reply_to_message:  
            target_user = message.reply_to_message.from_user
        else:
            query = message.command[1]
            try:
                target_user = await client.get_users(query)
            except PeerIdInvalid:
                return await message.reply_text("❌ Invalid user. Please give a valid username or ID.")

        # Fetch full chat info (to access bio)
        target = await client.get_chat(target_user.id)

        # Build info string
        userinfo = f"""
👤 **Name:** {target.first_name or ''} {target.last_name or ''}
🔗 **Username:** @{target.username or 'None'}
🆔 **ID:** {target.id}
🌐 **Language:** {getattr(target_user, 'language_code', 'Unknown')}
🤖 **Is Bot:** {target.is_bot}
📌 **Bio:** {target.bio or 'None'}
"""

        await message.reply_text(userinfo, disable_web_page_preview=True)

    except Exception as e:
        await message.reply_text(f"⚠️ Error: `{e}`")

# 🟢 Whois Help Command
@Client.on_message(filters.command("whoishelp"))
async def whois_help(client: Client, message: Message):
    text = """
**🆘 Whois Help**

Use this command to get information about a user.

**Usage:**
- `/whois <username>` → Get info by username.
- `/whois <user_id>` → Get info by ID.
- Reply to a user with `/whois` → Get info directly.

**Example:**
- `/whois neon`
- `/whois 123456789`
"""
    await message.reply_text(text)
