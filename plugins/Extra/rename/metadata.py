from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.users_chats_db import db
from info import RENAME_MODE

# --- Helper Function to format metadata for display ---
def format_metadata(metadata_str):
    if not metadata_str:
        return "🥲 **__Sorry !! No Metadata Found...__** 🥹"
    
    display_text = "**Your Saved Metadata:-**\n\n"
    # Convert the pipe-separated string to a cleaner display format
    for item in metadata_str.split('|'):
        display_text += f"`{item.strip()}`\n"
        
    return display_text

# --- Main /metadata Command ---
@Client.on_message(filters.private & filters.command('metadata'))
async def metadata_handler(client, message):
    if RENAME_MODE == False:
        return 
        
    user_id = message.from_user.id
    metadata = await db.get_metadata(user_id)
    
    metadata_text = format_metadata(metadata)
    
    # Define the inline keyboard layout
    buttons = []
    if metadata:
        # If metadata exists, show option to remove it
        buttons.append(InlineKeyboardButton("❌ Remove", callback_data="meta_delete"))
        
    # Always show option to add/update
    buttons.append(InlineKeyboardButton("➕ Add/Update New", callback_data="meta_add"))
    
    markup = InlineKeyboardMarkup([buttons])
    
    await message.reply_text(metadata_text, reply_markup=markup)

# --- Callback Query Handler for Metadata Buttons ---
@Client.on_callback_query(filters.regex("meta_"))
async def metadata_callbacks(client, callback_query):
    query_data = callback_query.data
    user_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id
    
    if query_data == "meta_delete":
        # Delete the metadata
        await db.set_metadata(user_id, metadata=None)
        await callback_query.message.edit_text("**__Your Metadata Successfully Deleted__** ❌")
        
    elif query_data == "meta_add":
        # Prompt the user to add new metadata
        
        # Edit the current message to show the prompt
        prompt_text = (
            "**__Give me the Metadata/File Tags to Set__ 🏷️**\n\n"
            "**💡 Format**:\n"
            "**`key1=value1`**\n"
            "**`key2=value2`**\n\n"
            "__**Example**__: `Title=My Awesome Movie|Artist=Neon Files|Genre=Action`\n\n"
            "**Note**: Tags should be separated by a **Pipe symbol (`|`)**\n\n"
            "__**Send your metadata now:**__"
        )
        await callback_query.message.edit_text(prompt_text)
        
        # Wait for the user's next message (the actual metadata text)
        try:
            metadata_msg = await client.listen(chat_id, filters.text, timeout=120)
            metadata_text = metadata_msg.text.strip()
            
            # --- Validation and Parsing ---
            data = {}
            valid = True
            for item in metadata_text.split('|'):
                key_value = item.strip().split('=', 1)
                if len(key_value) == 2:
                    data[key_value[0].strip()] = key_value[1].strip()
            
            if not data and metadata_text:
                valid = False
            # ------------------------------
            
            if not metadata_text or not valid:
                return await client.send_message(
                    chat_id, 
                    "__**Error: Could not parse any valid key=value pairs or metadata was empty. Please check the format and try the /metadata command again.**__ ❌"
                )

            # Save the metadata
            await db.set_metadata(user_id, metadata=metadata_text)
            
            # Show success message and the new metadata
            new_metadata_text = format_metadata(metadata_text)
            await client.send_message(
                chat_id, 
                f"__**Your Metadata Successfully Saved ✅**__\n\n{new_metadata_text}"
            )
            
        except TimeoutError:
            await client.send_message(chat_id, "__**Metadata input timed out. Please run the /metadata command again to start over.**__ ⌛")
        except Exception as e:
            await client.send_message(chat_id, f"__**An unexpected error occurred: {e}**__ ❌")
            
    # Always answer the callback query to remove the loading state
    await callback_query.answer()