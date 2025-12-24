# ---------------------------------------------------
# File Name: Approve.py
# Author: MyselfNeon
# Original Repo: https://github.com/MyselfNeon/NeonFilter-Bot
# GitHub: https://github.com/MyselfNeon/
# Telegram: https://t.me/MyelfNeon
# ---------------------------------------------------

import os
import json
import base64
import random
import asyncio
import logging
import datetime
from urllib.parse import quote_plus

from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ChatJoinRequest, Message, WebAppInfo

from Script import script
from info import *
from utils import get_settings, get_size, verify_user, check_token, check_verification, get_token, get_shortlink, get_tutorial, get_seconds
from database.ia_filterdb import get_file_details
from database.users_chats_db import db, delete_all_referal_users, get_referal_users_count, referal_add_user
from database.join_reqs import JoinReqs
from Neon.util.file_properties import get_name, get_hash

# --- Logger & Globals ---
logger = logging.getLogger(__name__)
BATCH_FILES = {}
join_db = JoinReqs

# --- Chat Join Request Handler ---
@Client.on_chat_join_request((filters.group | filters.channel))
async def auto_approve(client: Client, message: ChatJoinRequest):
    chat = message.chat 
    user = message.from_user 

    # 1. Auto Approve Logic
    if AUTO_APPROVE_MODE:
        if not await db.is_user_exist(user.id):
            await db.add_user(user.id, user.first_name)
        
        if chat.id == AUTH_CHANNEL:
            return 
            
        await client.approve_chat_join_request(chat_id=chat.id, user_id=user.id)
        
        text = f"<b>Hᴇʟʟᴏ {user.mention} 👋,\n\nYᴏᴜʀ Rᴇǫᴜᴇsᴛ Tᴏ Jᴏɪɴ {chat.title} Is Aᴘᴘʀᴏᴠᴇᴅ.\n\nPᴏᴡᴇʀᴇᴅ Bʏ - {CHNL_LNK}</b>"
        await client.send_message(chat_id=user.id, text=text)
         
    # 2. Request To Join / Database Logic
    if not REQUEST_TO_JOIN_MODE:
        return 
    if chat.id != AUTH_CHANNEL:
        return 
    if not join_db().isActive():
        return

    await join_db().add_user(
        user_id=user.id, 
        first_name=user.first_name, 
        username=user.username, 
        date=message.date
    )

