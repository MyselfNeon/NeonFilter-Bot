# restore_usernames.py
from pyrogram import Client, filters
from database.users_chats_db import db
from pyrogram.errors import PeerIdInvalid, FloodWait
import asyncio

ADMINS = [123456789]  # Replace with your actual admin IDs

@Client.on_message(filters.command("restore_usernames") & filters.user(ADMINS))
async def restore_usernames(client, message):
    msg = await message.reply("**__Starting username restoration for all users...__**")
    users_cursor = db.col.find({})
    updated_count = 0
    failed_count = 0

    async for user in users_cursor:
        user_id = user.get("id")
        try:
            tg_user = await client.get_users(user_id)
            username = tg_user.username or "None"
            await db.col.update_one({"id": user_id}, {"$set": {"username": username}})
            updated_count += 1
            await asyncio.sleep(0.1)  # small delay to avoid hitting rate limits
        except PeerIdInvalid:
            failed_count += 1
        except FloodWait as e:
            await asyncio.sleep(e.x)  # wait if Telegram asks us to slow down
        except Exception:
            failed_count += 1

    await msg.edit(f"✅ **Username restoration completed!**\n"
                   f"Updated: {updated_count}\n"
                   f"Failed: {failed_count}")
