# pinterest.py
# Pinterest Plugin – V4.6 (Patched & Optimized)
# Developer: Neon 😎

import time
import random
import requests
from bs4 import BeautifulSoup
from pyrogram import Client, filters, errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto

# ---------------- CONFIG ---------------- #

# Using a mobile user agent often forces Pinterest to serve server-side HTML
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
}

MAX_IMAGES = 6
NSFW_DURATION = 600

# ---------------- STATE ---------------- #

NSFW_UNLOCK = {}      # chat_id -> expiry timestamp
ALBUM_TRACKER = {}    # control_msg_id -> album message IDs
QUERY_CACHE = {}      # small_id -> full_query_string (To fix 64-byte limit)

# ---------------- SCRAPER ---------------- #

def fetch_images(query: str | None, limit=MAX_IMAGES):
    try:
        url = (
            f"https://www.pinterest.com/search/pins/?q={query.replace(' ', '%20')}"
            if query else "https://www.pinterest.com/"
        )
        
        # Timeout added to prevent bot hanging
        r = requests.get(url, headers=HEADERS, timeout=8)
        soup = BeautifulSoup(r.text, "html.parser")

        imgs = []
        # Pinterest structure varies, this catches standard img tags
        for img in soup.find_all("img"):
            src = img.get("src")
            if src and "pinimg.com" in src:
                # Filter out tiny avatars/icons (usually 75x75)
                if "75x75" in src:
                    continue
                # Upgrade quality
                imgs.append(src.replace("236x", "736x").replace("564x", "736x"))

        imgs = list(set(imgs)) # Remove duplicates
        random.shuffle(imgs)
        return imgs[:limit]

    except Exception as e:
        print(f"[Pinterest Error] {e}") # Log error for debugging
        return []

# ---------------- HELPERS ---------------- #

def nsfw_remaining(chat_id: int) -> int:
    return max(0, int(NSFW_UNLOCK.get(chat_id, 0) - time.time()))

def nsfw_active(chat_id: int) -> bool:
    return nsfw_remaining(chat_id) > 0

def cache_query(query: str) -> str:
    """Hashes query to a short ID to fit in 64-byte callback limit"""
    if not query: return "trending"
    qid = str(hash(query))[-8:] # Last 8 chars of hash
    QUERY_CACHE[qid] = query
    return qid

def get_query(qid: str) -> str | None:
    if qid == "trending": return None
    return QUERY_CACHE.get(qid, None)

def build_buttons(chat_id: int, query: str | None):
    qid = cache_query(query)
    
    buttons = [
        [
            InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/MyselfNeon"),
            # Shortened callback data
            InlineKeyboardButton("🔄 Refresh", callback_data=f"pint_ref:{qid}")
        ]
    ]
    remaining = nsfw_remaining(chat_id)
    if remaining > 0:
        buttons.append([
            InlineKeyboardButton(f"🔞 NSFW ({remaining}s)", callback_data="pint_nsfw_btn")
        ])
    return InlineKeyboardMarkup(buttons)

async def cleanup_album(client, chat_id: int, control_msg_id: int):
    msg_ids = ALBUM_TRACKER.pop(control_msg_id, [])
    if not msg_ids: return
    try:
        await client.delete_messages(chat_id, msg_ids)
    except:
        pass

# ---------------- COMMANDS ---------------- #

