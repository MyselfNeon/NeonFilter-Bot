# Group_Logger.py
from pyrogram import Client, filters
from info import LOG_CHANNEL  # your log channel ID

LOG_TEXT_G = """**#NewGroupInfo 👥**
**- __Name = {}__**
**- __Group Type = {}__**
**- __Link = {}__**
**- __Gʀᴏᴜᴘ ID__ =** <code>{}</code>
**- __Aᴅᴅᴇᴅ Bʏ - {}__**"""

@Client.on_message(filters.new_chat_members)
async def log_new_group(client, message):
    # Check if the bot itself was added
    for user in message.new_chat_members:
        if user.id == (await client.get_me()).id:
            chat = message.chat
            
            # Group name
            group_name = chat.title
            
            # Group type and link
            if chat.username:  # public group
                group_type = "Public"
                group_link = f"https://t.me/{chat.username}"
            else:  # private group
                group_type = "Private"
                group_link = "Private Group"
            
            # Who added the bot
            added_by = message.from_user.mention if message.from_user else "Unknown"

            # Send log to LOG_CHANNEL
            await client.send_message(
                LOG_CHANNEL,
                LOG_TEXT_G.format(
                    group_name,
                    group_type,
                    group_link,
                    chat.id,
                    added_by
                ),
                disable_web_page_preview=True
            )
          
