import re
import os
import json
import base64
import logging
import tempfile
from pyrogram import filters, Client, enums
from pyrogram.errors import ChannelInvalid, UsernameInvalid, UsernameNotModified
from info import ADMINS, LOG_CHANNEL, FILE_STORE_CHANNEL, PUBLIC_FILE_STORE
from database.ia_filterdb import unpack_new_file_id
from utils import temp

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# --------------------------
# Helper: check allowed users
# --------------------------
async def allowed(_, __, message):
    if PUBLIC_FILE_STORE:
        return True
    if message.from_user and message.from_user.id in ADMINS:
        return True
    return False

# --------------------------
# Single file link
# --------------------------
@Client.on_message(filters.command(['link', 'plink']) & filters.create(allowed))
async def gen_link_s(bot, message):
    try:
        await message.reply("**__Now Send Me Your File (Video, Audio, Document) 😊__**")
        neo = await bot.listen(message.chat.id)  # using pyromod.listen

        # Get file object safely
        file_obj = None
        if neo.document:
            file_obj = neo.document
        elif neo.video:
            file_obj = neo.video
        elif neo.audio:
            file_obj = neo.audio
        else:
            return await neo.reply("**__Send only Video, Audio, or Document.__**")

        if getattr(neo, "has_protected_content", False) and neo.from_user.id not in ADMINS:
            return await neo.reply("**__Protected content cannot be stored.__**")

        file_id, _ = unpack_new_file_id(file_obj.file_id)
        prefix = 'filep_' if message.text.lower().strip() == "/plink" else 'file_'
        b64_string = base64.urlsafe_b64encode(f"{prefix}{file_id}".encode()).decode().strip("=")

        await message.reply(f"Here is your Link:\nhttps://t.me/{temp.U_NAME}?start={b64_string}")
    except Exception as e:
        logger.error(f"Error in gen_link_s: {e}")
        await message.reply(f"❌ Error: {e}")

# --------------------------
# Batch link
# --------------------------
@Client.on_message(filters.command(['batch', 'pbatch']) & filters.create(allowed))
async def gen_link_batch(bot, message):
    try:
        parts = message.text.strip().split(" ")
        if len(parts) != 3:
            return await message.reply("**__Use correct Format ✅\n\nExample__**\n<code>/batch https://t.me/NeonFiles/10 https://t.me/NeonFiles/20</code>")

        cmd, first, last = parts
        regex = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?([\w\d_]+)/(\d+)$")

        # Helper to parse link
        def parse_link(link):
            m = regex.match(link)
            if not m:
                return None, None
            chat_id = m.group(4)
            msg_id = int(m.group(5))
            if chat_id.isnumeric():
                chat_id = int("-100" + chat_id)
            return chat_id, msg_id

        f_chat_id, f_msg_id = parse_link(first)
        l_chat_id, l_msg_id = parse_link(last)

        if not f_chat_id or not l_chat_id:
            return await message.reply("**__Invalid link ❌__**")

        if f_chat_id != l_chat_id:
            return await message.reply("**__Chat IDs do not match.__**")

        # Verify channel access
        try:
            chat_id = (await bot.get_chat(f_chat_id)).id
        except ChannelInvalid:
            return await message.reply("**__Private Channel / group. Make me admin to index files.__**")
        except (UsernameInvalid, UsernameNotModified):
            return await message.reply("**__Invalid link.__**")
        except Exception as e:
            return await message.reply(f"❌ Error: {e}")

        sts = await message.reply("**__Generating Link. This may take some time...__**")

        if chat_id in FILE_STORE_CHANNEL:
            # For file store channels, just encode
            string = f"{f_msg_id}_{l_msg_id}_{chat_id}_{cmd.lower().strip()}"
            b64 = base64.urlsafe_b64encode(string.encode()).decode().strip("=")
            return await sts.edit(f"Here is your link: https://t.me/{temp.U_NAME}?start=DSTORE-{b64}")

        # Otherwise, iterate messages and store metadata
        outlist = []
        og_msg = 0

        async for neo in bot.iter_messages(chat_id, l_msg_id, f_msg_id, reverse=True):
            if neo.empty or neo.service:
                continue
            if not neo.media:
                continue

            file_obj = None
            if neo.document:
                file_obj = neo.document
            elif neo.video:
                file_obj = neo.video
            elif neo.audio:
                file_obj = neo.audio

            if file_obj:
                caption = getattr(neo, 'caption', '')
                if caption:
                    caption = caption.html if hasattr(caption, 'html') else str(caption)
                outlist.append({
                    "file_id": file_obj.file_id,
                    "caption": caption,
                    "title": getattr(file_obj, "file_name", ""),
                    "size": file_obj.file_size,
                    "protect": cmd.lower().strip() == "/pbatch"
                })
                og_msg += 1

        # Save temp JSON
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as out:
            json.dump(outlist, out)
            tmp_path = out.name

        post = await bot.send_document(LOG_CHANNEL, tmp_path, file_name="Batch.json", caption=f"⚠️Generated for filestore by {message.from_user.first_name}")
        os.remove(tmp_path)

        file_id, _ = unpack_new_file_id(post.document.file_id)
        await sts.edit(f"Here is your link\nContains `{og_msg}` files.\nhttps://t.me/{temp.U_NAME}?start=BATCH-{file_id}")

    except Exception as e:
        logger.error(f"Error in gen_link_batch: {e}")
        await message.reply(f"❌ Error: {e}")
        
