import asyncio
import traceback
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from telethon import TelegramClient
from telethon.sessions import StringSession

# --- ⚠️ IMPORTANT: CHANGE THIS IMPORT ---
# Import your existing Pyrogram 'app' client here.
# If you are using Smart Plugins, you might not need this if you adjust the decorators.
try:
    from MyselfNeon import app  # Old import (Removed)
except ImportError:
    # REPLACE 'YOUR_MAIN_FILE' WITH THE FILE WHERE YOU DEFINE app = Client(...)
    # Example: from main import app
    pass 

# Error Imports
from pyrogram.errors import (
    ApiIdInvalid, PhoneNumberInvalid, PhoneCodeInvalid, PhoneCodeExpired,
    SessionPasswordNeeded, PasswordHashInvalid
)
from telethon.errors import (
    ApiIdInvalidError, PhoneNumberInvalidError, PhoneCodeInvalidError,
    PhoneCodeExpiredError, SessionPasswordNeededError, PasswordHashInvalidError
)

# ==================================================================
# 1. UI & CONSTANTS
# ==================================================================
ASK_QUES = "**__Choose The String Which You Want to Generate__ ⬇️**"
BUTTONS = [
    [InlineKeyboardButton("Tᴇʟᴇᴛʜᴏɴ 🤖", callback_data="gen_telethon"),
     InlineKeyboardButton("Pʏʀᴏɢʀᴀᴍ 🐍", callback_data="gen_pyrogram")],
    [InlineKeyboardButton("Tᴇʟᴇᴛʜᴏɴ Bᴏᴛ", callback_data="gen_telethon_bot"),
     InlineKeyboardButton("Pʏʀᴏɢʀᴀᴍ Bᴏᴛ", callback_data="gen_pyrogram_bot")]
]

# ==================================================================
# 2. CUSTOM LISTENER (Strict 30s Timeout & Auto-Delete)
# ==================================================================
RESPONSE_WAITERS = {}

@app.on_message(filters.text & filters.private & ~filters.bot, group=-100)
async def await_response_watcher(_, message: Message):
    """Watches for user replies to specific questions."""
    user_id = message.from_user.id
    if user_id in RESPONSE_WAITERS:
        future = RESPONSE_WAITERS[user_id]
        if not future.done():
            future.set_result(message)
            message.stop_propagation()

async def delete_later(message, delay=5):
    """
    Safety feature: Deletes sensitive inputs (API ID, Hash, Number) 
    after the specified delay to protect user privacy.
    """
    await asyncio.sleep(delay)
    try: 
        await message.delete()
    except: 
        pass

async def ask_strict(bot, user_id, text, timeout=30):
    """
    Asks a question with a strict 30s timeout.
    Auto-deletes the USER'S response after 5 seconds.
    """
    try:
        sent = await bot.send_message(user_id, text)
        future = asyncio.Future()
        RESPONSE_WAITERS[user_id] = future
        
        message = await asyncio.wait_for(future, timeout=timeout)
        
        # 🛡️ SECURITY: Auto-delete the user's sensitive input after 5s
        asyncio.create_task(delete_later(message, 5))
        return message
    except asyncio.TimeoutError:
        return None
    finally:
        RESPONSE_WAITERS.pop(user_id, None)

# ==================================================================
# 3. HANDLERS (Command & Callback)
# ==================================================================

@app.on_message(filters.private & filters.command(["gen", "generate", "session"]))
async def gen_command(client, message):
    await message.reply(ASK_QUES, reply_markup=InlineKeyboardMarkup(BUTTONS))

@app.on_callback_query(filters.regex(r"^gen_"))
async def callbacks(bot, callback_query):
    query = callback_query.data
    user_id = callback_query.from_user.id

    # Cleanup previous menu
    try: await callback_query.message.delete()
    except: pass

    if query == "generate":
        await bot.send_message(user_id, ASK_QUES, reply_markup=InlineKeyboardMarkup(BUTTONS))
        return

    # Determine Type
    telethon = "telethon" in query
    is_bot = "bot" in query
    
    try:
        if query == "gen_pyrogram":
            await generate_session(bot, user_id)
        elif query == "gen_pyrogram_bot":
            await generate_session(bot, user_id, is_bot=True)
        elif query == "gen_telethon_bot":
            await generate_session(bot, user_id, telethon=True, is_bot=True)
        elif query == "gen_telethon":
            await generate_session(bot, user_id, telethon=True)
    except Exception as e:
        print(traceback.format_exc())
        await bot.send_message(user_id, f"**Error:** `{e}`")