# --- Start Command Handler ---
@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    # 1. Check for arguments or stored commands
    if len(message.command) > 1:
        data = message.command[1]
    elif TRY_AGAIN_BTN is False:
        # Fallback to DB if enabled
        data = await db.get_msg_command(message.from_user.id)
        # FIX: Ensure data is a string if DB returns None
        if data is None:
            data = "None"
    else:
        data = "None"

    # 2. Referral Logic
    if data.split("-", 1)[0] == "NEO":
        user_id = int(data.split("-", 1)[1])
        neo = await referal_add_user(user_id, message.from_user.id)
        
        if neo and PREMIUM_AND_REFERAL_MODE:
            await message.reply(f"<b>You have joined using the referral link of user with ID {user_id}\n\nSend /start again to use the bot</b>")
            num_referrals = await get_referal_users_count(user_id)
            await client.send_message(chat_id=user_id, text="<b>{} start the bot with your referral link\n\nTotal Referals - {}</b>".format(message.from_user.mention, num_referrals))
            
            if num_referrals == REFERAL_COUNT:
                time_limit = REFERAL_PREMEIUM_TIME       
                seconds = await get_seconds(time_limit)
                if seconds > 0:
                    expiry_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
                    user_data = {"id": user_id, "expiry_time": expiry_time} 
                    await db.update_user(user_data)
                    await delete_all_referal_users(user_id)
                    await client.send_message(chat_id=user_id, text="<b>You Have Successfully Completed Total Referal.\n\nYou Added In Premium For {}</b>".format(REFERAL_PREMEIUM_TIME))
                    return 
        else:
            # Main Start Message (No params or Referral)
            buttons = [
                [InlineKeyboardButton('⤬ Aᴅᴅ Mᴇ Tᴏ Yᴏᴜʀ Gʀᴏᴜᴘ ⤬', url=f'http://t.me/{temp.U_NAME}?startgroup=true')],
                [InlineKeyboardButton('Eᴀʀɴ Mᴏɴᴇʏ', callback_data="shortlink_info"), InlineKeyboardButton('Mᴏᴠɪᴇ Gʀᴏᴜᴘ', url=GRP_LNK)],
                [InlineKeyboardButton('Hᴇʟᴘ', callback_data='help'), InlineKeyboardButton('Aʙᴏᴜᴛ', callback_data='about')],
                [InlineKeyboardButton('Jᴏɪɴ Uᴘᴅᴀᴛᴇ Cʜᴀɴɴᴇʟ', url=CHNL_LNK)]
            ]
            
            if PREMIUM_AND_REFERAL_MODE:
                buttons.insert(3, [InlineKeyboardButton('Pʀᴇᴍɪᴜᴍ Aɴᴅ Rᴇғᴇʀʀᴀʟ', callback_data='subscription')])
            
            if CLONE_MODE:
                buttons.append([InlineKeyboardButton('Cʀᴇᴀᴛᴇ Oᴡɴ Cʟᴏɴᴇ Bᴏᴛ', callback_data='clone')])
            
            reply_markup = InlineKeyboardMarkup(buttons)
            m = await message.reply_sticker("CAACAgUAAxkBAAEKVaxlCWGs1Ri6ti45xliLiUeweCnu4AACBAADwSQxMYnlHW4Ls8gQMAQ") 
            await asyncio.sleep(1)
            await m.delete()
            await message.reply_photo(
                photo=random.choice(PICS),
                caption=script.START_TXT.format(message.from_user.mention, temp.U_NAME, temp.B_NAME),
                reply_markup=reply_markup,
                parse_mode=enums.ParseMode.HTML
            )
            return 

    # 3. File Processing Logic
    try:
        pre, file_id = data.split('_', 1)
    except:
        file_id = data
        pre = ""
        
    # --- BATCH FILES ---
    if data.split("-", 1)[0] == "BATCH":
        sts = await message.reply("<b>Pʟᴇᴀsᴇ Wᴀɪᴛ...</b>")
        file_id = data.split("-", 1)[1]
        msgs = BATCH_FILES.get(file_id)
        
        if not msgs:
            file = await client.download_media(file_id)
            try: 
                with open(file) as file_data:
                    msgs = json.loads(file_data.read())
            except:
                await sts.edit("FAILED")
                return await client.send_message(LOG_CHANNEL, "UNABLE TO OPEN FILE.")
            os.remove(file)
            BATCH_FILES[file_id] = msgs

        filesarr = []
        for msg in msgs:
            title = msg.get("title")
            size = get_size(int(msg.get("size", 0)))
            f_caption = msg.get("caption", "")
            if BATCH_FILE_CAPTION:
                try:
                    f_caption = BATCH_FILE_CAPTION.format(file_name='' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)
                except:
                    pass
            if f_caption is None:
                f_caption = f"{title}"
            
            try:
                reply_markup = None
                if STREAM_MODE:
                    log_msg = await client.send_cached_media(chat_id=LOG_CHANNEL, file_id=msg.get("file_id"))
                    stream_link = f"{URL}watch/{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"
                    download_link = f"{URL}{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"
                    
                    reply_markup = InlineKeyboardMarkup([
                        [InlineKeyboardButton("• Dᴏᴡɴʟᴏᴀᴅ •", url=download_link), InlineKeyboardButton('• Wᴀᴛᴄʜ •', url=stream_link)],
                        [InlineKeyboardButton("• Wᴀᴛᴄʜ Iɴ Wᴇʙ Aᴘᴘ •", web_app=WebAppInfo(url=stream_link))]
                    ])
                    
                msg = await client.send_cached_media(
                    chat_id=message.from_user.id,
                    file_id=msg.get("file_id"),
                    caption=f_caption,
                    protect_content=msg.get('protect', False),
                    reply_markup=reply_markup
                )
                filesarr.append(msg)
                
            except FloodWait as e:
                await asyncio.sleep(e.value)
                # Retry once
                msg = await client.send_cached_media(
                    chat_id=message.from_user.id,
                    file_id=msg.get("file_id"),
                    caption=f_caption,
                    protect_content=msg.get('protect', False),
                    reply_markup=reply_markup
                )
                filesarr.append(msg)
            except:
                continue
            await asyncio.sleep(1) 
        
        await sts.delete()
        k = await client.send_message(chat_id=message.from_user.id, text=f"<blockquote><b><u>❗️❗️❗️IMPORTANT❗️️❗️❗️</u></b>\n\nTʜɪs Mᴇssᴀɢᴇ Wɪʟʟ Bᴇ Dᴇʟᴇᴛᴇᴅ Iɴ <b><u>10 mins</u> 🫥 <i></b>(Dᴜᴇ Tᴏ Cᴏᴘʏʀɪɢʜᴛ Issᴜᴇs)</i>.\n\n<b><i>Pʟᴇᴀsᴇ Fᴏʀᴡᴀʀᴅ Tʜɪs Mᴇssᴀɢᴇ Tᴏ Yᴏᴜʀ Sᴀᴠᴇᴅ Mᴇssᴀɢᴇs Oʀ Aɴʏ Pʀɪᴠᴀᴛᴇ Cʜᴀᴛ.</i></b></blockquote>")
        await asyncio.sleep(600)
        for x in filesarr:
            await x.delete()
        await k.edit_text("<b>✅ Yᴏᴜʀ Mᴇssᴀɢᴇ Is Sᴜᴄᴄᴇssғᴜʟʟʏ Dᴇʟᴇᴛᴇᴅ</b>")  
        return
        
    # --- DSTORE (Batch from DB) ---
    elif data.split("-", 1)[0] == "DSTORE":
        sts = await message.reply("<b>Pʟᴇᴀsᴇ Wᴀɪᴛ...</b>")
        b_string = data.split("-", 1)[1]
        decoded = (base64.urlsafe_b64decode(b_string + "=" * (-len(b_string) % 4))).decode("ascii")
        try:
            f_msg_id, l_msg_id, f_chat_id, protect = decoded.split("_", 3)
        except:
            f_msg_id, l_msg_id, f_chat_id = decoded.split("_", 2)
            protect = "/pbatch" if PROTECT_CONTENT else "batch"
            
        filesarr = []
        async for msg in client.iter_messages(int(f_chat_id), int(l_msg_id), int(f_msg_id)):
            if msg.media:
                media = getattr(msg, msg.media.value)
                file = getattr(msg, msg.media.value)
                size = get_size(int(file.file_size))
                file_name = getattr(media, 'file_name', '')
                f_caption = getattr(msg, 'caption', file_name)
                
                if BATCH_FILE_CAPTION:
                    try:
                        f_caption = BATCH_FILE_CAPTION.format(file_name=file_name, file_size='' if size is None else size, file_caption=f_caption)
                    except:
                        f_caption = getattr(msg, 'caption', '')
                        
                file_id = file.file_id
                reply_markup = None
                
                if STREAM_MODE:
                    log_msg = await client.send_cached_media(chat_id=LOG_CHANNEL, file_id=file_id)
                    stream_link = f"{URL}watch/{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"
                    download_link = f"{URL}{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"
                    
                    reply_markup = InlineKeyboardMarkup([
                        [InlineKeyboardButton("• Dᴏᴡɴʟᴏᴀᴅ •", url=download_link), InlineKeyboardButton('• Wᴀᴛᴄʜ •', url=stream_link)],
                        [InlineKeyboardButton("• Wᴀᴛᴄʜ Iɴ Wᴇʙ Aᴘᴘ •", web_app=WebAppInfo(url=stream_link))]
                    ])
                
                try:
                    p = await msg.copy(message.chat.id, caption=f_caption, protect_content=True if protect == "/pbatch" else False, reply_markup=reply_markup)
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                    p = await msg.copy(message.chat.id, caption=f_caption, protect_content=True if protect == "/pbatch" else False, reply_markup=reply_markup)
                except:
                    continue
            elif msg.empty:
                continue
            else:
                try:
                    p = await msg.copy(message.chat.id, protect_content=True if protect == "/pbatch" else False)
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                    p = await msg.copy(message.chat.id, protect_content=True if protect == "/pbatch" else False)
                except:
                    continue
            filesarr.append(p)
            await asyncio.sleep(1)
            
        await sts.delete()
        k = await client.send_message(chat_id=message.from_user.id, text=f"<blockquote><b><u>❗️❗️❗️IMPORTANT❗️️❗️❗️</u></b>\n\nTʜɪs Mᴇssᴀɢᴇ Wɪʟʟ Bᴇ Dᴇʟᴇᴛᴇᴅ Iɴ <b><u>10 mins</u> 🫥 <i></b>(Dᴜᴇ Tᴏ Cᴏᴘʏʀɪɢʜᴛ Issᴜᴇs)</i>.\n\n<b><i>Pʟᴇᴀsᴇ Fᴏʀᴡᴀʀᴅ Tʜɪs Mᴇssᴀɢᴇ Tᴏ Yᴏᴜʀ Sᴀᴠᴇᴅ Mᴇssᴀɢᴇs Oʀ Aɴʏ Pʀɪᴠᴀᴛᴇ Cʜᴀᴛ.</i></b></blockquote>")
        await asyncio.sleep(600)
        for x in filesarr:
            await x.delete()
        await k.edit_text("<b>✅ Yᴏᴜʀ Mᴇssᴀɢᴇ Is Sᴜᴄᴄᴇssғᴜʟʟʏ Dᴇʟᴇᴛᴇᴅ</b>")
        return

    # --- Verify Token ---
    elif data.split("-", 1)[0] == "verify":
        userid = data.split("-", 2)[1]
        token = data.split("-", 3)[2]
        if str(message.from_user.id) != str(userid):
            return await message.reply_text(text="<b>Iɴᴠᴀʟɪᴅ Lɪɴᴋ Oʀ Exᴘɪʀᴇᴅ Lɪɴᴋ</b>", protect_content=True)
        is_valid = await check_token(client, userid, token)
        if is_valid:
            text = "<b>Hᴇʏ {} 👋,\n\nYᴏᴜ Hᴀᴠᴇ Cᴏᴍᴘʟᴇᴛᴇᴅ Tʜᴇ Vᴇʀɪꜰɪᴄᴀᴛɪᴏɴ...\n\nNᴏᴡ Yᴏᴜ Hᴀᴠᴇ Uɴʟɪᴍɪᴛᴇᴅ Aᴄᴄᴇss Tɪʟʟ Tᴏᴅᴀʏ Nᴏᴡ Eɴᴊᴏʏ\n\n</b>"
            if PREMIUM_AND_REFERAL_MODE:
                text += "<b>Iғ Yᴏᴜ Wᴀɴᴛ Dɪʀᴇᴄᴛ Fɪʟᴇs Wɪᴛʜᴏᴜᴛ Aɴʏ Vᴇʀɪғɪᴄᴀᴛɪᴏɴs Tʜᴇɴ Bᴜʏ Bᴏᴛ Sᴜʙsᴄʀɪᴘᴛɪᴏɴ ☺️\n\n💶 Sᴇɴᴅ /plan Tᴏ Bᴜʏ Sᴜʙsᴄʀɪᴘᴛɪᴏɴ</b>"           
            await message.reply_text(text=text.format(message.from_user.mention), protect_content=True)
            await verify_user(client, userid, token)
        else:
            return await message.reply_text(text="<b>Iɴᴠᴀʟɪᴅ Lɪɴᴋ Oʀ Exᴘɪʀᴇᴅ Lɪɴᴋ</b>", protect_content=True)
            
    # --- Send Files (Direct) ---
    if data.startswith("sendfiles"):
        chat_id = int("-" + file_id.split("-")[1])
        settings = await get_settings(chat_id)
        pre = 'allfilesp' if settings['file_secure'] else 'allfiles'
        g = await get_shortlink(chat_id, f"https://telegram.me/{temp.U_NAME}?start={pre}_{file_id}")
        btn = [[InlineKeyboardButton('Dᴏᴡɴʟᴏᴀᴅ Nᴏᴡ', url=g)]]
        if settings['tutorial']:
            btn.append([InlineKeyboardButton('Hᴏᴡ Tᴏ Dᴏᴡɴʟᴏᴀᴅ', url=await get_tutorial(chat_id))])
        text = "<b>✅ Yᴏᴜʀ Fɪʟᴇ Rᴇᴀᴅʏ Cʟɪᴄᴋ Oɴ Dᴏᴡɴʟᴏᴀᴅ Nᴏᴡ Bᴜᴛᴛᴏɴ Tʜᴇɴ Oᴘᴇɴ Lɪɴᴋ Tᴏ Gᴇᴛ Fɪʟᴇ\n\n</b>"
        if PREMIUM_AND_REFERAL_MODE:
            text += "<b>Iғ Yᴏᴜ Wᴀɴᴛ Dɪʀᴇᴄᴛ Fɪʟᴇs Wɪᴛʜᴏᴜᴛ Aɴʏ Oᴘᴇɴɪɴɢ Lɪɴᴋ Aɴᴅ Wᴀᴛᴄʜɪɴɢ Aᴅs Tʜᴇɴ Bᴜʏ Bᴏᴛ Sᴜʙsᴄʀɪᴘᴛɪᴏɴ ☺️\n\n💶 Sᴇɴᴅ /plan Tᴏ Bᴜʏ Sᴜʙsᴄʀɪᴘᴛɪᴏɴ</b>"
        k = await client.send_message(chat_id=message.from_user.id, text=text, reply_markup=InlineKeyboardMarkup(btn))
        await asyncio.sleep(300)
        await k.edit("<b>✅ Yᴏᴜʀ Mᴇssᴀɢᴇ Is Sᴜᴄᴄᴇssғᴜʟʟʏ Dᴇʟᴇᴛᴇᴅ</b>")
        return

    # --- Shortlink Logic ---
    elif data.startswith("short"):
        user = message.from_user.id
        chat_id = temp.SHORT.get(user)
        if not chat_id: 
             return await message.reply("Session expired. Please search again.")
        settings = await get_settings(chat_id)
        pre = 'filep' if settings['file_secure'] else 'file'
        g = await get_shortlink(chat_id, f"https://telegram.me/{temp.U_NAME}?start={pre}_{file_id}")
        btn = [[InlineKeyboardButton('Dᴏᴡɴʟᴏᴀᴅ Nᴏᴡ', url=g)]]
        if settings['tutorial']:
            btn.append([InlineKeyboardButton('Hᴏᴡ Tᴏ Dᴏᴡɴʟᴏᴀᴅ', url=await get_tutorial(chat_id))])
        text = "<b>✅ Yᴏᴜʀ Fɪʟᴇ Rᴇᴀᴅʏ Cʟɪᴄᴋ Oɴ Dᴏᴡɴʟᴏᴀᴅ Nᴏᴡ Bᴜᴛᴛᴏɴ Tʜᴇɴ Oᴘᴇɴ Lɪɴᴋ Tᴏ Gᴇᴛ Fɪʟᴇ\n\n</b>"
        if PREMIUM_AND_REFERAL_MODE:
            text += "<b>Iғ Yᴏᴜ Wᴀɴᴛ Dɪʀᴇᴄᴛ Fɪʟᴇs Wɪᴛʜᴏᴜᴛ Aɴʏ Oᴘᴇɴɪɴɢ Lɪɴᴋ Aɴᴅ Wᴀᴛᴄʜɪɴɢ Aᴅs Tʜᴇɴ Bᴜʏ Bᴏᴛ Sᴜʙsᴄʀɪᴘᴛɪᴏɴ ☺️\n\n💶 Sᴇɴᴅ /plan Tᴏ Bᴜʏ Sᴜʙsᴄʀɪᴘᴛɪᴏɴ</b>"
        k = await client.send_message(chat_id=user, text=text, reply_markup=InlineKeyboardMarkup(btn))
        await asyncio.sleep(1200)
        await k.edit("<b>✅ Yᴏᴜʀ Mᴇssᴀɢᴇ Is Sᴜᴄᴄᴇssғᴜʟʟʏ Dᴇʟᴇᴛᴇᴅ</b>")
        return
        
    # --- All Files (Multiple) ---
    elif data.startswith("all"):
        files = temp.GETALL.get(file_id)
        if not files:
            return await message.reply('<b><i>No such file exist.</b></i>')
        filesarr = []
        for file in files:
            file_id = file["file_id"]
            files1 = await get_file_details(file_id)
            title = files1["file_name"]
            size = get_size(files1["file_size"])
            f_caption = files1["caption"]
            if CUSTOM_FILE_CAPTION:
                try:
                    f_caption = CUSTOM_FILE_CAPTION.format(file_name='' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)
                except:
                    pass
            if f_caption is None:
                f_caption = f"{' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@'), files1['file_name'].split()))}"
            
            # Premium/Verify Check
            if not await db.has_premium_access(message.from_user.id):
                if not await check_verification(client, message.from_user.id) and VERIFY:
                    btn = [
                        [InlineKeyboardButton("Vᴇʀɪғʏ", url=await get_token(client, message.from_user.id, f"https://telegram.me/{temp.U_NAME}?start="))],
                        [InlineKeyboardButton("Hᴏᴡ Tᴏ Vᴇʀɪғʏ", url=VERIFY_TUTORIAL)]
                    ]
                    text = "<b>Hᴇʏ {} 👋,\n\nYᴏᴜ Aʀᴇ Nᴏᴛ Vᴇʀɪғɪᴇᴅ Tᴏᴅᴀʏ, Pʟᴇᴀsᴇ Cʟɪᴄᴋ Oɴ Vᴇʀɪғʏ & Gᴇᴛ Uɴʟɪᴍɪᴛᴇᴅ Aᴄᴄᴇss Fᴏʀ Tᴏᴅᴀʏ</b>"
                    if PREMIUM_AND_REFERAL_MODE:
                        text += "<b>Iғ Yᴏᴜ Wᴀɴᴛ Dɪʀᴇᴄᴛ Fɪʟᴇs Wɪᴛʜᴏᴜᴛ Aɴʏ Vᴇʀɪғɪᴄᴀᴛɪᴏɴs Tʜᴇɴ Bᴜʏ Bᴏᴛ Sᴜʙsᴄʀɪᴘᴛɪᴏɴ ☺️\n\n💶 Sᴇɴᴅ /plan Tᴏ Bᴜʏ Sᴜʙsᴄʀɪᴘᴛɪᴏɴ</b>"
                    await message.reply_text(text=text.format(message.from_user.mention), protect_content=True, reply_markup=InlineKeyboardMarkup(btn))
                    return

            reply_markup = None
            if STREAM_MODE:
                button = [[InlineKeyboardButton('Sᴛʀᴇᴀᴍ Aɴᴅ Dᴏᴡɴʟᴏᴀᴅ', callback_data=f'generate_stream_link:{file_id}')]]
                reply_markup = InlineKeyboardMarkup(button)
            
            msg = await client.send_cached_media(
                chat_id=message.from_user.id,
                file_id=file_id,
                caption=f_caption,
                protect_content=True if pre == 'allfilesp' else False,
                reply_markup=reply_markup
            )
            filesarr.append(msg)
            
        k = await client.send_message(chat_id=message.from_user.id, text=f"<blockquote><b><u>❗️❗️❗️IMPORTANT❗️️❗️❗️</u></b>\n\nTʜɪs Mᴇssᴀɢᴇ Wɪʟʟ Bᴇ Dᴇʟᴇᴛᴇᴅ Iɴ <b><u>10 mins</u> 🫥 <i></b>(Dᴜᴇ Tᴏ Cᴏᴘʏʀɪɢʜᴛ Issᴜᴇs)</i>.\n\n<b><i>Pʟᴇᴀsᴇ Fᴏʀᴡᴀʀᴅ Tʜɪs Mᴇssᴀɢᴇ Tᴏ Yᴏᴜʀ Sᴀᴠᴇᴅ Mᴇssᴀɢᴇs Oʀ Aɴʏ Pʀɪᴠᴀᴛᴇ Cʜᴀᴛ.</i></b></blockquote>")
        await asyncio.sleep(600)
        for x in filesarr:
            await x.delete()
        await k.edit_text("<b>✅ Yᴏᴜʀ Mᴇssᴀɢᴇ Is Sᴜᴄᴄᴇssғᴜʟʟʏ Dᴇʟᴇᴛᴇᴅ</b>")
        return    

    # --- Shortlink Redirection ---
    elif data.startswith("files"):
        user = message.from_user.id
        if temp.SHORT.get(user) is None:
            await message.reply_text(text="<b>Please Search Again in Group</b>")
        else:
            chat_id = temp.SHORT.get(user)
        
        settings = await get_settings(chat_id)
        pre = 'filep' if settings['file_secure'] else 'file'
        
        if settings['is_shortlink'] and not await db.has_premium_access(user):
            g = await get_shortlink(chat_id, f"https://telegram.me/{temp.U_NAME}?start={pre}_{file_id}")
            btn = [[InlineKeyboardButton('Dᴏᴡɴʟᴏᴀᴅ Nᴏᴡ', url=g)]]
            if settings['tutorial']:
                btn.append([InlineKeyboardButton('Hᴏᴡ Tᴏ Dᴏᴡɴʟᴏᴀᴅ', url=await get_tutorial(chat_id))])
            text = "<b>✅ Yᴏᴜʀ Fɪʟᴇ Rᴇᴀᴅʏ Cʟɪᴄᴋ Oɴ Dᴏᴡɴʟᴏᴀᴅ Nᴏᴡ Bᴜᴛᴛᴏɴ Tʜᴇɴ Oᴘᴇɴ Lɪɴᴋ Tᴏ Gᴇᴛ Fɪʟᴇ\n\n</b>"
            if PREMIUM_AND_REFERAL_MODE:
                text += "<b>Iғ Yᴏᴜ Wᴀɴᴛ Dɪʀᴇᴄᴛ Fɪʟᴇs Wɪᴛʜᴏᴜᴛ Aɴʏ Oᴘᴇɴɪɴɢ Lɪɴᴋ Aɴᴅ Wᴀᴛᴄʜɪɴɢ Aᴅs Tʜᴇɴ Bᴜʏ Bᴏᴛ Sᴜʙsᴄʀɪᴘᴛɪᴏɴ ☺️\n\n💶 Sᴇɴᴅ /plan Tᴏ Bᴜʏ Sᴜʙsᴄʀɪᴘᴛɪᴏɴ</b>"
            k = await client.send_message(chat_id=message.from_user.id, text=text, reply_markup=InlineKeyboardMarkup(btn))
            await asyncio.sleep(1200)
            await k.edit("<b>✅ Yᴏᴜʀ Mᴇssᴀɢᴇ Is Sᴜᴄᴄᴇssғᴜʟʟʏ Dᴇʟᴇᴛᴇᴅ</b>")
            return

    # --- Single File (Final Fallback) ---
    user = message.from_user.id
    files_ = await get_file_details(file_id)           
    
    # Logic for Decoded Base64 (if file details not found directly)
    if not files_:
        try:
            pre, file_id = ((base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))).decode("ascii")).split("_", 1)
        except:
            return await message.reply('No such file exist.')

        if not await db.has_premium_access(message.from_user.id):
            if not await check_verification(client, message.from_user.id) and VERIFY:
                btn = [
                    [InlineKeyboardButton("Vᴇʀɪғʏ", url=await get_token(client, message.from_user.id, f"https://telegram.me/{temp.U_NAME}?start="))],
                    [InlineKeyboardButton("Hᴏᴡ Tᴏ Vᴇʀɪғʏ", url=VERIFY_TUTORIAL)]
                ]
                text = "<b>Hᴇʏ {} 👋,\n\nYᴏᴜ Aʀᴇ Nᴏᴛ Vᴇʀɪғɪᴇᴅ Tᴏᴅᴀʏ, Pʟᴇᴀsᴇ Cʟɪᴄᴋ Oɴ Vᴇʀɪғʏ & Gᴇᴛ Uɴʟɪᴍɪᴛᴇᴅ Aᴄᴄᴇss Fᴏʀ Tᴏᴅᴀʏ</b>"
                if PREMIUM_AND_REFERAL_MODE:
                    text += "<b>Iғ Yᴏᴜ Wᴀɴᴛ Dɪʀᴇᴄᴛ Fɪʟᴇs Wɪᴛʜᴏᴜᴛ Aɴʏ Vᴇʀɪғɪᴄᴀᴛɪᴏɴs Tʜᴇɴ Bᴜʏ Bᴏᴛ Sᴜʙsᴄʀɪᴘᴛɪᴏɴ ☺️\n\n💶 Sᴇɴᴅ /plan Tᴏ Bᴜʏ Sᴜʙsᴄʀɪᴘᴛɪᴏɴ</b>"
                await message.reply_text(text=text.format(message.from_user.mention), protect_content=True, reply_markup=InlineKeyboardMarkup(btn))
                return

        reply_markup = None
        if STREAM_MODE:
            button = [[InlineKeyboardButton('Sᴛʀᴇᴀᴍ Aɴᴅ Dᴏᴡɴʟᴏᴀᴅ', callback_data=f'generate_stream_link:{file_id}')]]
            reply_markup = InlineKeyboardMarkup(button)
            
        msg = await client.send_cached_media(
            chat_id=message.from_user.id,
            file_id=file_id,
            protect_content=True if pre == 'filep' else False,
            reply_markup=reply_markup
        )
        filetype = msg.media
        file = getattr(msg, filetype.value)
        title = file.file_name
        size = get_size(file.file_size)
        f_caption = f"<code>{title}</code>"
        if CUSTOM_FILE_CAPTION:
            try:
                f_caption = CUSTOM_FILE_CAPTION.format(file_name='' if title is None else title, file_size='' if size is None else size, file_caption='')
            except:
                pass
        await msg.edit_caption(caption=f_caption)
        btn = [[InlineKeyboardButton("✅ Gᴇᴛ Fɪʟᴇ Aɢᴀɪɴ ✅", callback_data=f'del#{file_id}')]]
        k = await msg.reply(text=f"<blockquote><b><u>❗️❗️❗️IMPORTANT❗️️❗️❗️</u></b>\n\nTʜɪs Mᴇssᴀɢᴇ Wɪʟʟ Bᴇ Dᴇʟᴇᴛᴇᴅ Iɴ <b><u>10 mins</u> 🫥 <i></b>(Dᴜᴇ Tᴏ Cᴏᴘʏʀɪɢʜᴛ Issᴜᴇs)</i>.\n\n<b><i>Pʟᴇᴀsᴇ Fᴏʀᴡᴀʀᴅ Tʜɪs Mᴇssᴀɢᴇ Tᴏ Yᴏᴜʀ Sᴀᴠᴇᴅ Mᴇssᴀɢᴇs Oʀ Aɴʏ Pʀɪᴠᴀᴛᴇ Cʜᴀᴛ.</i></b></blockquote>")
        await asyncio.sleep(600)
        await msg.delete()
        await k.edit_text("<b>✅ Yᴏᴜʀ Mᴇssᴀɢᴇ Is Sᴜᴄᴄᴇssғᴜʟʟʏ Dᴇʟᴇᴛᴇᴅ Iғ Yᴏᴜ Wᴀɴᴛ Aɢᴀɪɴ Tʜᴇɴ Cʟɪᴄᴋ Oɴ Bᴇʟᴏᴡ Bᴜᴛᴛᴏɴ</b>", reply_markup=InlineKeyboardMarkup(btn))
        return

    # Normal File details from DB
    files = files_
    title = files["file_name"]
    size = get_size(files["file_size"])
    f_caption = files["caption"]
    if CUSTOM_FILE_CAPTION:
        try:
            f_caption = CUSTOM_FILE_CAPTION.format(file_name='' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)
        except:
            f_caption = f_caption
    if f_caption is None:
        f_caption = f"{' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@'), files['file_name'].split()))}"
        
    if not await db.has_premium_access(message.from_user.id):
        if not await check_verification(client, message.from_user.id) and VERIFY:
            btn = [
                [InlineKeyboardButton("Vᴇʀɪғʏ", url=await get_token(client, message.from_user.id, f"https://telegram.me/{temp.U_NAME}?start="))],
                [InlineKeyboardButton("Hᴏᴡ Tᴏ Vᴇʀɪғʏ", url=VERIFY_TUTORIAL)]
            ]
            text = "<b>Hᴇʏ {} 👋,\n\nYᴏᴜ Aʀᴇ Nᴏᴛ Vᴇʀɪғɪᴇᴅ Tᴏᴅᴀʏ, Pʟᴇᴀsᴇ Cʟɪᴄᴋ Oɴ Vᴇʀɪғʏ & Gᴇᴛ Uɴʟɪᴍɪᴛᴇᴅ Aᴄᴄᴇss Fᴏʀ Tᴏᴅᴀʏ</b>"
            if PREMIUM_AND_REFERAL_MODE:
                text += "<b>Iғ Yᴏᴜ Wᴀɴᴛ Dɪʀᴇᴄᴛ Fɪʟᴇs Wɪᴛʜᴏᴜᴛ Aɴʏ Vᴇʀɪғɪᴄᴀᴛɪᴏɴs Tʜᴇɴ Bᴜʏ Bᴏᴛ Sᴜʙsᴄʀɪᴘᴛɪᴏɴ ☺️\n\n💶 Sᴇɴᴅ /plan Tᴏ Bᴜʏ Sᴜʙsᴄʀɪᴘᴛɪᴏɴ</b>"
            await message.reply_text(text=text.format(message.from_user.mention), protect_content=True, reply_markup=InlineKeyboardMarkup(btn))
            return

    reply_markup = None
    if STREAM_MODE:
        button = [[InlineKeyboardButton('Sᴛʀᴇᴀᴍ Aɴᴅ Dᴏᴡɴʟᴏᴀᴅ', callback_data=f'generate_stream_link:{file_id}')]]
        reply_markup = InlineKeyboardMarkup(button)
        
    msg = await client.send_cached_media(
        chat_id=message.from_user.id,
        file_id=file_id,
        caption=f_caption,
        protect_content=True if pre == 'filep' else False,
        reply_markup=reply_markup
    )
    btn = [[InlineKeyboardButton("✅ Gᴇᴛ Fɪʟᴇ Aɢᴀɪɴ ✅", callback_data=f'del#{file_id}')]]
    k = await msg.reply(text=f"<blockquote><b><u>❗️❗️❗️IMPORTANT❗️️❗️❗️</u></b>\n\nTʜɪs Mᴇssᴀɢᴇ Wɪʟʟ Bᴇ Dᴇʟᴇᴛᴇᴅ Iɴ <b><u>10 mins</u> 🫥 <i></b>(Dᴜᴇ Tᴏ Cᴏᴘʏʀɪɢʜᴛ Issᴜᴇs)</i>.\n\n<b><i>Pʟᴇᴀsᴇ Fᴏʀᴡᴀʀᴅ Tʜɪs Mᴇssᴀɢᴇ Tᴏ Yᴏᴜʀ Sᴀᴠᴇᴅ Mᴇssᴀɢᴇs Oʀ Aɴʏ Pʀɪᴠᴀᴛᴇ Cʜᴀᴛ.</i></b></blockquote>")
    await asyncio.sleep(600)
    await msg.delete()
    await k.edit_text("<b>✅ Yᴏᴜʀ Mᴇssᴀɢᴇ Is Sᴜᴄᴄᴇssғᴜʟʟʏ Dᴇʟᴇᴛᴇᴅ Iғ Yᴏᴜ Wᴀɴᴛ Aɢᴀɪɴ Tʜᴇɴ Cʟɪᴄᴋ Oɴ Bᴇʟᴏᴡ Bᴜᴛᴛᴏɴ</b>", reply_markup=InlineKeyboardMarkup(btn))
    return

# MyselfNeon
# Don't Remove Credit 🥺
# Telegram Channel @NeonFiles
