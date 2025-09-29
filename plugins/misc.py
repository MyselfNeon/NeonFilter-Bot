#Mics.py
import os, logging, time
from pyrogram import Client, filters, enums
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant, MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
from info import IMDB_TEMPLATE
from utils import extract_user, get_file_id, get_poster, last_online 
from datetime import datetime
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

@Client.on_message(filters.command('id'))
async def showid(client, message):
    chat_type = message.chat.type
    if chat_type == enums.ChatType.PRIVATE:
        user_id = message.chat.id
        first = message.from_user.first_name
        last = message.from_user.last_name or ""
        username = message.from_user.username
        dc_id = message.from_user.dc_id or ""
        await message.reply_text(
            f"<b><i>👤 Fɪʀsᴛ Nᴀᴍᴇ : {first}\n📌 Lᴀsᴛ Nᴀᴍᴇ : {last}\n🔖 UsᴇʀNᴀᴍᴇ : {username}\n🆔 Tᴇʟᴇɢʀᴀᴍ ID : </i></b><code>{user_id}</code>\n<b><i>🏢 Dᴀᴛᴀ Cᴇɴᴛʀᴇ : {dc_id}</i></b>",
            quote=True,
            parse_mode=enums.ParseMode.HTML
        )

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        _id = ""
        _id += (
            "<b><i>📝 Cʜᴀᴛ ID :</i></b> "
            f"<code>{message.chat.id}</code>\n"
        )
        if message.reply_to_message:
            _id += (
                "<b><i>👤 Usᴇʀ ID :</i></b> "
                f"<code>{message.from_user.id if message.from_user else 'Anonymous'}</code>\n"
                "<b><i>🆔 Rᴇᴘʟɪᴇᴅ Usᴇʀ ID :</i></b> "
                f"<code>{message.reply_to_message.from_user.id if message.reply_to_message.from_user else 'Anonymous'}</code>\n"
            )
            file_info = get_file_id(message.reply_to_message)
        else:
            _id += (
                "<b><i>🔖 Usᴇʀ ID :</i></b> "
                f"<code>{message.from_user.id if message.from_user else 'Anonymous'}</code>\n"
            )
            file_info = get_file_id(message)
        if file_info:
            _id += (
                f"<b><i>{file_info.message_type} :</i></b> "
                f"<code>{file_info.file_id}</code>\n"
            )
        await message.reply_text(
            _id,
            quote=True,
            parse_mode=enums.ParseMode.HTML
        )

