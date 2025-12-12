import openai
from openai import AsyncOpenAI
# Import the configuration variable from your config file
from info import OPENAI_API_KEY 

# 1. Initialization Logic based on imported key
AI_ENABLED = False
client = None

if OPENAI_API_KEY:
    AI_ENABLED = True
    try:
        # Initialize the client only if the key is present
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        print("OpenAI API Key successfully loaded from info.py/environment.")
    except Exception as e:
        # Handle errors during client instantiation (e.g., library error)
        AI_ENABLED = False
        print(f"Error initializing OpenAI client: {e}")
else:
    print("Warning: OPENAI_API_KEY is not set. AI commands will be disabled.")


# --- AI Functionality ---

async def ai(query):
    """
    Asynchronously queries the OpenAI Chat Completions API.
    """
    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": query}
            ],
            max_tokens=100,
            n=1,
            temperature=0.9
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        # Catch and report any API errors (e.g., rate limits, invalid key check on first call)
        error_message = f"OpenAI API Error: {e}"
        print(error_message)
        return f"Sorry, the AI encountered an error: {e}"
     
async def ask_ai(m, message):
    """
    Handles the Telegram interaction and checks the AI status.
    """
    if not AI_ENABLED:
        # Display message if the feature is disabled due to a missing key
        await m.edit("🚫 **AI is disabled.** Please set the `OPENAI_API_KEY` environment variable to enable this command.")
        return
        
    try:
        # Extract the question (everything after the command)
        question = message.text.split(" ", 1)[1]
        
        # Generate response using the async OpenAI function
        response = await ai(question)
        
        # Send response back to user by editing the placeholder message (m)
        await m.edit(f"{response}")
        
    except IndexError:
        # Handle case where only /openai was sent without a question
        await m.edit("Please provide a question after the command.")
        
    except Exception as e:
        # Handle other non-API errors (e.g., Pyrogram errors)
        error_message = f"An error occurred: {type(e).__name__}: {e}"
        await m.edit(error_message)