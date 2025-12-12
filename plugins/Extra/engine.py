import openai
from openai import AsyncOpenAI

# 1. Configuration and Client Setup
# NOTE: Replace the placeholder key below with your actual OpenAI API Key.
# It is highly recommended to use environment variables for keys.
API_KEY = "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" 

# Instantiate the AsyncOpenAI client globally
client = AsyncOpenAI(api_key=API_KEY)

async def ai(query):
    """
    Asynchronously queries the OpenAI Chat Completions API (gpt-3.5-turbo).
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
        
        # Extract the content from the response object
        return response.choices[0].message.content.strip()

    except Exception as e:
        # Catch and report any API errors
        error_message = f"OpenAI API Error: {e}"
        print(error_message)
        return f"Sorry, the AI encountered an error: {e}"
     
async def ask_ai(m, message):
    """
    Handles the Telegram interaction: extracting the question and updating the message.
    """
    try:
        # Extract the question (everything after the command, e.g., /openai question)
        # Note: We rely on openai.py to ensure the command is not empty
        question = message.text.split(" ", 1)[1]
        
        # Generate response using the async OpenAI function
        response = await ai(question)
        
        # Send response back to user by editing the placeholder message (m)
        await m.edit(f"{response}")
        
    except IndexError:
        # This handles the unlikely case where the command was empty,
        # though openai.py should catch it.
        await m.edit("Please provide a question after the command.")
        
    except Exception as e:
        # Handle other non-API errors (e.g., Pyrogram errors)
        error_message = f"An error occurred: {type(e).__name__}: {e}"
        await m.edit(error_message)