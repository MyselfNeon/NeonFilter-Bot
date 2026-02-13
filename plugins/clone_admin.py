# -------------------------------------------------------------------------------------
# 🎮 CLONE ADMIN COMMANDS (Owner Only)
#
# 1. /clonestats
#    - Shows the total number of clone bots currently in your database.
#    - Useful for a quick check of your bot's growth.
#
# 2. /listclones
#    - Generates a full list of all clone bots with their Owner IDs and masked tokens.
#    - If the list is too long, it sends a text file instead of a message.
#
# 3. /chkclone [user_id]
#    - Checks if a specific user has created a clone bot.
#    - Returns the Bot Token if found.
#
# 4. /delclone [user_id]
#    - Forcefully deletes a specific user's clone bot from the database.
#    - Use this to ban/remove abusive clones.
#
# -------------------------------------------------------------------------------------

import os
import datetime
from pyrogram import Client, filters
from database.users_chats_db import db
from info import ADMINS

@Client.on_message(filters.command("clonestats") & filters.user(ADMINS))
async def clone_stats(client, message):
    """
    Get an overview of the clone bot system.
    """
    msg = await message.reply("<b>🔄 Fetching Clone Stats...</b>")
    
    # Fetch all bots from DB
    bots_cursor = await db.get_all_bots()
    bots = await bots_cursor.to_list(length=None)
    
    total_clones = len(bots)
    now = datetime.datetime.now().strftime("%d/%m/%y")
    
    text = (
        f"**⌬ 📊 #CloneStats**\n"
        f"**┟ Total Clones: __{total_clones}__**\n"
        f"**┖ Last Updated: __{now}__**"
    )
    
    await msg.edit(text)


@Client.on_message(filters.command("listclones") & filters.user(ADMINS))
async def list_clones(client, message):
    """
    List all created clone bots. Returns a text file if the list is long.
    """
    msg = await message.reply("<b><i>🔄 Fetching Clone List...</i></b>")
    
    bots_cursor = await db.get_all_bots()
    bots = await bots_cursor.to_list(length=None)
    
    if not bots:
        return await msg.edit("<b><i>⚠️ No clone bots found.</i></b>")
    
    output_list = []
    for i, bot in enumerate(bots, 1):
        owner_id = bot.get('user_id', 'Unknown')
        token = bot.get('bot_token', 'Unknown')
        
        # Masking token (showing first 15 chars)
        masked_token = f"{token[:15]}..." if len(token) > 15 else token
        
        output_list.append(f"{i}. Owner: {owner_id} | Token: {masked_token}")
    
    # If list is short (10 or less), send as text
    if len(output_list) <= 10:
        text = "**⌬ 📃 #CloneList**\n┟ " + "\n**┟ **".join(output_list) + "\n**┖ End of List**"
        await msg.edit(text)
    else:
        # If list is long, save to file
        with open("clones_list.txt", "w") as f:
            f.write("\n".join(output_list))
        
        await msg.delete()
        await message.reply_document(
            document="clones_list.txt",
            caption=f"**⌬ 📃 #CloneList**\n**┟ Total Clones: {len(bots)}**\n**┖ Check file for details.**"
        )
        os.remove("clones_list.txt")


@Client.on_message(filters.command("chkclone") & filters.user(ADMINS))
async def check_clone(client, message):
    """
    Check if a specific user has a clone bot.
    Usage: /chkclone [user_id]
    """
    if len(message.command) < 2:
        return await message.reply("<b>⚠️ Usage:</b> <code>/chkclone [user_id]</code>")
    
    try:
        target_user_id = int(message.command[1])
    except ValueError:
        return await message.reply("<b>⚠️ Invalid User ID.</b>")
    
    msg = await message.reply("<b>🔍 Searching Database...</b>")
    
    # Fetch all bots to find the specific user
    bots_cursor = await db.get_all_bots()
    bots = await bots_cursor.to_list(length=None)
    
    target_bot = None
    for bot in bots:
        if bot.get('user_id') == target_user_id:
            target_bot = bot
            break
            
    if target_bot:
        token = target_bot.get('bot_token', 'Unknown')
        # Try to extract bot ID from token (digits before colon)
        bot_id = token.split(':')[0] if ':' in token else "Unknown"
        
        await msg.edit(
            f"**⌬ 🔎 #CloneDetails**\n"
            f"**┟ Owner ID:** <code>{target_user_id}</code>\n"
            f"**┟ Bot ID:** <code>{bot_id}</code>\n"
            f"**┖ Token:** <code>{token}</code>"
        )
    else:
        await msg.edit(f"**⌬ ❌ #NotFound**\n**┖ No clone found for User ID:** <code>{target_user_id}</code>")


@Client.on_message(filters.command("delclone") & filters.user(ADMINS))
async def force_delete_clone(client, message):
    """
    Force delete a clone bot by Admin.
    Usage: /delclone [user_id]
    """
    if len(message.command) < 2:
        return await message.reply("<b>⚠️ Usage:</b> <code>/delclone [user_id]</code>")
    
    try:
        target_user_id = int(message.command[1])
    except ValueError:
        return await message.reply("<b>⚠️ Invalid User ID.</b>")
        
    if not await db.is_clone_exist(target_user_id):
        return await message.reply(f"⌬ ❌ #NotFound\n┖ No clone found for User ID: <code>{target_user_id}</code>")
        
    await db.delete_clone(target_user_id)
    
    await message.reply(
        f"**⌬ 🗑 #CloneDeleted**\n"
        f"**┟ User ID:** <code>{target_user_id}</code>\n"
        f"**┖ Status: Removed from DB**"
    )