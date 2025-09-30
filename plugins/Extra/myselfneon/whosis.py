# whois.py
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import RPCError  # updated import
from datetime import datetime

WHOIS_TXT = """<b>ᴡʜᴏɪꜱ ᴍᴏᴅᴜʟᴇ

ɴᴏᴛᴇ:- ɢɪᴠᴇ ᴀ ᴜꜱᴇʀ ᴅᴇᴛᴀɪʟꜱ
Usage:
/whois &lt;username or user_id&gt; - ɢɪᴠᴇ ᴀ ᴜꜱᴇʀ ꜰᴜʟʟ ᴅᴇᴛᴀɪʟꜱ 📑
Or reply to a user’s message with /whois
</b>"""

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

@Client.on_message(filters.command("whois"))
async def whois(client: Client, message: Message):
    target_user = None

    # Check if command is a reply
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    elif len(message.command) >= 2:
        query = message.command[1]
        try:
            if query.isdigit():
                target_user = await client.get_users(int(query))
            else:
                target_user = await client.get_users(query)
        except RPCError:  # handles "user not found" and other RPC errors
            return await message.reply_text("❌ User not found.")
        except Exception as e:
            return await message.reply_text(f"❌ Error: {e}")
    else:
        return await message.reply_text(WHOIS_TXT, parse_mode="html", quote=True)

    if not target_user:
        return await message.reply_text("❌ Could not fetch user information.")

    # Optional: group restrictions
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

    text = f"""
<b>👤 User Info</b>
ID: <code>{target_user.id}</code>
Name: {target_user.first_name or 'None'} {target_user.last_name or ''}
Username: @{target_user.username or 'None'}
DC ID: {target_user.dc_id}
Language Code: {target_user.language_code or 'None'}
Bio: {target_user.bio or 'None'}
Status: {format_status(target_user)}
Restrictions: {', '.join(restrictions) if restrictions else 'None'}
"""

    # Profile picture
    if target_user.photo:
        await message.reply_photo(photo=target_user.photo.big_file_id, caption=text, parse_mode="html")
    else:
        await message.reply_text(text, parse_mode="html", quote=True)
