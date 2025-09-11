# plugins/song_standalone.py
import os, tempfile, shutil, asyncio, logging
from urllib.parse import quote_plus, unquote_plus
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

import aiohttp
from shazamio import Shazam
from pydub import AudioSegment
from pytube import YouTube
from youtubesearchpython import VideosSearch

log = logging.getLogger(__name__)
shazam = Shazam()

# In-memory user state (only for this plugin)
SONG_STATE = {}

MAX_RECOG_SECONDS = 25
LYRICS_OVH = "https://api.lyrics.ovh/v1/{artist}/{title}"

# ---------------- Utilities ----------------
def song_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎧 Recognize Song", callback_data="song|menu|recognize")],
        [InlineKeyboardButton("🔎 Search by Name", callback_data="song|menu|search")],
        [InlineKeyboardButton("🔗 Link", callback_data="song|menu|link")],
        [InlineKeyboardButton("🔤 Lyrics", callback_data="song|menu|lyrics")],
    ])

def song_result_kbd(title, artist, youtube_url=None):
    q_title, q_artist = quote_plus(title), quote_plus(artist)
    kb = []
    if youtube_url:
        kb.append([InlineKeyboardButton("▶️ YouTube Link", callback_data=f"song|result|yt|{quote_plus(youtube_url)}")])
    kb.append([
        InlineKeyboardButton("🔤 Get Lyrics", callback_data=f"song|result|lyrics|{q_title}||{q_artist}"),
        InlineKeyboardButton("🎵 Song MP3", callback_data=f"song|result|mp3|{q_title}||{q_artist}")
    ])
    return InlineKeyboardMarkup(kb)

def youtube_search(query):
    try:
        vs = VideosSearch(query, limit=1)
        res = vs.result()
        if res and res.get("result"):
            v = res["result"][0]
            url = f"https://www.youtube.com/watch?v={v['id']}"
            return url, v.get("title"), v.get("channel", {}).get("name", ""), v.get("thumbnails", [{}])[0].get("url")
    except: pass
    return None, None, None, None

async def fetch_lyrics(artist, title):
    try:
        url = LYRICS_OVH.format(artist=quote_plus(artist), title=quote_plus(title))
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=10) as r:
                if r.status == 200:
                    return (await r.json()).get("lyrics")
    except: pass
    return None

def convert_to_wav(src, dst):
    audio = AudioSegment.from_file(src)[:MAX_RECOG_SECONDS*1000]
    audio.set_frame_rate(16000).set_channels(1).export(dst, format="wav")

async def recognize_song(wav_path):
    with open(wav_path, "rb") as f:
        return await shazam.recognize_song(f.read())

async def download_mp3(yt_url, tmpdir):
    def blocking(url, outdir):
        yt = YouTube(url)
        stream = yt.streams.filter(only_audio=True).order_by("abr").desc().first()
        return stream.download(output_path=outdir), yt.title, yt.author
    loop = asyncio.get_event_loop()
    file, title, author = await loop.run_in_executor(None, blocking, yt_url, tmpdir)
    mp3 = os.path.splitext(file)[0] + ".mp3"
    AudioSegment.from_file(file).export(mp3, format="mp3")
    return mp3, title, author

def split_chunks(text, size=3500):
    return [text[i:i+size] for i in range(0, len(text), size)]

# ---------------- Handlers ----------------
@Client.on_message(filters.private & filters.command("songs"))
async def song_entry(client: Client, m: Message):
    await m.reply_text("🎶 *Song Module*\nChoose an action:", parse_mode="markdown", reply_markup=song_main_menu())

@Client.on_callback_query(filters.regex(r"^song\|menu\|"))
async def song_menu_cb(client: Client, cq: CallbackQuery):
    _, _, action = cq.data.split("|", 2)
    uid = cq.from_user.id
    if action == "recognize":
        SONG_STATE[uid] = "expect_audio"
        await cq.message.reply_text("📤 Send me audio/voice/video.")
    elif action == "search":
        SONG_STATE[uid] = "expect_search"
        await cq.message.reply_text("🔎 Send me a song name.")
    elif action == "link":
        SONG_STATE[uid] = "expect_link"
        await cq.message.reply_text("🔗 Send me a YouTube link.")
    elif action == "lyrics":
        SONG_STATE[uid] = "expect_lyrics"
        await cq.message.reply_text("🔤 Send me a song title or artist - title.")
    await cq.answer()