@Client.on_message(filters.command("pint"))
async def pint_cmd(client, message):
    chat_id = message.chat.id
    query = " ".join(message.command[1:]).strip() or None

    if not nsfw_active(chat_id):
        if query and any(x in query.lower() for x in ["sex", "tits", "nude", "porn", "hentai"]):
            return await message.reply("🔒 **NSFW Locked.**\nUse `/pint_nsfw ON` to unlock.")

    status_msg = await message.reply("🔍 Searching...")
    
    images = fetch_images(query)
    if not images:
        return await status_msg.edit("⚠️ **No results found.**\nPinterest might be blocking the bot or the query is too obscure.")

    try:
        album = await client.send_media_group(
            chat_id,
            [InputMediaPhoto(i) for i in images]
        )
        await status_msg.delete() # Remove "Searching..."
    except errors.WebpageCurlFailed:
         return await status_msg.edit("⚠️ **Upload Failed.**\nTelegram couldn't fetch these image URLs.")
    except Exception as e:
         return await status_msg.edit(f"⚠️ Error: {e}")

    control = await client.send_message(
        chat_id,
        f"📌 **Pinterest**\n🔍 `{query or 'Trending'}`",
        reply_markup=build_buttons(chat_id, query),
        reply_to_message_id=album[0].id
    )

    ALBUM_TRACKER[control.id] = [m.id for m in album]

@Client.on_message(filters.command("pint_nsfw"))
async def pint_nsfw_toggle(_, message):
    if len(message.command) < 2:
        return await message.reply("Usage: `/pint_nsfw ON` or `/pint_nsfw OFF`")

    mode = message.command[1].upper()
    chat_id = message.chat.id

    if mode == "ON":
        NSFW_UNLOCK[chat_id] = time.time() + NSFW_DURATION
        await message.reply(f"😈 **NSFW Unlocked** for {NSFW_DURATION}s.")
    elif mode == "OFF":
        NSFW_UNLOCK.pop(chat_id, None)
        await message.reply("🛡️ **NSFW Locked.**")
    else:
        await message.reply("Invalid option. Use `ON` or `OFF`.")

# ---------------- CALLBACKS ---------------- #

@Client.on_callback_query(filters.regex("^pint_ref:"))
async def pint_refresh(client, cq):
    chat_id = cq.message.chat.id
    qid = cq.data.split(":", 1)[1]
    query = get_query(qid)

    # Note: If cache is cleared (bot restart), query might be None. 
    # Logic handles it as trending, which is acceptable fallback.

    await cleanup_album(client, chat_id, cq.message.id)

    if not nsfw_active(chat_id):
        NSFW_UNLOCK.pop(chat_id, None)

    try:
        images = fetch_images(query)
        if not images:
            return await cq.answer("⚠️ No new images found", show_alert=True)

        album = await client.send_media_group(
            chat_id,
            [InputMediaPhoto(i) for i in images]
        )
        ALBUM_TRACKER[cq.message.id] = [m.id for m in album]
        
        await cq.message.edit_reply_markup(reply_markup=build_buttons(chat_id, query))
        await cq.answer("🔄 Refreshed")
        
    except Exception as e:
        await cq.answer(f"Error: {str(e)[:50]}", show_alert=True)

@Client.on_callback_query(filters.regex("^pint_nsfw_btn$"))
async def pint_nsfw_btn(client, cq):
    chat_id = cq.message.chat.id

    if not nsfw_active(chat_id):
        NSFW_UNLOCK.pop(chat_id, None)
        await cleanup_album(client, chat_id, cq.message.id)
        await cq.message.edit_reply_markup(reply_markup=build_buttons(chat_id, None))
        return await cq.answer("🔒 Time's up! NSFW locked.", show_alert=True)

    await cleanup_album(client, chat_id, cq.message.id)

    # Specific NSFW query list to rotate
    nsfw_queries = ["aesthetic nude art", "boudoir photography", "artistic body", "model portrait"]
    target_query = random.choice(nsfw_queries)

    images = fetch_images(target_query)
    
    if images:
        album = await client.send_media_group(chat_id, [InputMediaPhoto(i) for i in images])
        ALBUM_TRACKER[cq.message.id] = [m.id for m in album]
        await cq.answer("🔞 NSFW loaded")
    else:
        await cq.answer("⚠️ Search failed", show_alert=True)

    await cq.message.edit_reply_markup(reply_markup=build_buttons(chat_id, None))
