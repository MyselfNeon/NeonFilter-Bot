# genlink.py
import re
import os
import json
import base64
import logging
from utils import temp
from pyrogram import filters, Client, enums
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid, UsernameInvalid, UsernameNotModified
from info import ADMINS, LOG_CHANNEL, FILE_STORE_CHANNEL, PUBLIC_FILE_STORE
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
    """Generates a direct link from a single message link provided in the command."""
    
    # 1. Check for link argument
    if " " not in message.text:
        return await message.reply(
            "**__Use Correct Format.\n\nExample <code>/link https://t.me/NeonFiles/5428</code>__**"
        )
    
    links = message.text.strip().split(" ")
    if len(links) != 2:
        return await message.reply(
            "**__Use Correct Format.\n\nExample <code>/link https://t.me/NeonFiles/5428</code>__**"
        )

    cmd, file_link = links
    
    # 2. Extract chat ID and message ID using Regex
    regex = re.compile(
        "(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$"
    )

    match = regex.match(file_link)
    if not match:
        return await message.reply('**❌ __Invalid Link Specified__**')
        
    chat_id_str = match.group(4)
    msg_id = int(match.group(5))
    
    if chat_id_str.isnumeric():
        f_chat_id = int("-100" + chat_id_str)
    else:
        f_chat_id = chat_id_str # Use username if it's not a numeric channel ID
        
    # 3. Get the message object
    try:
        msg = await bot.get_messages(f_chat_id, msg_id)
    except Exception as e:
        logger.error(f"Error fetching message for single link: {e}")
        return await message.reply(f'**__Error: Could not access the message. Check if the bot is an admin in the channel/group.__**\n\nDetails: `{e}`')

    # 4. Check for media
    file_object = msg.document or msg.video or msg.audio or msg.photo or msg.animation
    
    if not file_object:
        return await message.reply("❌ **Invalid Message:** The linked message does not contain a supported file (document, video, audio, photo, or animation).")

    # 5. Check protected content (optional, added for completeness)
    if msg.has_protected_content and message.chat.id not in ADMINS:
        return await message.reply("okDa")
        
    # 6. Generate the final link
    file_id, ref = unpack_new_file_id(file_object.file_id)
    
    string = 'filep_' if cmd.lower().strip() == "/plink" else 'file_'
    string += file_id
    outstr = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")
    
    await message.reply(f"**__Here is Your Link :\n\nhttps://t.me/{temp.U_NAME}?start={outstr}__**")


@Client.on_message(filters.command(['batch', 'pbatch']) & filters.create(allowed))
async def gen_link_batch(bot, message):
    if " " not in message.text:
        return await message.reply(
            "**__Use Correct Format.\n\nExample <code>/batch https://t.me/NeonFiles/01 https://t.me/NeonFiles/20</code>__**"
        )

    links = message.text.strip().split(" ")
    if len(links) != 3:
        return await message.reply(
            "**__Use Correct Format.\n\nExample <code>/batch https://t.me/NeonFiles/01 https://t.me/NeonFiles/20</code>__**"
        )

    cmd, first, last = links
    regex = re.compile(
        "(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$"
    )

    match = regex.match(first)
    if not match:
        return await message.reply('**❌ __Invalid Link__**')
    f_chat_id = match.group(4)
    f_msg_id = int(match.group(5))
    if f_chat_id.isnumeric():
        f_chat_id = int("-100" + f_chat_id)

    match = regex.match(last)
    if not match:
        return await message.reply('**❌ __Invalid Link__**')
    l_chat_id = match.group(4)
    l_msg_id = int(match.group(5))
    if l_chat_id.isnumeric():
        l_chat_id = int("-100" + l_chat_id)

    if f_chat_id != l_chat_id:
        return await message.reply("**__Chat IDs Not Matched__**")

    try:
        chat_id = (await bot.get_chat(f_chat_id)).id
    except ChannelInvalid:
        return await message.reply(
            '**__This may be a Private Channel / Group. Make me an Admin Over There to Index the Files.__**'
        )
    except (UsernameInvalid, UsernameNotModified):
        return await message.reply('**__Invalid Link Specified__**')
    except Exception as e:
        logger.exception(e)
        return await message.reply(f'**__Errors - {e}__**')

    sts = await message.reply(
        "**__Generating Link for Your Message.\nThis May take Time Depending Upon Number of Messages__**"
    )
    
    # Existing logic for handling FILE_STORE_CHANNEL for large batches
    if chat_id in FILE_STORE_CHANNEL:
        string = f"{f_msg_id}_{l_msg_id}_{chat_id}_{cmd.lower().strip()}"
        b_64 = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")
        return await sts.edit(f"**__Here is Your Link 🖇️\n\nhttps://t.me/{temp.U_NAME}?start=DSTORE-{b_64}__**")

    FRMT = "**__Generating Link...\nTotal Messages: `{total}`\nDone: `{current}`\nRemaining: `{rem}`\nStatus: `{sts}`__**"

    outlist = []
    og_msg = 0
    tot = 0
    total_messages = l_msg_id - f_msg_id + 1

    async for msg in bot.iter_messages(f_chat_id, l_msg_id, f_msg_id):
        tot += 1
        # Update status message occasionally
        if tot % 20 == 0:
            try:
                await sts.edit(FRMT.format(total=total_messages, current=tot, rem=total_messages - tot, sts="Processing..."))
            except:
                pass 

        if msg.empty or msg.service:
            continue
        if not msg.media:
            continue
            
        try:
            # Use robust file object detection
            file_object = msg.document or msg.video or msg.audio or msg.photo or msg.animation
            
            if not file_object:
                continue

            caption = getattr(msg, 'caption', '')
            if caption:
                caption = caption.html
            
            file = {
                "file_id": file_object.file_id,
                "caption": caption,
                "title": getattr(file_object, "file_name", ""),
                "size": file_object.file_size,
                "protect": cmd.lower().strip() == "/pbatch",
            }
            og_msg += 1
            outlist.append(file)
            
        except Exception as e:
            logger.error(f"Error processing message {msg.id} in chat {f_chat_id}: {e}")
            pass

    file_path = f"batchmode_{message.from_user.id}.json"
    with open(file_path, "w+") as out:
        json.dump(outlist, out, indent=4)

    post = await bot.send_document(
        LOG_CHANNEL,
        file_path,
        file_name="Batch.json",
        caption=f"**__⚠️ Generated for Filestore. Contains {og_msg} files.__**"
    )
    os.remove(file_path)

    file_id, ref = unpack_new_file_id(post.document.file_id)
    await sts.edit(
        f"**__Here is Your Link\nContains `{og_msg}` Files.\n https://t.me/{temp.U_NAME}?start=BATCH-{file_id}__**"
    )


# Dont remove Credits
# Developer Telegram @MyselfNeon
# Update channel - @NeonFiles
