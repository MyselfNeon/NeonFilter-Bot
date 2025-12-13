import openai
from openai import AsyncOpenAI
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from info import OPENAI_API_KEY 

# --- Global State ---
# We use a try-except block here to prevent crashes if the key is invalid format
try:
    AI_ENABLED = bool(OPENAI_API_KEY) and len(OPENAI_API_KEY) > 10
    client = AsyncOpenAI(api_key=OPENAI_API_KEY) if AI_ENABLED else None
except Exception:
    AI_ENABLED = False
    client = None

print(f"AI Status: {'Enabled' if AI_ENABLED else 'Disabled'}")

CHAT_HISTORY = {} 

# Default Settings
DEFAULT_MODEL = "gpt-3.5-turbo"
DEFAULT_MAX_TOKENS = 100
USER_SETTINGS = {} 

MODEL_CONFIG = {
    "Fast Chat": ["gpt-3.5-turbo", 100],
    "Creative Chat": ["gpt-4-turbo", 200], 
    "Quick Q&A": ["gpt-3.5-turbo-instruct", 80],
}

# --- Helper Functions ---

def get_user_id(message):
    """Safely extract user ID, handling anonymous admins."""
    if message.from_user:
        return message.from_user.id
    if message.sender_chat:
        return message.sender_chat.id
    return 0 # Fallback

def get_user_settings(user_id):
    if user_id not in USER_SETTINGS:
        USER_SETTINGS[user_id] = {"model": DEFAULT_MODEL, "max_tokens": DEFAULT_MAX_TOKENS}
    return USER_SETTINGS[user_id]

def get_chat_messages(user_id, new_prompt):
    if user_id not in CHAT_HISTORY:
        CHAT_HISTORY[user_id] = []
    history = CHAT_HISTORY[user_id][-6:] # Keep last 6 messages (3 turns)
    history.append({"role": "user", "content": new_prompt})
    return history

def update_chat_history(user_id, prompt, response):
    if user_id not in CHAT_HISTORY:
        CHAT_HISTORY[user_id] = []
    CHAT_HISTORY[user_id].append({"role": "user", "content": prompt})
    CHAT_HISTORY[user_id].append({"role": "assistant", "content": response})

# --- Main AI Function ---

async def ai(user_id, query):
    if not AI_ENABLED or not client:
        return "🚫 AI is disabled. Please check your OPENAI_API_KEY in info.py."

    settings = get_user_settings(user_id)
    messages = get_chat_messages(user_id, query)

    try:
        response = await client.chat.completions.create(
            model=settings["model"],
            messages=messages,
            max_tokens=settings["max_tokens"],
            n=1,
            temperature=0.7
        )
        content = response.choices[0].message.content.strip()
        update_chat_history(user_id, query, content)
        return content

    except openai.RateLimitError:
        return "❌ **Quota Exceeded (429):** You have run out of OpenAI credits. Please add $5 to your OpenAI billing balance."
    except openai.AuthenticationError:
        return "❌ **Invalid Key:** Your API key is incorrect. Please check info.py."
    except Exception as e:
        print(f"OpenAI Error: {e}")
        return f"⚠️ **Error:** {e}"

# --- Command Logic ---

async def ask_ai(m, message):
    try:
        user_id = get_user_id(message)
        if len(message.command) < 2:
            await m.edit("👋 Hi! asking me something.\nExample: `/openai How are you?`")
            return

        question = message.text.split(" ", 1)[1]
        response = await ai(user_id, question)
        
        # Display the result
        model_name = get_user_settings(user_id)['model']
        await m.edit(f"**🤖 AI ({model_name}):**\n\n{response}")
        
    except Exception as e:
        await m.edit(f"❌ Error in ask_ai: {e}")

async def reset_chat_history(m):
    try:
        user_id = get_user_id(m)
        if user_id in CHAT_HISTORY:
            del CHAT_HISTORY[user_id]
            await m.edit("🗑️ **Memory Wiped!** I have forgotten our previous conversation.")
        else:
            await m.edit("✨ My memory was already empty.")
    except Exception as e:
        await m.edit(f"❌ Error resetting: {e}")

async def get_usage_info(m):
    try:
        user_id = get_user_id(m)
        history_count = len(CHAT_HISTORY.get(user_id, []))
        settings = get_user_settings(user_id)
        
        text = (
            "📊 **AI Status Panel**\n"
            f"🔹 **System Status:** {'✅ Online' if AI_ENABLED else '❌ Offline (Key Missing)'}\n"
            f"🔹 **Your Model:** `{settings['model']}`\n"
            f"🔹 **Conversation Depth:** `{history_count // 2}` turns\n\n"
            "💡 *Note: If you see Error 429, you must add prepaid credits to your OpenAI account.*"
        )
        
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("💳 Check Billing", url="https://platform.openai.com/account/billing/overview")]])
        await m.edit(text, reply_markup=btn)
    except Exception as e:
        await m.edit(f"❌ Error getting usage: {e}")

async def send_model_selection(m):
    try:
        buttons = []
        row = []
        for name, data in MODEL_CONFIG.items():
            # data[0] is model id, data[1] is max tokens
            row.append(InlineKeyboardButton(name, callback_data=f"setmodel_{data[0]}_{data[1]}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row: buttons.append(row)
        
        await m.edit("⚙️ **Select AI Personality:**", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await m.edit(f"❌ Error showing models: {e}")

async def set_user_model(callback_query):
    user_id = callback_query.from_user.id
    data = callback_query.data.split('_')
    model_id = data[1]
    tokens = int(data[2])
    
    USER_SETTINGS[user_id] = {"model": model_id, "max_tokens": tokens}
    if user_id in CHAT_HISTORY:
        del CHAT_HISTORY[user_id]
        
    await callback_query.message.edit_text(f"✅ **Model Switched to:** `{model_id}`\n\nMemory has been reset.")
