from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from plugins.Extra.engine import ask_ai, reset_chat_history, send_model_selection, set_user_model

# 1. Main Chat Command (Aliases: /gemini, /ai, /ask)
@Client.on_message(filters.command(['gemini', 'ai', 'ask', 'openai']))
async def gemini_handler(client, message):
    m = await message.reply_text("✨ Initializing...")
    await ask_ai(m, message)

# 2. Reset Command
@Client.on_message(filters.command(['reset', 'clear']))
async def reset_handler(client, message):
    m = await message.reply_text("⏳ Processing...")
    await reset_chat_history(m)

# 3. Model Selector
@Client.on_message(filters.command(['model', 'models']))
async def model_handler(client, message):
    m = await message.reply_text("⚙️ Loading models...")
    await send_model_selection(m)

# 4. Callback for Model Buttons
@Client.on_callback_query(filters.regex(r'^setgemini_'))
async def gemini_callback_handler(client, callback_query: CallbackQuery):
    try:
        await set_user_model(callback_query)
    except Exception as e:
        await callback_query.answer(f"Error: {e}", show_alert=True)
