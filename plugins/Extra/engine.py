import google.generativeai as genai
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from info import GEMINI_API_KEY

# 1. Configuration and Client Setup
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

# 2. Global Chat Storage
# Stores active chat sessions: {user_id: ChatSessionObject}
USER_CHATS = {}

# 3. Model Configuration
# Gemini 1.5 Flash is currently the best balance of speed and free tier limits.
MODEL_CONFIG = {
    "Fast (Flash)": "gemini-1.5-flash",
    "Smart (Pro)": "gemini-1.5-pro",
}
# Default to Flash
USER_MODELS = {} 

# --- Helper Functions ---

def get_user_model_name(user_id):
    """Returns the model ID selected by the user, defaults to Flash."""
    return USER_MODELS.get(user_id, "gemini-1.5-flash")

def get_chat_session(user_id):
    """Retrieves or creates a Gemini ChatSession for the user."""
    # If user has no session, start a new one
    if user_id not in USER_CHATS:
        model_name = get_user_model_name(user_id)
        try:
            model = genai.GenerativeModel(model_name)
            USER_CHATS[user_id] = model.start_chat(history=[])
        except Exception as e:
            print(f"Error starting chat for {user_id}: {e}")
            return None
    return USER_CHATS[user_id]

# --- Main AI Function ---

async def ai(user_id, query):
    if not AI_ENABLED:
        return "🚫 AI is disabled. Please add `GEMINI_API_KEY` to `info.py`."

    try:
        chat = get_chat_session(user_id)
        if not chat:
            return "❌ Error: Could not initialize chat session."
        
        # Send message to Gemini (Async)
        response = await chat.send_message_async(query)
        
        return response.text

    except Exception as e:
        # Check for safety filter errors (common with Gemini)
        if "safety" in str(e).lower():
            return "⚠️ **Safety Block:** I cannot answer this query due to safety content filters."
        return f"⚠️ **Gemini Error:** {e}"

# --- Command Logic ---

async def ask_ai(m, message):
    try:
        # Check if user actually provided a question
        if len(message.command) < 2:
            await m.edit("👋 **Hello! I am Gemini.**\n\nAsk me anything: `/gemini How to make tea?`\n\n_Powered by Google AI_")
            return

        user_id = message.from_user.id
        question = message.text.split(" ", 1)[1]
        
        # Send processing status
        await m.edit("👀 **Thinking...**")
        
        response = await ai(user_id, question)
        
        # Format the output with Markdown
        model_label = "Flash" if "flash" in get_user_model_name(user_id) else "Pro"
        await m.edit(f"**♊ Gemini ({model_label}):**\n\n{response}")
        
    except Exception as e:
        await m.edit(f"❌ **Error:** {e}")

async def reset_chat_history(m):
    """Wipes the memory for the user."""
    user_id = m.from_user.id
    if user_id in USER_CHATS:
        del USER_CHATS[user_id] # Deleting key forces a new session next time
        await m.edit("🗑️ **Memory Wiped!** I have forgotten our previous conversation.")
    else:
        await m.edit("✨ My memory is already clean.")

async def send_model_selection(m):
    """Sends buttons to switch models."""
    buttons = []
    for friendly_name, model_id in MODEL_CONFIG.items():
        # Callback data format: setgemini_modelid
        buttons.append([InlineKeyboardButton(friendly_name, callback_data=f"setgemini_{model_id}")])
    
    await m.edit(
        "⚙️ **Select Gemini Model:**\n\n"
        "• **Flash:** Faster response, great for simple tasks.\n"
        "• **Pro:** Smarter reasoning, better for complex coding/writing.",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def set_user_model(callback_query):
    """Callback to switch the user's model."""
    user_id = callback_query.from_user.id
    model_id = callback_query.data.split("_")[1]
    
    # Save preference
    USER_MODELS[user_id] = model_id
    
    # Reset chat history because different models can't share the same session object
    if user_id in USER_CHATS:
        del USER_CHATS[user_id]
        
    await callback_query.message.edit_text(f"✅ **Switched to {model_id}!**\n\nMemory has been reset to apply changes.")
