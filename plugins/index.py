
import logging, re, asyncio
from utils import temp
from info import ADMINS
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, MessageNotModified
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid, ChatAdminRequired, UsernameInvalid, UsernameNotModified
from info import INDEX_REQ_CHANNEL as LOG_CHANNEL
from database.ia_filterdb import save_file
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
lock = asyncio.Lock()

@Client.on_callback_query(filters.regex(r'^index'))
async def index_files(bot, query):
    if query.data.startswith('index_cancel'):
        temp.CANCEL = True
        return await query.answer("Cancelling Indexing")
    _, raju, chat, lst_msg_id, from_user = query.data.split("#")
    if raju == 'reject':
        await query.message.delete()
        await bot.send_message(
            int(from_user),
            f'**__Your Submission for Indexing {chat} has been Decliened by Our Moderators__**.',
            reply_to_message_id=int(lst_msg_id)
        )
        return

    if lock.locked():
        return await query.answer('Wait until previous process complete.', show_alert=True)
    msg = query.message

    await query.answer('Processing...⏳', show_alert=True)
    if int(from_user) not in ADMINS:
        await bot.send_message(
            int(from_user),
            f'**__Your Submission for Indexing {chat} has been Accepted by Our Moderators and will be Added Soon.__**',
            reply_to_message_id=int(lst_msg_id)
        )
    await msg.edit(
        "Starting Indexing",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton('Cancel', callback_data='index_cancel')]]
        )
    )
    try:
        chat = int(chat)
    except:
        chat = chat
    await index_files_to_db(int(lst_msg_id), chat, msg, bot)


