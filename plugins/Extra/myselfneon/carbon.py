# carbon_plugin.py
# Standalone Carbon plugin for Pyrogram
# Supports /carbon and /helpcarbon commands with optional flags

import html
import logging
from urllib.parse import quote_plus
from pyrogram import filters
from pyrogram.types import Message
import aiohttp

logger = logging.getLogger(__name__)

CARBON_ENDPOINTS = [
    "https://carbonara-42.vercel.app/api/cook?code=",
    "https://carbonara-42.herokuapp.com/api/cook?code=",
]

DEFAULTS = {
    "theme": "dracula",
    "fontSize": 16,
    "language": "auto",
}

def parse_flags(text: str):
    """Parse --flag=value style flags"""
    parts = text.strip().split()
    flags = {}
    remaining = []
    for p in parts:
        if p.startswith("--") and "=" in p:
            k, v = p[2:].split("=", 1)
            flags[k] = v
        else:
            remaining.append(p)
    return flags, " ".join(remaining)

async def fetch_carbon_image(code, theme=None, fontSize=None, language=None, bg=None):
    theme = theme or DEFAULTS["theme"]
    fontSize = fontSize or DEFAULTS["fontSize"]
    language = language or DEFAULTS["language"]
    safe_code = quote_plus(code)
    params = [f"theme={quote_plus(theme)}", f"fontFamily=Hack", f"fontSize={fontSize}"]
    if language != "auto":
        params.append(f"language={quote_plus(language)}")
    if bg:
        params.append(f"backgroundColor={quote_plus(bg)}")
    suffix = "&".join(params)

    async with aiohttp.ClientSession() as session:
        for base in CARBON_ENDPOINTS:
            url = base + safe_code
            sep = "&" if "?" in base else "?"
            url = f"{url}{sep}{suffix}" if suffix else url
            try:
                async with session.get(url, timeout=30) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        if data and len(data) > 100:
                            return data
                        else:
                            logger.warning("Carbon endpoint %s returned unexpected size %s", base, len(data) if data else 0)
            except Exception as e:
                logger.exception("Error fetching from %s: %s", base, e)
    return None

# ---- STANDALONE HANDLERS ----
def register(app):
    @app.on_message(filters.command("carbon") & ~filters.edited)
    async def carbon_handler(client, message: Message):
        if message.reply_to_message and (message.reply_to_message.text or message.reply_to_message.caption):
            raw_input = message.reply_to_message.text or message.reply_to_message.caption
        else:
            raw_input = message.text.partition(" ")[2].strip()
        if not raw_input:
            return await message.reply_text("Please reply to a message or pass the text. Example: /carbon print('hello')")

        flags, text = parse_flags(raw_input)
        if not text:
            text = raw_input

        theme = flags.get("theme") or DEFAULTS["theme"]
        fontSize = int(flags.get("fontSize", DEFAULTS["fontSize"]))
        language = flags.get("language") or DEFAULTS["language"]
        bg = flags.get("bg")

        if len(text) > 4000:
            return await message.reply_text("Text is too long (limit 4000 characters).")

        status = await message.reply_text("⏳ Generating carbon image...")

        code_payload = html.unescape(text)
        img_bytes = await fetch_carbon_image(code_payload, theme=theme, fontSize=fontSize, language=language, bg=bg)

        if not img_bytes:
            return await status.edit("❌ Failed to generate the carbon image. Try again later.")

        try:
            if len(img_bytes) > 5 * 1024 * 1024:
                await client.send_document(chat_id=message.chat.id, document=img_bytes, caption="Here is your carbon image.")
            else:
                await client.send_photo(chat_id=message.chat.id, photo=img_bytes, caption="Here is your carbon image.")
            await status.delete()
        except Exception as e:
            logger.exception("Error sending carbon image: %s", e)
            await status.edit(f"❌ Generated image but failed to send it. Error: {e}")

    @app.on_message(filters.command("helpcarbon") & ~filters.edited)
    async def help_carbon(client, message: Message):
        help_text = (
            "**/carbon** - Generate a Carbon-style code image.\n\n"
            "Usage:\n"
            "• Reply to a message with `/carbon`\n"
            "• Or send `/carbon your code here`\n\n"
            "Optional flags (space-separated, anywhere in text):\n"
            "• `--theme=dracula|monokai|one-light|dracula|nord` (default: dracula)\n"
            "• `--fontSize=NUMBER` (default: 16)\n"
            "• `--language=LANG` (default: auto)\n"
            "• `--bg=#HEX` or `rgba(r,g,b,a)` (background color)\n\n"
            "Example:\n"
            "`/carbon --theme=one-light --fontSize=14 print('Hello World!')`"
        )
        await message.reply_text(help_text)

# ---- AUTO-REGISTER ON IMPORT ----
try:
    app  # if 'app' exists in global scope
except NameError:
    pass  # do nothing
else:
    register(app)
    
