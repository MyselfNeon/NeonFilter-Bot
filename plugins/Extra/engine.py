import warnings
# Silence "Python 3.10 end of life" warning to keep logs clean
warnings.filterwarnings("ignore", category=FutureWarning)

import google.generativeai as genai
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from info import GEMINI_API_KEY

# --- DYNAMIC MODEL LOADER (Self-Healing) ---
AI_ENABLED = False
MODEL_CONFIG = {} # Stores only valid models found on your account

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        AI_ENABLED = True
        print("✅ Google Gemini Connected")
        
        # 1. Ask Google what models are actually valid for this API key
        print("🔍 Scanning for available models...")
        all_models = list(genai.list_models())
        
        for m in all_models:
            if 'generateContent' in m.supported_generation_methods:
                model_id = m.name.replace("models/", "")
                
                # Prioritize specific versions to build a clean menu
                if "flash" in model_id and "1.5" in model_id:
                    MODEL_CONFIG["⚡ Flash (Fast)"] = model_id
                elif "pro" in model_id and "1.5" in model_id:
                    MODEL_CONFIG["🧠 Pro (Smart)"] = model_id
                elif "gemini-pro" == model_id and "Standard" not in MODEL_CONFIG:
                    MODEL_CONFIG["⭐ Standard"] = model_id

        # If strict filtering failed, grab the first available generative model
        if not MODEL_CONFIG:
            for m in all_models:
                if 'generateContent' in m.supported_generation_methods:
                    name = m.name.replace("models/", "")
                    MODEL_CONFIG[f"🤖 {name}"] = name
                    break
        
        print(f"📋 Valid Models Loaded: {list(MODEL_CONFIG.values())}")

    except Exception as e:
        print(f"❌ Critical Gemini Error: {e}")

else:
    print("⚠️ GEMINI_API_KEY missing in info.py. AI disabled.")

# --- CHAT SESSION MANAGEMENT ---
USER_CHATS = {}
USER_MODELS = {} 

def get_safe_user_id(message):
    """Safely extract user ID from a message (handles users and anon admins)."""
    if hasattr(message, 'from_user') and message.from_user:
        return message.from_user.id
    if hasattr(message, 'sender_chat') and message.sender_chat:
        return message.sender_chat.id
    return None

def get_user_model_name(user_id):
    # Default to the first valid model we found
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
            # Fallback: try to heal by picking the first valid model again
            print(f"⚠️ Model {model_name} failed. Falling back.")
            fallback = list(MODEL_CONFIG.values())[0] if MODEL_CONFIG else "gemini-pro"
            try:
                USER_CHATS[user_id] = genai.GenerativeModel(fallback).start_chat(history=[])
            except:
                return None
    return USER_CHATS[user_id]

# --- AI LOGIC ---
async def ai(user_id, query):
    if not AI_ENABLED:
        return "🚫 AI is disabled. Check API Key."

    try:
        chat = get_chat_session(user_id)
        if not chat:
            return "❌ Error: Could not start chat session."
            
        response = await chat.send_message_async(query)
        return response.text
    except Exception as e:
        return f"⚠️ **Gemini Error:** {e}"

# --- COMMAND HANDLERS ---
async def ask_ai(m, message):
    try:
        if len(message.command) < 2:
            await m.edit("👋 **Hi! I'm Gemini.**\nAsk me anything: `/gemini How are you?`")
            return

        user_id = get_safe_user_id(message)
        if not user_id:
            await m.edit("❌ Error: Could not identify user.")
            return

        question = message.text.split(" ", 1)[1]
        
        await m.edit("👀 **Thinking...**")
        response = await ai(user_id, question)
        
        # Simple label for the header
        current_model = get_user_model_name(user_id)
        label = "AI"
        if "pro" in current_model: label = "Pro"
        elif "flash" in current_model: label = "Flash"
        
        await m.edit(f"**♊ Gemini ({label}):**\n\n{response}")
        
    except Exception as e:
        await m.edit(f"❌ Error: {e}")

async def reset_chat_history(m, original_message):
    # FIXED: Get ID from the user's message, not the bot's reply
    user_id = get_safe_user_id(original_message)
    
    if not user_id:
        await m.edit("❌ Error: Could not identify you.")
        return

    if user_id in USER_CHATS:
        del USER_CHATS[user_id]
        await m.edit("🗑️ **Memory Wiped!**\nI have forgotten our previous conversation.")
    else:
        await m.edit("✨ **Clean Slate:** My memory of you was already empty.")

async def send_model_selection(m):
    if not MODEL_CONFIG:
        await m.edit("❌ No models found. Please check logs.")
        return

    buttons = []
    for friendly_name, model_id in MODEL_CONFIG.items():
        buttons.append([InlineKeyboardButton(friendly_name, callback_data=f"setgemini_{model_id}")])
    
    buttons.append([InlineKeyboardButton("❌ Close", callback_data="close_data")])

    await m.edit(
        "⚙️ **Select AI Model**\nThese models are available on your account:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def set_user_model(callback_query):
    user_id = callback_query.from_user.id
    model_id = callback_query.data.split("_")[1]
    
    USER_MODELS[user_id] = model_id
    
    # Reset chat history so the new model takes effect
    if user_id in USER_CHATS:
        del USER_CHATS[user_id]
    
    # Delete the menu and send a fresh confirmation (Fixes "Selected Both" glitch)
    await callback_query.message.delete()
    await callback_query.message.reply_text(f"✅ **Model Switched!**\n\nNow using: `{model_id}`")
    