@Client.on_message(filters.private & filters.command('index'))
async def send_for_index(bot, message):
    vj = await bot.ask(message.chat.id, "**__Now Send Me Your Channel Last Post Link Or Forward A Last Message From Your Index Channel.\n\nAnd You Can Skip Number By__ \n/setskip __YᴏᴜʀSᴋɪᴘNᴜᴍʙᴇʀ__**")
    if vj.forward_from_chat and vj.forward_from_chat.type == enums.ChatType.CHANNEL:
        last_msg_id = vj.forward_from_message_id
        chat_id = vj.forward_from_chat.username or vj.forward_from_chat.id
    elif vj.text:
        regex = re.compile("(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")
        match = regex.match(vj.text)
        if not match:
            return await vj.reply('**__Invalid Link\n\nTry Again By__ /index')
        chat_id = match.group(4)
        last_msg_id = int(match.group(5))
        if chat_id.isnumeric():
            chat_id  = int(("-100" + chat_id))
    else:
        return
    try:
        await bot.get_chat(chat_id)
    except ChannelInvalid:
        return await vj.reply('**__This May be a Private Channel / Group. Make me an Admin Over there to Index the files.__**')
    except (UsernameInvalid, UsernameNotModified):
        return await vj.reply('Invalid Link specified.')
    except Exception as e:
        logger.exception(e)
        return await vj.reply(f'Errors - {e}')
    try:
        k = await bot.get_messages(chat_id, last_msg_id)
    except:
        return await message.reply('**__Make Sure That Iam An Admin In The Channel, if channel is private__**')
    if k.empty:
        return await message.reply('**__This may be Group and I am not am Admin of the Group.__**')

    if message.from_user.id in ADMINS:
        buttons = [[
            InlineKeyboardButton('Yes', callback_data=f'index#accept#{chat_id}#{last_msg_id}#{message.from_user.id}')
        ],[
            InlineKeyboardButton('close', callback_data='close_data')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        return await message.reply(
            f'**__Do you Want To Index This Channel/ Group ?\n\nChat ID/ Username:__** <code>{chat_id}</code>\n**__Last Message ID:__** <code>{last_msg_id}</code>',
            reply_markup=reply_markup
        )

    if type(chat_id) is int:
        try:
            link = (await bot.create_chat_invite_link(chat_id)).invite_link
        except ChatAdminRequired:
            return await message.reply('**__Make Sure I am An Admin in the Chat and have Permission to Invite Users.__**')
    else:
        link = f"@{message.forward_from_chat.username}"
    buttons = [[
        InlineKeyboardButton('Aᴄᴄᴇᴘᴛ Iɴᴅᴇx', callback_data=f'index#accept#{chat_id}#{last_msg_id}#{message.from_user.id}')
    ],[
        InlineKeyboardButton('Rᴇjᴇᴄᴛ Iɴᴅᴇx', callback_data=f'index#reject#{chat_id}#{message.id}#{message.from_user.id}'),
    ]]
    reply_markup = InlineKeyboardMarkup(buttons)
    await bot.send_message(
        LOG_CHANNEL,
        f'#IndexRequest\n\n**__By__ : {message.from_user.mention} (<code>{message.from_user.id}</code>)\n__Chat ID/ Username__ - <code> {chat_id}</code>\n__Last Message ID__ - <code>{last_msg_id}</code>\nInviteLink - {link}',
        reply_markup=reply_markup
    )
    await message.reply('**__ThankYou For the Contribution, Wait For My Moderators to Verify the Files.__**')


@Client.on_message(filters.command('setskip') & filters.user(ADMINS))
async def set_skip_number(bot, message):
    if ' ' in message.text:
        _, skip = message.text.split(" ")
        try:
            skip = int(skip)
        except:
            return await message.reply("**__Skip Number Should be an Integer.__**")
        await message.reply(f"**__Successfully set SKIP number as__** {skip}")
        temp.CURRENT = int(skip)
    else:
        await message.reply("**__Give me a Skip Number__**")


async def index_files_to_db(lst_msg_id, chat, msg, bot):
    total_files = 0
    duplicate = 0
    errors = 0
    deleted = 0
    no_media = 0
    unsupported = 0
    async with lock:
        try:
            current = temp.CURRENT
            temp.CANCEL = False
            async for message in bot.iter_messages(chat, lst_msg_id, temp.CURRENT):
                if temp.CANCEL:
                    await msg.edit(f"**__Successfully Cancelled!!\n\nSaved__ <code>{total_files}</code> __files to dataBase!\nDuplicate Files Skipped:__ <code>{duplicate}</code>\n__Deleted Messages Skipped:__ <code>{deleted}</code>\n__Non-Media messages skipped:__ <code>{no_media + unsupported}</code>(Unsupported Media - `{unsupported}` )\n__Errors Occurred:__ <code>{errors}</code>**")
                    break
                current += 1
                if current % 30 == 0:
                    can = [[InlineKeyboardButton('Cancel', callback_data='index_cancel')]]
                    reply = InlineKeyboardMarkup(can)
                    try:
                        await msg.edit_text(
                            text=f"**__Total messages fetched:__ <code>{current}</code>\n__Total messages saved:__ <code>{total_files}</code>\n__Duplicate Files Skipped:__ <code>{duplicate}</code>\n__Deleted Messages Skipped:__ <code>{deleted}</code>\n__Non-Media messages skipped:__ <code>{no_media + unsupported}</code>(Unsupported Media - `{unsupported}` )\n__Errors Occurred:__ <code>{errors}</code>**",
                            reply_markup=reply
                        )
                    except MessageNotModified:
                        pass
                if message.empty:
                    deleted += 1
                    continue
                elif not message.media:
                    no_media += 1
                    continue
                elif message.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.AUDIO, enums.MessageMediaType.DOCUMENT]:
                    unsupported += 1
                    continue
                media = getattr(message, message.media.value, None)
                if not media:
                    unsupported += 1
                    continue
                media.caption = message.caption
                aynav, vnay = await save_file(media)
                if aynav:
                    total_files += 1
                elif vnay == 0:
                    duplicate += 1
                elif vnay == 2:
                    errors += 1
        except Exception as e:
            logger.exception(e)
            k = await msg.edit(f'**__Error: {e}__**')
            await k.reply_text(f'**__Succesfully saved__ <code>{total_files}</code> __To DataBase!\nDuplicate Files Skipped:__ <code>{duplicate}</code>\n__Deleted Messages Skipped:__ <code>{deleted}</code>\n__Non-Media messages Skipped:__ <code>{no_media + unsupported}</code>(Unsupported Media - `{unsupported}` )\n__Errors Occurred:__ <code>{errors}</code>**')
            await k.reply_text("**__If You Get Message Not Modified Error Then Skip Your Saved File Then Index Again__**")
        else:
            await msg.edit(f'**__Succesfully Saved__ <code>{total_files}</code> __To DataBase!\nDuplicate Files Skipped:__ <code>{duplicate}</code>\n__Deleted Messages Skipped:__ <code>{deleted}</code>\n__Non-Media messages skipped:__ <code>{no_media + unsupported}</code>(Unsupported Media - `{unsupported}` )\n__Errors Occurred__: <code>{errors}</code>**')
