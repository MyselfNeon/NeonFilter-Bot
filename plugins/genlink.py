import json
import os
import base64
import uuid
from pyrogram import Client, filters
from info import ADMINS, PUBLIC_FILE_STORE
from utils import temp
from database.ia_filterdb import unpack_new_file_id

BATCH_STORAGE = "batch_links.json"
if os.path.exists(BATCH_STORAGE):
    with open(BATCH_STORAGE, "r") as f:
        BATCHES = json.load(f)
else:
    BATCHES = {}

def save_batches():
    with open(BATCH_STORAGE, "w") as f:
        json.dump(BATCHES, f)

async def allowed(_, __, message):
    if PUBLIC_FILE_STORE:
        return True
    if message.from_user and message.from_user.id in ADMINS:
        return True
    return False

# --------------------------
# Batch link generator
# --------------------------
@Client.on_message(filters.command(['batch', 'pbatch']) & filters.create(allowed))
async def gen_link_batch(bot: Client, message):
    await message.reply("**__Send me the first message of the batch.__**")
    first_msg = await bot.listen(message.chat.id)
    first_id = first_msg.text if first_msg.text else first_msg.message_id

    await message.reply("**__Now send me the last message of the batch.__**")
    last_msg = await bot.listen(message.chat.id)
    last_id = last_msg.text if last_msg.text else last_msg.message_id

    # Iterate and store messages
    f_msg_id = int(first_id)
    l_msg_id = int(last_id)
    chat_id = first_msg.chat.id
    outlist = []

    async for neo in bot.iter_messages(chat_id, l_msg_id, f_msg_id, reverse=True):
        if neo.empty or neo.service:
            continue
        file_obj = neo.document or neo.video or neo.audio
        if file_obj:
            caption = getattr(neo, 'caption', '')
            if caption:
                caption = caption.html if hasattr(caption, 'html') else str(caption)
            outlist.append({
                "file_id": unpack_new_file_id(file_obj.file_id)[0],
                "caption": caption,
                "title": getattr(file_obj, "file_name", ""),
                "size": file_obj.file_size
            })

    if not outlist:
        return await message.reply("**__No media found in this range.__**")

    token = str(uuid.uuid4())
    BATCHES[token] = {
        "files": outlist,
        "protect": message.text.lower().strip() == "/pbatch"
    }
    save_batches()

    await message.reply(f"Here is your batch link containing `{len(outlist)}` files:\nhttps://t.me/{temp.U_NAME}?start={token}")

# --------------------------
# Start handler for batch
# --------------------------
@Client.on_message(filters.command("start"))
async def start_handler(bot: Client, message):
    start_param = message.text.split(" ", 1)
    if len(start_param) < 2:
        return await message.reply("**__Welcome! Send a file link to get files.__**")
    token = start_param[1]

    if token in BATCHES:
        batch = BATCHES[token]
        for f in batch["files"]:
            await message.reply_document(f["file_id"], caption=f.get("caption", ""))
    else:
        await message.reply("**__No file found for this link.__**")
