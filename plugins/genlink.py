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
    user_id = message.from_user.id
    
    # Send the prompt and wait for the user's response (file)
    prompt_msg = await message.reply("**__Now Send Me Your File (Video, Audio, Document, Photo, or Animation) Which You Want To Store.__**")

    try:
        # Use get_response to wait for the next message from the same user
        neo = await bot.get_response(
            chat_id=user_id,
            # Set a timeout in seconds (e.g., 60 seconds)
            timeout=60
        )
    except Exception as e:
        # If timeout or any other error occurs
        await prompt_msg.edit("**Timed out!** Please run the command again if you still want to generate a link.")
        return

    # Check for the file object robustly
    file_object = neo.document or neo.video or neo.audio or neo.photo or neo.animation

    if not file_object:
        # Check if they sent a text message instead of a file
        if neo.text:
            return await neo.reply("❌ **Invalid Input:** You sent a text message. Please send a file (Document, Video, Audio, Photo, or Animation).")
        else:
            # For stickers, animated emojis, etc.
            return await neo.reply("❌ **Invalid Input:** Please send a file (Document, Video, Audio, Photo, or Animation), not stickers or other unsupported media.")
    
    # Check for protected content (using the message where the file was sent)
    if neo.has_protected_content and message.chat.id not in ADMINS:
        return await neo.reply("okDa")
        
    # Get file_id from the detected file object
    try:
        file_id, ref = unpack_new_file_id(file_object.file_id)
    except Exception as e:
        logger.error(f"Error unpacking file ID: {e}")
        return await neo.reply("❌ **File Error:** Could not process the file ID for link generation.")
    
    # Generate the base64 encoded link
    string = 'filep_' if message.text.lower().strip() == "/plink" else 'file_'
    string += file_id
    outstr = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")
    
    # Reply with the generated link
    await message.reply(f"**__Here is Your Link :\n\nhttps://t.me/{temp.U_NAME}?start={outstr}__**")

# ---

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
        logger.exception(e) # Log the exception for debugging
        return await message.reply(f'**__Errors - {e}__**')

    sts = await message.reply(
        "**__Generating Link for Your Message.\nThis May take Time Depending Upon Number of Messages__**"
    )

    if chat_id in FILE_STORE_CHANNEL:
        string = f"{f_msg_id}_{l_msg_id}_{chat_id}_{cmd.lower().strip()}"
        b_64 = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")
        return await sts.edit(f"**__Here is Your Link 🖇️\n\nhttps://t.me/{temp.U_NAME}?start=DSTORE-{b_64}__**")

    FRMT = "**__Generating Link...\nTotal Messages: `{total}`\nDone: `{current}`\nRemaining: `{rem}`\nStatus: `{sts}`__**"

    outlist = []
    og_msg = 0
    tot = 0

    async for msg in bot.iter_messages(f_chat_id, l_msg_id, f_msg_id):
        tot += 1
        # Update status message occasionally to show progress (optional, but good practice)
        if tot % 20 == 0:
            try:
                await sts.edit(FRMT.format(total=(l_msg_id - f_msg_id + 1), current=tot, rem=(l_msg_id - f_msg_id + 1 - tot), sts="Processing..."))
            except:
                pass # Ignore FloodWait

        if msg.empty or msg.service:
            continue
        if not msg.media:
            continue  # only media messages supported
            
        try:
            # Get the file object using the same robust method as /link
            file_object = msg.document or msg.video or msg.audio or msg.photo or msg.animation
            
            if not file_object:
                continue # Skip if no storable file object is found

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
            pass # Continue to the next message even if one fails

    # Save the file list to a JSON file
    file_path = f"batchmode_{message.from_user.id}.json"
    with open(file_path, "w+") as out:
        json.dump(outlist, out, indent=4)

    # Upload the JSON file to the log channel
    post = await bot.send_document(
        LOG_CHANNEL,
        file_path,
        file_name="Batch.json",
        caption=f"**__⚠️ Generated for Filestore. Contains {og_msg} files.__**"
    )
    os.remove(file_path) # Clean up local file

    # Generate the final link
    file_id, ref = unpack_new_file_id(post.document.file_id)
    await sts.edit(
        f"**__Here is Your Link\nContains `{og_msg}` Files.\n https://t.me/{temp.U_NAME}?start=BATCH-{file_id}__**"
    )

# Dont remove Credits
# Developer Telegram @MyselfNeon
# Update channel - @NeonFiles

