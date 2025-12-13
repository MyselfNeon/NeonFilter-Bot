from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from plugins.Extra.engine import ask_ai, reset_chat_history, send_model_selection, set_user_model

# 1. Main Chat Command (Aliases: /gemini, /ai, /ask)
@Client.on_message(filters.command(['gemini', 'ai', 'ask']))
async def gemini_handler(client, message):
    # Send a placeholder message first
    m = await message.reply_text("✨ Initializing Gemini...")
    # Pass the placeholder 'm' and the original 'message' to the engine
    await ask_ai(m, message)

# 2. Reset Command - Clears context/history
@Client.on_message(filters.command(['reset', 'clear']))
async def reset_handler(client, message):
    m = await message.reply_text("⏳ Processing request...")
    await reset_chat_history(m)

# 3. Model Selector - Switch between Flash/Pro
@Client.on_message(filters.command(['model', 'models']))
async def model_handler(client, message):
    m = await message.reply_text("⚙️ Loading models...")
    await send_model_selection(m)

# 4. Callback Handler for Model Buttons
# Listens for any callback data starting with "setgemini_"
@Client.on_callback_query(filters.regex(r'^setgemini_'))
async def gemini_callback_handler(client, callback_query: CallbackQuery):
    try:
        await set_user_model(callback_query)
    except Exception as e:
        await callback_query.answer(f"Error: {e}", show_alert=True)
