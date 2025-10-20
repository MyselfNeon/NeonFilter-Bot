# ====================== PLUGINS/WHOIS.PY ======================
from pyrogram import Client, filters
from pyrogram.types import Message
from datetime import datetime

WHOIS_TXT = """<b><i>🕵️ Whois Module</i></b>

**__Use to Get Telegram User Details.__**

<b><i>Usage :</b>
• /whois @username
• /whois user_id
• Reply to a Message with /whois</i>
"""

# ====================== MAIN HANDLER ======================
@Client.on_message(filters.command("whois") & filters.private)
async def whois_user(client: Client, message: Message):
    try:
        # determine target
        if message.reply_to_message:
            user = message.reply_to_message.from_user
        elif len(message.command) > 1:
            target = message.command[1]
            if target.startswith("@"):
                user = await client.get_users(target)
            else:
                try:
                    user_id = int(target)
                    user = await client.get_users(user_id)
                except ValueError:
                    return await message.reply("**__❌ Invalid user ID or Username !__**", quote=True)
        else:
            return await message.reply(WHOIS_TXT, quote=True)

        # ====================== BUILD USER INFO ======================
        text = f"<b><i>👤 USER INFO</i></b>\n\n"
        text += f"<b><i>🆔 User ID :</b> <code>{user.id}</code>\n"
        text += f"📛 <b><i>Name :</b> {user.first_name or 'N/A'}</i>"
        if user.last_name:
            text += f"<i> {user.last_name}</i>\n"
        else:
            text += "\n"

        if user.username:
            text += f"🖇️ <b><i>Username :</b> @{user.username}</i>\n"
        else:
            text += "🖇️ <b><i>Username :</b> None\n"

        text += f"🧾 <b><i>DC ID :</b> {user.dc_id or 'Unknown'}\n"
        text += f"🤖 <b><i>Is Bo. :</b> {'Yes' if user.is_bot else 'No'}</i>\n"
        text += f"✅ <b><i>Is Verified :</b> {'Yes' if user.is_verified else 'No'}</i>\n"
        text += f"🚫 <b><i>Is Scam :</b> {'Yes' if user.is_scam else 'No'}</i>\n"
        text += f"📵 <b><i>Is Fake :</b> {'Yes' if user.is_fake else 'No'}</i>\n"

        # premium check
        text += f"💎 <b><i>Is Premium:</b> {'Yes' if getattr(user, 'is_premium', False) else 'No'}</i>\n"

        # language, if available
        if getattr(user, "language_code", None):
            text += f"🌐 <b><i>Language :</b> {user.language_code.upper()}</i>\n"

        # status line
        if getattr(user, "status", None):
            text += f"🕓 <b><i>Status :</b> {user.status}</i>\n"

        # bio if retrievable
        try:
            full = await client.get_chat(user.id)
            if getattr(full, "bio", None):
                text += f"\n💬 <b><i>Bio :</b>\n{full.bio}</i>"
        except Exception:
            pass

        # last seen formatting
        if getattr(user, "last_online_date", None):
            time_ago = datetime.fromtimestamp(user.last_online_date)
            text += f"\n🕰️ <b><i>Last Online :</b> {time_ago.strftime('%Y-%m-%d %H:%M:%S')}</i>"

        # profile photo (if available)
        if user.photo:
            photo = await client.download_media(user.photo.big_file_id)
            await message.reply_photo(photo, caption=text, quote=True)
        else:
            await message.reply(text, quote=True)

    except Exception as e:
        await message.reply(f"**⚠️ __Error :__**\n<blockquote>`{e}`</blockquote>\n\n**__Might be an Invalid Username or Restricted Account 🙄🚫__**", quote=True)

# ====================== HELP COMMAND ======================
@Client.on_message(filters.command("whoishelp") & filters.private)
async def whois_help(client: Client, message: Message):
    await message.reply(WHOIS_TXT, quote=True)