@Client.on_message(filters.command(["info"]))
async def who_is(client, message):
    status_message = await message.reply_text(
        "<b><i>⌛ Fetching User Info...</i></b>"
    )
    await status_message.edit_text(
        "<b><i>⏳ Processing User Info...</i></b>"
    )
    from_user = None
    from_user_id, _ = extract_user(message)
    try:
        from_user = await client.get_users(from_user_id)
    except Exception as error:
        await status_message.edit_text(str(error))
        return
    if from_user is None:
        return await status_message.edit_text("no valid user_id / message specified")
    message_out_str = ""
    message_out_str += f"<b><i>👤 Fɪʀsᴛ Nᴀᴍᴇ : {from_user.first_name}</i></b>\n"
    last_name = from_user.last_name or "<b><i>Nᴏɴᴇ</i></b>"
    message_out_str += f"<b><i>📌 Lᴀsᴛ Nᴀᴍᴇ : {last_name}</i></b>\n"
    message_out_str += f"<b><i>🆔 Tᴇʟᴇɢʀᴀᴍ ID :</i></b> <code>{from_user.id}</code>\n"
    username = from_user.username or "<b><i>Nᴏɴᴇ</i></b>"
    dc_id = from_user.dc_id or "[User Doesn't Have A Valid DP]"
    message_out_str += f"<b><i>🏢 Dᴀᴛᴀ Cᴇɴᴛʀᴇ : {dc_id}</i></b>\n"
    message_out_str += f"<b><i>🔖 Usᴇʀ Nᴀᴍᴇ : @{username}</i></b>\n"
    message_out_str += f"<b><i>🖇️ Usᴇʀ Lɪɴᴋ : <a href='tg://user?id={from_user.id}'>Cʟɪᴄᴋ Hᴇʀᴇ</a></i></b>\n"
    if message.chat.type in ((enums.ChatType.SUPERGROUP, enums.ChatType.CHANNEL)):
        try:
            chat_member_p = await message.chat.get_member(from_user.id)
            joined_date = (
                chat_member_p.joined_date or datetime.now()
            ).strftime("%d %b %Y | %I:%M %p")
            message_out_str += (
                "<b><i>🎭 Jᴏɪɴᴇᴅ Tʜɪs Cʜᴀᴛ Oɴ :</i></b>\n"
                f"<b><i>{joined_date}</i></b>\n"
            )
        except UserNotParticipant:
            pass
    chat_photo = from_user.photo
    if chat_photo:
        local_user_photo = await client.download_media(chat_photo.big_file_id)
        buttons = [[
            InlineKeyboardButton('🔐 Close', callback_data='close_data')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_photo(
            photo=local_user_photo,
            quote=True,
            reply_markup=reply_markup,
            caption=message_out_str,
            parse_mode=enums.ParseMode.HTML,
            disable_notification=True
        )
        try:
            os.remove(local_user_photo)
        except Exception:
            pass
    else:
        buttons = [[
            InlineKeyboardButton('🔐 Cʟᴏsᴇ', callback_data='close_data')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_text(
            text=message_out_str,
            reply_markup=reply_markup,
            quote=True,
            parse_mode=enums.ParseMode.HTML,
            disable_notification=True
        )
    await status_message.delete()

@Client.on_message(filters.command(["imdb", 'search']))
async def imdb_search(client, message):
    if ' ' in message.text:
        k = await message.reply_text('<b><i>Searching ImDB</i></b>')
        r, title = message.text.split(None, 1)
        movies = await get_poster(title, bulk=True)
        if not movies:
            return await message.reply_text("<b><i>No Results Found</i></b>")
        btn = [
            [
                InlineKeyboardButton(
                    text=f"{movie.get('title')} - {movie.get('year')}",
                    callback_data=f"imdb#{movie.get('movieID')}",
                )
            ]
            for movie in movies
        ]
        await k.edit_text('<b><i>Here is What I Found On IMDb 🌐</i></b>', reply_markup=InlineKeyboardMarkup(btn))
    else:
        await message.reply_text('<b><i>Give Me a Movie / Series Name</i></b>')

@Client.on_callback_query(filters.regex('^imdb'))
async def imdb_callback(bot: Client, quer_y: CallbackQuery):
    i, movie = quer_y.data.split('#')
    imdb = await get_poster(query=movie, id=True)
    btn = [
            [
                InlineKeyboardButton(
                    text=f"{imdb.get('title')}",
                    url=imdb['url'],
                )
            ]
        ]
    if imdb:
        caption = IMDB_TEMPLATE.format(
            query = imdb['title'],
            title = imdb['title'],
            votes = imdb['votes'],
            aka = imdb["aka"],
            seasons = imdb["seasons"],
            box_office = imdb['box_office'],
            localized_title = imdb['localized_title'],
            kind = imdb['kind'],
            imdb_id = imdb["imdb_id"],
            cast = imdb["cast"],
            runtime = imdb['runtime'],
            countries = imdb['countries'],
            certificates = imdb["certificates"],
            languages = imdb["languages"],
            director = imdb["director"],
            writer = imdb["writer"],
            producer = imdb["producer"],
            composer = imdb["composer"],
            cinematographer = imdb["cinematographer"],
            music_team = imdb["music_team"],
            distributors = imdb["distributors"],
            release_date = imdb['release_date'],
            year = imdb['year'],
            genres = imdb['genres'],
            poster = imdb['poster'],
            plot = imdb['plot'],
            rating = imdb['rating'],
            url = imdb['url'],
            **locals()
        )
    else:
        caption = "No Results"
    if imdb.get('poster'):
        try:
            await quer_y.message.reply_photo(photo=imdb['poster'], caption=caption, reply_markup=InlineKeyboardMarkup(btn))
        except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
            pic = imdb.get('poster')
            poster = pic.replace('.jpg', "._V1_UX360.jpg")
            await quer_y.message.reply_photo(photo=poster, caption=caption, reply_markup=InlineKeyboardMarkup(btn))
        except Exception as e:
            logger.exception(e)
            await quer_y.message.reply_text(caption, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=False)
        await quer_y.message.delete()
    else:
        await quer_y.message.edit_text(caption, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=False)
    await quer_y.answer()
    

# Dont remove Credits
# Developer Telegram @MyselfNeon
# Update channel - @NeonFiles


