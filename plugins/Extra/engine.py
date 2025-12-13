import warnings
# Silence the "Python 3.10 support" warning to keep logs clean
warnings.filterwarnings("ignore", category=FutureWarning)

import google.generativeai as genai
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from info import GEMINI_API_KEY

# ==========================================
# ⚙️ CONFIGURATION & SETUP
# ==========================================
AI_ENABLED = False

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        AI_ENABLED = True
        print("✅ Google Gemini AI Enabled")
    except Exception as e:
        print(f"❌ Gemini Configuration Error: {e}")
else:
    print("⚠️ GEMINI_API_KEY missing in info.py. AI commands will be disabled.")

# Global Chat Storage
USER_CHATS = {}

# Model Config: Use 'gemini-pro' as it is the most stable for your version
MODEL_CONFIG = {
    "Standard (Pro)": "gemini-pro",
    "Fast (Flash)": "gemini-pro", 
}
USER_MODELS = {} 

# ==========================================
# 🛠️ HELPER FUNCTIONS
# ==========================================

def get_user_model_name(user_id):
    return USER_MODELS.get(user_id, "gemini-pro")

def get_chat_session(user_id):
    if user_id not in USER_CHATS:
        model_name = get_user_model_name(user_id)
        try:
            model = genai.GenerativeModel(model_name)
            USER_CHATS[user_id] = model.start_chat(history=[])
        except Exception as e:
            # Fallback if specific model fails
            print(f"⚠️ Model error: {e}, falling back to pro.")
            fallback = genai.GenerativeModel("gemini-pro")
            USER_CHATS[user_id] = fallback.start_chat(history=[])
    return USER_CHATS[user_id]

# ==========================================
# 🧠 MAIN AI LOGIC
# ==========================================

async def ai(user_id, query):
    if not AI_ENABLED:
        return "🚫 AI is disabled. Please add `GEMINI_API_KEY` to `info.py`."

    try:
        chat = get_chat_session(user_id)
        response = await chat.send_message_async(query)
        return response.text

    except Exception as e:
        error_msg = str(e).lower()
        if "safety" in error_msg:
            return "⚠️ **Safety Block:** I cannot answer this query due to safety filters."
        return f"⚠️ **Gemini Error:** {e}"

# ==========================================
# 🎮 COMMAND HANDLERS
# ==========================================

async def ask_ai(m, message):
    try:
        if len(message.command) < 2:
            await m.edit("👋 **Hello! I am Gemini.**\n\nAsk me anything: `/gemini How are you?`")
            return

        user_id = message.from_user.id
        question = message.text.split(" ", 1)[1]
        
        await m.edit("👀 **Thinking...**")
        response = await ai(user_id, question)
        
        model_label = "Pro" if "pro" in get_user_model_name(user_id) else "Flash"
        await m.edit(f"**♊ Gemini ({model_label}):**\n\n{response}")
        
    except Exception as e:
        await m.edit(f"❌ **Error:** {e}")

async def reset_chat_history(m):
    user_id = m.from_user.id
    if user_id in USER_CHATS:
        del USER_CHATS[user_id]
        await m.edit("🗑️ **Memory Wiped!**")
    else:
        await m.edit("✨ Memory is already clean.")

async def send_model_selection(m):
    buttons = []
    for friendly_name, model_id in MODEL_CONFIG.items():
        buttons.append([InlineKeyboardButton(friendly_name, callback_data=f"setgemini_{model_id}")])
    
    await m.edit(
        "⚙️ **Select Gemini Model:**\n(Mapped to stable versions)",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def set_user_model(callback_query):
    user_id = callback_query.from_user.id
    model_id = callback_query.data.split("_")[1]
    USER_MODELS[user_id] = model_id
    if user_id in USER_CHATS:
        del USER_CHATS[user_id]
    await callback_query.message.edit_text(f"✅ **Switched to {model_id}!**\n\nMemory has been reset.")
