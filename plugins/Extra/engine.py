import warnings
warnings.filterwarnings("ignore") # Silence python warnings

import google.generativeai as genai
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from info import GEMINI_API_KEY

# ==========================================
# 🧠 DYNAMIC MODEL LOADER (The Fix)
# ==========================================
AI_ENABLED = False
AVAILABLE_MODELS = []
MODEL_CONFIG = {}

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        AI_ENABLED = True
        print("✅ Google Gemini Connected")
        
        # 1. Ask Google what models are actually valid for you
        print("🔍 Scanning for available models...")
        all_models = list(genai.list_models())
        
        for m in all_models:
            # We only want models that can generate text (generateContent)
            if 'generateContent' in m.supported_generation_methods:
                model_id = m.name.replace("models/", "")
                
                # Filter for the best ones to show in the menu
                if "flash" in model_id and "1.5" in model_id:
                    MODEL_CONFIG["⚡ Flash (Fast)"] = model_id
                elif "pro" in model_id and "1.5" in model_id:
                    MODEL_CONFIG["🧠 Pro (Smart)"] = model_id
                elif "gemini-pro" == model_id and "Standard" not in MODEL_CONFIG:
                    MODEL_CONFIG["⭐ Standard"] = model_id

        # If we found nothing specific, grab the first valid generative model
        if not MODEL_CONFIG:
            for m in all_models:
                if 'generateContent' in m.supported_generation_methods:
                    name = m.name.replace("models/", "")
                    MODEL_CONFIG[f"🤖 {name}"] = name
                    break
        
        print(f"📋 Valid Models Found: {list(MODEL_CONFIG.values())}")

    except Exception as e:
        print(f"❌ Critical Gemini Error: {e}")
        MODEL_CONFIG = {"⚠️ Error Mode": "gemini-pro"} # Fallback

else:
    print("⚠️ GEMINI_API_KEY missing.")

# ==========================================
# ⚙️ CHAT MANAGEMENT
# ==========================================
USER_CHATS = {}
USER_MODELS = {} 

def get_user_model_name(user_id):
    # Default to the first available model in our valid list
    if user_id in USER_MODELS:
        return USER_MODELS[user_id]
    return list(MODEL_CONFIG.values())[0] if MODEL_CONFIG else "gemini-pro"

def get_chat_session(user_id):
    if user_id not in USER_CHATS:
        model_name = get_user_model_name(user_id)
        try:
            model = genai.GenerativeModel(model_name)
            USER_CHATS[user_id] = model.start_chat(history=[])
        except Exception as e:
            # If the session fails, try to heal by picking the first valid model again
            fallback = list(MODEL_CONFIG.values())[0]
            USER_CHATS[user_id] = genai.GenerativeModel(fallback).start_chat(history=[])
    return USER_CHATS[user_id]

# ==========================================
# 💬 AI LOGIC
# ==========================================

async def ai(user_id, query):
    if not AI_ENABLED:
        return "🚫 AI is disabled. Check API Key."

    try:
        chat = get_chat_session(user_id)
        response = await chat.send_message_async(query)
        return response.text
    except Exception as e:
        return f"⚠️ **Gemini Error:** {e}"

# ==========================================
# 🎮 COMMAND HANDLERS
# ==========================================

async def ask_ai(m, message):
    try:
        if len(message.command) < 2:
            await m.edit("👋 **Hi! I'm Gemini.**\nAsk me anything: `/gemini How are you?`")
            return

        user_id = message.from_user.id
        question = message.text.split(" ", 1)[1]
        
        await m.edit("👀 **Thinking...**")
        response = await ai(user_id, question)
        
        current_model = get_user_model_name(user_id)
        await m.edit(f"**♊ Gemini ({current_model}):**\n\n{response}")
        
    except Exception as e:
        await m.edit(f"❌ Error: {e}")

async def reset_chat_history(m):
    user_id = m.from_user.id
    if user_id in USER_CHATS:
        del USER_CHATS[user_id]
        await m.edit("🗑️ **Memory Wiped!**")
    else:
        await m.edit("✨ Memory is already clean.")

async def send_model_selection(m):
    # DYNAMIC BUTTON GENERATION
    # Only shows buttons for models that ACTUALLY EXIST on your account
    buttons = []
    for friendly_name, model_id in MODEL_CONFIG.items():
        buttons.append([InlineKeyboardButton(friendly_name, callback_data=f"setgemini_{model_id}")])
    
    # Close button to clean up UI
    buttons.append([InlineKeyboardButton("❌ Close", callback_data="close_data")])

    await m.edit(
        "⚙️ **Select AI Model**\nThese models are available on your account:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def set_user_model(callback_query):
    user_id = callback_query.from_user.id
    model_id = callback_query.data.split("_")[1]
    
    USER_MODELS[user_id] = model_id
    
    # Reset chat history
    if user_id in USER_CHATS:
        del USER_CHATS[user_id]
    
    # UI FIX: Delete the old menu and send a fresh confirmation
    # This prevents the "both buttons selected" visual bug
    await callback_query.message.delete()
    await callback_query.message.reply_text(f"✅ **Model Switched!**\n\nNow using: `{model_id}`")
