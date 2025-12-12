from pyrogram import Client, filters
from plugins.Extra.engine import ask_ai

@Client.on_message(filters.command('openai'))
async def openai_ask(client, message):
    """
    Pyrogram command handler for the /openai command.
    """
    
    # 1. Check if input was provided
    if len(message.command) == 1:
       return await message.reply_text("Please provide a prompt for the AI!")
    
    # 2. Send a placeholder message and store the message object (m)
    m = await message.reply_text("👀 Thinking...")
    
    # 3. Call the asynchronous AI processing function
    await ask_ai(m, message)