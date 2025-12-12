import openai
from openai import AsyncOpenAI
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from info import OPENAI_API_KEY 

# --- Global State and Configuration ---
AI_ENABLED = bool(OPENAI_API_KEY)
client = AsyncOpenAI(api_key=OPENAI_API_KEY) if AI_ENABLED else None
print(f"AI Status: {'Enabled' if AI_ENABLED else 'Disabled'}")

# Global Dictionary to store chat history: {user_id: [{'role': 'user', 'content': '...'}]}
CHAT_HISTORY = {} 

# Default Model and Token Limit (can be changed by user via command)
DEFAULT_MODEL = "gpt-3.5-turbo"
DEFAULT_MAX_TOKENS = 100
MODEL_CONFIG = {
    # Friendly Name: [OpenAI Model ID, Tokens per call]
    "Fast Chat": ["gpt-3.5-turbo", 100],
    "Creative Chat": ["gpt-4o", 200], # Assuming access to GPT-4o for a premium feel
    "Quick Q&A": ["gpt-3.5-turbo-instruct", 80],
}
USER_SETTINGS = {} # {user_id: {"model": "gpt-3.5-turbo", "max_tokens": 100}}


# --- Helper Functions ---

def get_user_settings(user_id):
    """Retrieves or creates default settings for a user."""
    if user_id not in USER_SETTINGS:
        USER_SETTINGS[user_id] = {"model": DEFAULT_MODEL, "max_tokens": DEFAULT_MAX_TOKENS}
    return USER_SETTINGS[user_id]

def get_chat_messages(user_id, new_prompt):
    """Retrieves chat history and appends the new prompt."""
    if user_id not in CHAT_HISTORY:
        CHAT_HISTORY[user_id] = []
    
    # Get current history (up to last 5 turns to prevent massive tokens)
    history = CHAT_HISTORY[user_id][-10:]
    
    # Append the new user prompt
    history.append({"role": "user", "content": new_prompt})
    return history

def update_chat_history(user_id, prompt, response):
    """Updates the chat history with the user's prompt and the AI's response."""
    if user_id not in CHAT_HISTORY:
        CHAT_HISTORY[user_id] = []
        
    # Append the user's message
    CHAT_HISTORY[user_id].append({"role": "user", "content": prompt})
    # Append the assistant's reply
    CHAT_HISTORY[user_id].append({"role": "assistant", "content": response})


async def ai(user_id, query):
    """Asynchronously queries the OpenAI Chat Completions API with context."""
    if not AI_ENABLED:
        return "🚫 AI is disabled. Please set the OPENAI_API_KEY."

    settings = get_user_settings(user_id)
    messages = get_chat_messages(user_id, query)

    try:
        response = await client.chat.completions.create(
            model=settings["model"],
            messages=messages,
            max_tokens=settings["max_tokens"],
            n=1,
            temperature=0.7 # Lowered temperature slightly for better consistency
        )
        
        # Extract the content
        content = response.choices[0].message.content.strip()
        
        # Update history
        update_chat_history(user_id, query, content)
        
        return content

    except Exception as e:
        error_message = f"OpenAI API Error: {e}"
        print(error_message)
        return f"Sorry, the AI encountered an error: {e}"


async def ask_ai(m, message):
    """Handles the Telegram interaction and checks the AI status."""
    if not AI_ENABLED:
        await m.edit("🚫 **AI is disabled.** Please set the `OPENAI_API_KEY` environment variable to enable this command.")
        return
        
    try:
        user_id = message.from_user.id
        question = message.text.split(" ", 1)[1]
        
        # Generate response using the async OpenAI function
        response = await ai(user_id, question)
        
        await m.edit(f"**🤖 AI Model:** `{get_user_settings(user_id)['model']}`\n\n{response}")
        
    except IndexError:
        await m.edit("Please provide a question after the command.")
        
    except Exception as e:
        error_message = f"An error occurred: {type(e).__name__}: {e}"
        await m.edit(error_message)

# --- New Command Handlers ---

async def reset_chat_history(m):
    """Clears the chat history for a user."""
    user_id = m.from_user.id
    if user_id in CHAT_HISTORY:
        del CHAT_HISTORY[user_id]
        await m.edit("🗑️ **Chat history cleared!** Starting a new conversation.")
    else:
        await m.edit("🤷 No active chat history found for you.")
        
async def get_usage_info(m):
    """Placeholder for checking API usage (Requires custom billing integration)."""
    
    # NOTE: Checking API usage directly is complex as OpenAI doesn't have a simple 
    # API endpoint for 'remaining quota'. This must rely on external monitoring or a dedicated webhook.
    
    # For now, we provide general information and a link.
    history_length = len(CHAT_HISTORY.get(m.from_user.id, []))
    
    text = (
        "📊 **AI Status and Usage**\n"
        f"  - **Feature Status:** {'✅ Enabled' if AI_ENABLED else '❌ Disabled'}\n"
        f"  - **Current Model:** `{get_user_settings(m.from_user.id)['model']}`\n"
        f"  - **Max Tokens:** `{get_user_settings(m.from_user.id)['max_tokens']}`\n"
        f"  - **Chat History Length:** `{history_length // 2}` turns\n\n"
        "To check your **remaining quota/billing**, please visit the official OpenAI dashboard."
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("OpenAI Billing Dashboard", url="https://platform.openai.com/account/billing/overview")]
    ])
    
    await m.edit(text, reply_markup=keyboard)


async def get_model_selection_keyboard():
    """Generates the inline keyboard for model selection."""
    buttons = []
    row = []
    for friendly_name in MODEL_CONFIG:
        callback_data = f"setmodel_{MODEL_CONFIG[friendly_name][0]}_{MODEL_CONFIG[friendly_name][1]}"
        row.append(InlineKeyboardButton(friendly_name, callback_data=callback_data))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
        
    return InlineKeyboardMarkup(buttons)

async def send_model_selection(m):
    """Sends the message with model selection buttons."""
    keyboard = await get_model_selection_keyboard()
    await m.edit("🤖 **Select AI Model**\n\nChoose a model to change the AI's speed and creativity. This will reset your current chat history.", reply_markup=keyboard)


async def set_user_model(callback_query):
    """Handles the callback query to set the user's model."""
    user_id = callback_query.from_user.id
    data = callback_query.data.split('_') # e.g., ['setmodel', 'gpt-3.5-turbo', '100']
    
    if len(data) != 3 or data[0] != "setmodel":
        return
        
    model_id = data[1]
    max_tokens = int(data[2])
    
    # Update settings
    USER_SETTINGS[user_id] = {"model": model_id, "max_tokens": max_tokens}
    
    # Clear chat history as model change often breaks context
    if user_id in CHAT_HISTORY:
        del CHAT_HISTORY[user_id]
        
    await callback_query.message.edit_text(
        f"✅ **Model Updated!**\n"
        f"  - **Model:** `{model_id}`\n"
        f"  - **Max Response:** `{max_tokens}` tokens\n"
        f"  - **History:** Cleared.\n\n"
        f"You can now use the `/openai` command."
    )