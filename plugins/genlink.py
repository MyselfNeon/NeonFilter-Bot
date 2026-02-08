import re
import os
import json
import base64
import logging
import asyncio
from utils import temp
from pyrogram import filters, Client, enums
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid, UsernameInvalid, UsernameNotModified
from info import ADMINS, LOG_CHANNEL, DUMP_CHANNEL, FILE_STORE_CHANNEL, PUBLIC_FILE_STORE
from database.ia_filterdb import unpack_new_file_id

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def allowed(_, __, message):
    if PUBLIC_FILE_STORE:
        return True
    if message.from_user and message.from_user.id in ADMINS:
        return True
    return False

@Client.on_message(filters.command(['link', 'plink']) & filters.create(allowed))
async def gen_link_s(bot, message):
    # --- 1. Interface: Reply or Interactive ---
    if message.reply_to_message and message.reply_to_message.media:
        neo = message.reply_to_message
        status_msg = await message.reply("⚡ **Processing...**")
    else:
        try:
            ask_msg = await bot.ask(
                chat_id=message.from_user.id,
                text="**📂 Send me the file you want to store.**",
                timeout=300
            )
            neo = ask_msg
            status_msg = await neo.reply("⚡ **Processing...**")
        except asyncio.TimeoutError:
            return await message.reply("❌ **Timeout!**")
        except Exception as e:
            return await message.reply(f"❌ **Error:** {e}")

    # --- 2. Validation ---
    file_type = neo.media
    if file_type not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.AUDIO, enums.MessageMediaType.DOCUMENT]:
        return await status_msg.edit("❌ **Invalid Media!**")

    if neo.has_protected_content:
        return await status_msg.edit("🔒 **Restricted Content!**\nI cannot copy files from restricted channels.")

    # --- 3. AUTO-LOG: Save to Dump Channel First ---
    try:
        # We COPY the message to the Dump Channel. This effectively "Saves" it.
        log_msg = await neo.copy(DUMP_CHANNEL)
    except Exception as e:
        return await status_msg.edit(f"❌ **Save Failed:** Could not copy to Dump Channel.\n`{e}`")

    # --- 4. Generate Link (Using Database ID) ---
    try:
        # We use the ID from the SAVED message in Dump Channel
        # CRITICAL FIX: *ignore prevents the "too many values" crash
        file_id, ref, *ignore = unpack_new_file_id(getattr(log_msg, file_type.value).file_id)
        
        prefix = 'filep_' if message.text.lower().strip() == "/plink" else 'file_'
        string = f"{prefix}{file_id}"
        
        outstr = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")
        
        bot_username = temp.U_NAME if hasattr(temp, 'U_NAME') else (await bot.get_me()).username
        link = f"https://t.me/{bot_username}?start={outstr}"

        await status_msg.edit(
            f"✅ **Link Generated!**\n\n"
            f"📂 **Archived to Logs:** Yes\n"
            f"🔗 **Link:** {link}"
        )
        
    except Exception as e:
        logger.error(f"Genlink Error: {e}")
        await status_msg.edit(f"⚠️ **Error:** `{e}`")


@Client.on_message(filters.command(['batch', 'pbatch']) & filters.create(allowed))
async def gen_link_batch(bot, message):
    # --- 1. Input Check ---
    if " " not in message.text or len(message.text.strip().split(" ")) != 3:
        return await message.reply("⚠️ **Usage:** `/batch link1 link2`")

    cmd, first, last = message.text.strip().split(" ")
    regex = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")

    match_f = regex.match(first)
    match_l = regex.match(last)

    if not match_f or not match_l:
        return await message.reply('❌ **Invalid Links**')

    f_chat_id = int("-100" + match_f.group(4)) if match_f.group(4).isnumeric() else match_f.group(4)
    f_msg_id = int(match_f.group(5))
    l_chat_id = int("-100" + match_l.group(4)) if match_l.group(4).isnumeric() else match_l.group(4)
    l_msg_id = int(match_l.group(5))

    if f_chat_id != l_chat_id:
        return await message.reply("❌ **Channel Mismatch!**")

    status_msg = await message.reply("⏳ **Checking access...**")

    try:
        chat_id = (await bot.get_chat(f_chat_id)).id
    except Exception:
        return await status_msg.edit('❌ **Access Denied!** Make me Admin there.')

    # --- 2. DSTORE Mode (Internal) ---
    if chat_id in FILE_STORE_CHANNEL:
        string = f"{f_msg_id}_{l_msg_id}_{chat_id}_{cmd.lower().strip()}"
        b_64 = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")
        bot_username = temp.U_NAME if hasattr(temp, 'U_NAME') else (await bot.get_me()).username
        return await status_msg.edit(f"✅ **Fast Link:** https://t.me/{bot_username}?start=DSTORE-{b_64}")

    # --- 3. BATCH Mode (External) ---
    await status_msg.edit(f"⏳ **Scanning messages...**")
    outlist = []
    og_msg = 0

    async for msg in bot.iter_messages(f_chat_id, l_msg_id, f_msg_id):
        if msg.empty or msg.service or not msg.media: continue
        try:
            file_type = msg.media
            file_obj = getattr(msg, file_type.value)
            caption = getattr(msg, 'caption', '')
            if caption: caption = caption.html
            
            if file_obj:
                outlist.append({
                    "file_id": file_obj.file_id,
                    "caption": caption,
                    "title": getattr(file_obj, "file_name", "Unknown"),
                    "size": file_obj.file_size,
                    "protect": cmd.lower().strip() == "/pbatch",
                })
                og_msg += 1
        except: pass

    if not outlist:
        return await status_msg.edit("❌ **No files found.**")

    # --- 4. Save JSON and Get Database ID ---
    try:
        file_name = f"batchmode_{message.from_user.id}.json"
        with open(file_name, "w+") as out:
            json.dump(outlist, out)

        # Upload JSON to Dump Channel (Auto-Save)
        post = await bot.send_document(
            DUMP_CHANNEL,
            file_name,
            caption=f"**⚠️ Batch Data**\nUser: {message.from_user.mention}\nFiles: {og_msg}"
        )
        os.remove(file_name)

        # CRITICAL FIX: Use unpack_new_file_id with *ignore to prevent crashes
        # This converts the file ID to your database format
        file_id, ref, *ignore = unpack_new_file_id(post.document.file_id)
        
        bot_username = temp.U_NAME if hasattr(temp, 'U_NAME') else (await bot.get_me()).username
        
        # Link Format: BATCH-<ShortDatabaseID>
        await status_msg.edit(
            f"✅ **Batch Link Ready!**\n\n"
            f"📂 Files: `{og_msg}`\n"
            f"🔗 Link: https://t.me/{bot_username}?start=BATCH-{file_id}"
        )

    except Exception as e:
        logger.error(f"Batch Error: {e}")
        await status_msg.edit(f"❌ **Error:** `{e}`")