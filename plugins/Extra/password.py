import secrets
import string
import math
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Import ADMINS from info.py
from info import ADMINS

# In-memory settings storage. 
# Structure: {user_id: {'length': 12, 'upper': True, 'digits': True, 'symbols': True, 'ambiguous': False}}
USER_SETTINGS = {}

DEFAULT_SETTINGS = {
    'length': 14,
    'upper': True,
    'digits': True,
    'symbols': True,
    'ambiguous': False # If True, excludes l, 1, O, 0, etc.
}

# --- HELPER FUNCTIONS --- #

def get_settings(user_id):
    """Fetch user settings or return defaults."""
    if user_id not in USER_SETTINGS:
        USER_SETTINGS[user_id] = DEFAULT_SETTINGS.copy()
    return USER_SETTINGS[user_id]

def calculate_entropy(password, pool_size):
    """Calculates password entropy in bits."""
    if not password: return 0
    return len(password) * math.log2(pool_size)

def get_strength_bar(entropy):
    """Returns a visual strength bar based on entropy."""
    if entropy < 28:
        return "🟥⬜️⬜️⬜️⬜️ (Very Weak)"
    elif entropy < 36:
        return "🟥🟥⬜️⬜️⬜️ (Weak)"
    elif entropy < 60:
        return "🟨🟨🟨⬜️⬜️ (Medium)"
    elif entropy < 128:
        return "🟩🟩🟩🟩⬜️ (Strong)"
    else:
        return "🟩🟩🟩🟩🟩 (Unbreakable)"

def generate_secure_password(settings):
    """Generates a cryptographically secure password based on settings."""
    chars = string.ascii_lowercase
    pool_size = 26

    if settings['upper']:
        chars += string.ascii_uppercase
        pool_size += 26
    if settings['digits']:
        chars += string.digits
        pool_size += 10
    if settings['symbols']:
        chars += "!@#$%^&*()_+-=[]{}|;:,.<>?/`~"
        pool_size += 30
    
    # Remove ambiguous characters if requested
    if settings['ambiguous']:
        ambiguous_chars = "1lI0O"
        table = str.maketrans('', '', ambiguous_chars)
        chars = chars.translate(table)
        pool_size = max(1, pool_size - len(ambiguous_chars)) # Prevent 0 pool

    # Fallback if user disables everything
    if not chars:
        chars = string.ascii_lowercase
        pool_size = 26

    # Generate secure password
    password = "".join(secrets.choice(chars) for _ in range(settings['length']))
    
    return password, pool_size