# ==================================================================
# 4. MAIN GENERATION LOGIC
# ==================================================================
async def generate_session(bot: Client, user_id: int, telethon=False, is_bot: bool = False):
    
    ty = "Tᴇʟᴇᴛʜᴏɴ" if telethon else "Pʏʀᴏɢʀᴀᴍ"
    if is_bot: ty += " Bᴏᴛ"
    
    await bot.send_message(user_id, f"**__Starting {ty} Session Generator...__**\n⚠️ __You have 30s per step.__")

    # --- 1. API ID ---
    api_id_msg = await ask_strict(bot, user_id, "**__Send Your `API_ID`__**\n__(Send /skip to use Official Keys)__")
    if not api_id_msg or "/cancel" in api_id_msg.text: 
        return await bot.send_message(user_id, "❌ **Cancelled.**")
    
    if "/skip" in api_id_msg.text:
        # OFFICIAL TELEGRAM DESKTOP KEYS (Prevents common OTP issues)
        api_id = 2040
        api_hash = "b18441a1ff607e10a989891a5462e627"
    else:
        try:
            api_id = int(api_id_msg.text)
        except ValueError:
            return await bot.send_message(user_id, "❌ **API ID must be a number!**")
        
        api_hash_msg = await ask_strict(bot, user_id, "**__Send Your `API_HASH`__**")
        if not api_hash_msg: return await bot.send_message(user_id, "❌ **Timeout.**")
        api_hash = api_hash_msg.text

    # --- 2. PHONE NUMBER ---
    t = "**__Send Phone Number__**\nExample: `+919876543210`" if not is_bot else "**__Send Bot Token__**"
    phone_msg = await ask_strict(bot, user_id, t)
    if not phone_msg: return await bot.send_message(user_id, "❌ **Timeout.**")
    phone_number = phone_msg.text

    await bot.send_message(user_id, "**__Connecting to Telegram...__**")

    # --- 3. CONNECT CLIENT ---
    if telethon:
        client = TelegramClient(StringSession(), api_id, api_hash)
    elif is_bot:
        client = Client(name="bot", api_id=api_id, api_hash=api_hash, bot_token=phone_number, in_memory=True)
    else:
        # DEVICE SPOOFING: Pretend to be Samsung S21 Ultra to avoid bans
        client = Client(
            name="user", 
            api_id=api_id, 
            api_hash=api_hash, 
            in_memory=True,
            device_model="Samsung SM-G998B", 
            system_version="Android 12",
            app_version="8.9.3",
            lang_code="en"
        )

    await client.connect()

    try:
        code = None
        if not is_bot:
            if telethon:
                code = await client.send_code_request(phone_number)
            else:
                code = await client.send_code(phone_number)
    except (ApiIdInvalid, ApiIdInvalidError):
        return await bot.send_message(user_id, "❌ **API ID/Hash Invalid.**")
    except (PhoneNumberInvalid, PhoneNumberInvalidError):
        return await bot.send_message(user_id, "❌ **Phone Number Invalid.**")
    except Exception as e:
        return await bot.send_message(user_id, f"❌ **Error:** {e}")

    # --- 4. OTP INPUT ---
    if not is_bot:
        otp_msg = await ask_strict(bot, user_id, "✅ **OTP Sent!**\nCheck **Telegram App**.\n\n**Enter OTP:** `1 2 3 4 5`")
        if not otp_msg: return await bot.send_message(user_id, "❌ **Timeout.**")
        
        phone_code = otp_msg.text.replace(" ", "")

        try:
            if telethon:
                await client.sign_in(phone_number, phone_code)
            else:
                await client.sign_in(phone_number, code.phone_code_hash, phone_code)
        except (PhoneCodeInvalid, PhoneCodeInvalidError):
            return await bot.send_message(user_id, "❌ **Wrong OTP.**")
        except (PhoneCodeExpired, PhoneCodeExpiredError):
            return await bot.send_message(user_id, "❌ **OTP Expired.**")
        except (SessionPasswordNeeded, SessionPasswordNeededError):
            pwd_msg = await ask_strict(bot, user_id, "⚠️ **2FA Password Required:**")
            if not pwd_msg: return await bot.send_message(user_id, "❌ **Timeout.**")
            
            try:
                if telethon:
                    await client.sign_in(password=pwd_msg.text)
                else:
                    await client.check_password(password=pwd_msg.text)
            except (PasswordHashInvalid, PasswordHashInvalidError):
                return await bot.send_message(user_id, "❌ **Wrong Password.**")
    else:
        if telethon:
            await client.start(bot_token=phone_number)
        else:
            await client.sign_in_bot(phone_number)

    # --- 5. EXPORT ---
    if telethon:
        string_session = client.session.save()
    else:
        string_session = await client.export_session_string()

    text = f"**__Your {ty} Session__**\n\n`{string_session}`\n\n**__Generated By @NeonFiles__**"
    
    try:
        await client.send_message("me", text)
        await bot.send_message(user_id, "✅ **Success!**\nString sent to your **Saved Messages**.")
    except Exception:
        await bot.send_message(user_id, text)

    await client.disconnect()
