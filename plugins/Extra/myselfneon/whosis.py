# ====================== PLUGINS/WHOIS.PY ======================
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import RPCError

# ====================== HELP TEXT ======================
WHOIS_TXT = """<blockquote>✨ **WHOIS HELP** ✨</blockquote>

**Usage:**
/whois `<username | user_id>` – Get full details of a user 📑  
Reply to a user’s message with /whois – Get their details

**Examples:**
`/whois neon`  
`/whois 123456789`

**🔥 Powered By @NeonFiles 🔥**
"""

# ====================== STATUS FORMATTER ======================
def format_status(user):
    status = []
    if user.is_bot:
        status.append("🤖 Bot")
    if user.is_verified:
        status.append("✅ Verified")
    if user.is_premium:
        status.append("💎 Premium")
    if user.is_scam:
        status.append("⚠️ Scam")
    return ", ".join(status) if status else "Normal"

# ====================== MAIN WHOIS ======================
@Client.on_message(filters.command("whois") & filters.private)
async def whois(client: Client, message: Message):
    target_user = None

    # Case 1: If replying
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user

    # Case 2: If argument given
    elif len(message.command) >= 2:
        query = message.command[1]
        try:
            if query.isdigit():
                target_user = await client.get_users(int(query))
            else:
                target_user = await client.get_users(query)
        except RPCError:
            return await message.reply("**❌ User Not Found.**\nUse `/whoishelp` for usage.")
        except Exception as e:
            return await message.reply(f"**❌ Error:** `{e}`")

    # Case 3: If no arguments
    else:
        return await message.reply(WHOIS_TXT)

    # If still None
    if not target_user:
        return await message.reply("**❌ Could Not Fetch User Information.**")

    # Restrictions (optional, group context)
    restrictions = []
    try:
        if message.chat.type in ["supergroup", "group"]:
            member = await client.get_chat_member(message.chat.id, target_user.id)
            if member.can_send_messages is False:
                restrictions.append("❌ Cannot send messages")
            if member.can_add_web_page_previews is False:
                restrictions.append("❌ Cannot add web previews")
            if member.can_send_media_messages is False:
                restrictions.append("❌ Cannot send media")
    except:
        pass

    # Info text
    text = f"""
<b>👤 User Info</b>
ID: <code>{target_user.id}</code>
Name: {target_user.first_name or 'None'} {target_user.last_name or ''}
Username: @{target_user.username or 'None'}
DC ID: {getattr(target_user, 'dc_id', 'N/A')}
Language Code: {getattr(target_user, 'language_code', 'None')}
Bio: {target_user.about or 'None'}
Status: {format_status(target_user)}
Restrictions: {', '.join(restrictions) if restrictions else 'None'}
"""

    # Reply with photo if exists
    if target_user.photo:
        await message.reply_photo(photo=target_user.photo.big_file_id, caption=text)
    else:
        await message.reply(text)

# ====================== WHOIS HELP COMMAND ======================
@Client.on_message(filters.command("whoishelp") & filters.private)
async def whoishelp(_, message: Message):
    await message.reply(WHOIS_TXT)