def build_keyboard(user_id, settings):
    """Creates the interactive control panel."""
    
    # State markers
    s_upper = "✅" if settings['upper'] else "❌"
    s_digits = "✅" if settings['digits'] else "❌"
    s_symbols = "✅" if settings['symbols'] else "❌"
    s_ambig = "🚫" if settings['ambiguous'] else "👁️" # Eye icon means visible/allowed

    keyboard = [
        [
            InlineKeyboardButton(f"A-Z {s_upper}", callback_data=f"pw_toggle_upper_{user_id}"),
            InlineKeyboardButton(f"0-9 {s_digits}", callback_data=f"pw_toggle_digits_{user_id}"),
            InlineKeyboardButton(f"@#$ {s_symbols}", callback_data=f"pw_toggle_symbols_{user_id}")
        ],
        [
            InlineKeyboardButton(f"No Confusing Chars {s_ambig}", callback_data=f"pw_toggle_ambig_{user_id}")
        ],
        [
            InlineKeyboardButton("➖", callback_data=f"pw_len_down_{user_id}"),
            InlineKeyboardButton(f"📏 Length: {settings['length']}", callback_data="pw_noop"),
            InlineKeyboardButton("➕", callback_data=f"pw_len_up_{user_id}")
        ],
        [
            InlineKeyboardButton("🔄 Gᴇɴᴇʀᴀᴛᴇ Nᴇᴡ", callback_data=f"pw_refresh_{user_id}")
        ],
        [
            InlineKeyboardButton("🗑️ Cʟᴏsᴇ", callback_data=f"pw_close_{user_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- COMMAND HANDLER --- #

@Client.on_message(filters.command(["genpassword", "genpw", "pw"]))
async def password_command(bot, message):
    # Optional: Uncomment the next 2 lines if you ONLY want ADMINS to use this command
    # if message.from_user.id not in ADMINS:
    #     return

    user_id = message.from_user.id
    settings = get_settings(user_id)
    
    # Generate initial password
    password, pool_size = generate_secure_password(settings)
    entropy = calculate_entropy(password, pool_size)
    strength_text = get_strength_bar(entropy)

    txt = (
        f"<b>🔐 Sᴇᴄᴜʀᴇ Pᴀssᴡᴏʀᴅ Gᴇɴᴇʀᴀᴛᴏʀ</b>\n\n"
        f"<code>{password}</code>\n\n"
        f"📊 <b>Sᴛʀᴇɴɢᴛʜ:</b> {strength_text}\n"
        f"🔢 <b>Eɴᴛʀᴏᴘʏ:</b> {int(entropy)} bits\n"
        f"👇 <i>Customize your settings below:</i>"
    )

    await message.reply_text(
        text=txt,
        reply_markup=build_keyboard(user_id, settings),
        parse_mode=enums.ParseMode.HTML
    )

# --- CALLBACK HANDLER --- #

@Client.on_callback_query(filters.regex(r"^pw_"))
async def password_callback(bot, query: CallbackQuery):
    data = query.data.split("_")
    action = data[1]
    
    # Handle "noop" (clicking the length display)
    if action == "noop":
        await query.answer("Use + or - to change length.")
        return

    # Extract the ID of the user who owns this specific panel
    try:
        owner_id = int(data[-1])
    except ValueError:
        await query.answer("Error: Invalid data.", show_alert=True)
        return

    # Security Check: Ensure only the person who started the command can use the buttons
    # If you want ADMINS to be able to control anyone's panel, you can add `and query.from_user.id not in ADMINS`
    if query.from_user.id != owner_id:
        await query.answer("⚠️ This is not your control panel.", show_alert=True)
        return

    # Fetch settings
    settings = get_settings(owner_id)

    # Process Actions
    if action == "refresh":
        pass # Just regenerate at the end
    
    elif action == "close":
        await query.message.delete()
        return

    elif action == "toggle":
        setting_key = data[2] # upper, digits, symbols, ambig
        settings[setting_key] = not settings[setting_key]
        
        # Ensure at least one character set is active
        if not any([settings['upper'], settings['digits'], settings['symbols'], not settings['ambiguous']]):
             settings['upper'] = True # Re-enable upper if everything is off
             await query.answer("⚠️ You must have at least one character type!", show_alert=True)

    elif action == "len":
        direction = data[2] # up, down
        if direction == "up" and settings['length'] < 64:
            settings['length'] += 1
        elif direction == "down" and settings['length'] > 4:
            settings['length'] -= 1
        else:
            await query.answer("Limit reached (4-64 chars)")
            return

    # Save settings 
    USER_SETTINGS[owner_id] = settings

    # Regenerate Password with new settings
    password, pool_size = generate_secure_password(settings)
    entropy = calculate_entropy(password, pool_size)
    strength_text = get_strength_bar(entropy)

    txt = (
        f"<b>🔐 Sᴇᴄᴜʀᴇ Pᴀssᴡᴏʀᴅ Gᴇɴᴇʀᴀᴛᴏʀ</b>\n\n"
        f"<code>{password}</code>\n\n"
        f"📊 <b>Sᴛʀᴇɴɢᴛʜ:</b> {strength_text}\n"
        f"🔢 <b>Eɴᴛʀᴏᴘʏ:</b> {int(entropy)} bits\n"
        f"👇 <i>Customize your settings below:</i>"
    )

    try:
        await query.message.edit_text(
            text=txt,
            reply_markup=build_keyboard(owner_id, settings),
            parse_mode=enums.ParseMode.HTML
        )
    except Exception:
        # Avoid error if message content is identical (e.g. clicking refresh and getting same random string, unlikely but possible)
        pass
        
