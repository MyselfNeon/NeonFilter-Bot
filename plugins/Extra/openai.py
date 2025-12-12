from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from plugins.Extra.engine import ask_ai, reset_chat_history, get_usage_info, send_model_selection, set_user_model

# --- Command Handler for /openai ---

@Client.on_message(filters.command('openai'))
async def openai_ask(client, message):
    if len(message.command) == 1:
       return await message.reply_text("Please provide a prompt for the AI!")
    
    m = await message.reply_text("👀 Thinking...")
    await ask_ai(m, message)

# --- New Command Handlers ---

@Client.on_message(filters.command('reset'))
async def reset_command(client, message):
    """Clears the chat history."""
    m = await message.reply_text("⏳ Clearing history...")
    await reset_chat_history(m)

@Client.on_message(filters.command('usage'))
async def usage_command(client, message):
    """Shows current usage info and a link to the billing page."""
    m = await message.reply_text("📊 Fetching usage info...")
    await get_usage_info(m)

@Client.on_message(filters.command('model'))
async def model_command(client, message):
    """Opens the model selection keyboard."""
    m = await message.reply_text("🤖 Preparing model selection...")
    await send_model_selection(m)

# --- Callback Query Handler ---

@Client.on_callback_query(filters.regex(r'^setmodel_'))
async def model_callback_handler(client, callback_query: CallbackQuery):
    """Handles button clicks for model selection."""
    try:
        await set_user_model(callback_query)
        await callback_query.answer("Model updated successfully!")
    except Exception as e:
        await callback_query.answer(f"Error changing model: {e}", show_alert=True)