@Client.on_message(filters.private & (filters.audio | filters.voice | filters.video | filters.video_note))
async def song_media(client: Client, m: Message):
    if SONG_STATE.get(m.from_user.id) != "expect_audio": return
    wait = await m.reply_text("🎧 Recognizing...")
    tmp = tempfile.mkdtemp()
    try:
        f = await client.download_media(m, file_name=os.path.join(tmp, "in"))
        wav = os.path.join(tmp, "out.wav"); convert_to_wav(f, wav)
        res = await recognize_song(wav)
        track = res.get("track") if res else None
        if not track: return await wait.edit("❌ Not recognized.")
        title, artist = track.get("title","?"), track.get("subtitle","?")
        yt_url, yt_title, yt_ch, thumb = youtube_search(f"{title} {artist}")
        kb = song_result_kbd(title, artist, yt_url)
        cap = f"🎵 *{title}*\n👤 _{artist}_"
        if thumb: await m.reply_photo(thumb, caption=cap, parse_mode="markdown", reply_markup=kb)
        else: await wait.edit(cap, parse_mode="markdown", reply_markup=kb)
    finally:
        SONG_STATE.pop(m.from_user.id, None)
        shutil.rmtree(tmp, ignore_errors=True)

@Client.on_message(filters.private & filters.text)
async def song_text(client: Client, m: Message):
    state = SONG_STATE.get(m.from_user.id)
    if not state: return
    query = m.text.strip(); SONG_STATE.pop(m.from_user.id, None)
    if state == "expect_search":
        yt_url, title, ch, thumb = youtube_search(query)
        if not yt_url: return await m.reply_text("❌ No results.")
        kb = song_result_kbd(title, ch, yt_url)
        cap = f"🔍 *{title}*\n👤 _{ch}_"
        if thumb: await m.reply_photo(thumb, caption=cap, parse_mode="markdown", reply_markup=kb)
        else: await m.reply_text(cap, parse_mode="markdown", reply_markup=kb)
    elif state == "expect_link":
        yt_url = query if "youtu" in query else None
        if not yt_url: return await m.reply_text("❌ Only YouTube links supported.")
        yt, title, ch, thumb = youtube_search(query)
        kb = song_result_kbd(title or "Song", ch or "", yt_url)
        await m.reply_text(f"🔗 {yt_url}", reply_markup=kb)
    elif state == "expect_lyrics":
        parts = query.split("-",1)
        artist, title = (parts[0].strip(), parts[1].strip()) if len(parts)==2 else ("", query)
        lyrics = await fetch_lyrics(artist, title)
        if lyrics:
            for c in split_chunks(lyrics): await m.reply_text(c)
        else:
            await m.reply_text(f"❌ Lyrics not found.\nTry: https://genius.com/search?q={quote_plus(query)}")

@Client.on_callback_query(filters.regex(r"^song\|result\|"))
async def song_result_cb(client: Client, cq: CallbackQuery):
    parts = cq.data.split("|")
    action = parts[2]
    if action == "yt":
        url = unquote_plus(parts[3])
        await cq.message.reply_text(f"▶️ {url}"); await cq.answer()
    elif action == "lyrics":
        t,a = unquote_plus(parts[3]).split("||")[0], unquote_plus(parts[3]).split("||")[1]
        lyrics = await fetch_lyrics(a, t)
        if lyrics: 
            for c in split_chunks(lyrics): await cq.message.reply_text(c)
        else: await cq.message.reply_text("❌ Lyrics not found."); await cq.answer()
    elif action == "mp3":
        title, artist = [unquote_plus(x) for x in parts[3].split("||")]
        yt_url, *_ = youtube_search(f"{title} {artist}")
        if not yt_url: return await cq.message.reply_text("❌ Couldn’t find YouTube audio.")
        tmp = tempfile.mkdtemp()
        try:
            mp3, t, auth = await download_mp3(yt_url, tmp)
            await cq.message.reply_audio(mp3, title=t, performer=auth)
        finally: shutil.rmtree(tmp, ignore_errors=True)
        await cq.answer()
      
