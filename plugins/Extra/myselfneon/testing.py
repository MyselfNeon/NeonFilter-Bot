import asyncio
import aiohttp
from pyrogram import Client, filters
from pyrogram.types import Message

# --- CONFIGURATION ---
DOWNLOAD_LIMIT = 1024 * 1024  # 1 MB
CHECK_INTERVAL = 300          # 5 Minutes

# Dictionary to keep track of active tasks: { "url": asyncio.Task }
active_tasks = {}

@Client.on_message(filters.command("addt") & filters.user(12345678)) # Replace with your ID
async def add_keep_alive(client: Client, message: Message):
    """
    Usage: /addt https://link.com
    Adds a link to the keep-alive loop.
    """
    if len(message.command) < 2:
        await message.reply_text("❌ Usage: `/addt https://url-here`")
        return

    url = message.command[1]

    if url in active_tasks:
        await message.reply_text(f"⚠️ Task already running for:\n`{url}`")
        return

    # Create a background task for this specific URL
    task = asyncio.create_task(keep_alive_loop(url))
    active_tasks[url] = task
    
    await message.reply_text(f"✅ **Added:** `{url}`\nDownloading 1MB every {CHECK_INTERVAL}s.")


@Client.on_message(filters.command("delt") & filters.user(12345678)) # Replace with your ID
async def delete_keep_alive(client: Client, message: Message):
    """
    Usage: /delt https://link.com
    Stops the keep-alive task for the specific link.
    """
    if len(message.command) < 2:
        await message.reply_text("❌ Usage: `/delt https://url-here`")
        return

    url = message.command[1]

    if url not in active_tasks:
        await message.reply_text("⚠️ URL not found in active tasks.")
        return

    # Cancel the asyncio task
    task = active_tasks[url]
    task.cancel()
    
    # Remove from dictionary
    del active_tasks[url]
    
    await message.reply_text(f"🗑 **Deleted:** `{url}`\nTask stopped successfully.")


@Client.on_message(filters.command("listt") & filters.user(12345678))
async def list_tasks(client: Client, message: Message):
    """
    Lists all currently active URLs.
    """
    if not active_tasks:
        await message.reply_text("Empty. No active tasks.")
        return

    text = "**Active Keep-Alive Tasks:**\n"
    for url in active_tasks:
        text += f"🔗 `{url}`\n"
    
    await message.reply_text(text)


async def keep_alive_loop(url):
    """
    The background loop that downloads 1MB and then cancels.
    """
    print(f"Starting loop for {url}")
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                timeout = aiohttp.ClientTimeout(total=60)
                
                async with session.get(url, timeout=timeout) as response:
                    total_downloaded = 0
                    
                    # Stream chunks (1KB at a time)
                    async for chunk in response.content.iter_chunked(1024):
                        total_downloaded += len(chunk)
                        
                        # Stop once we reach the limit (0.5MB - 1MB)
                        if total_downloaded >= DOWNLOAD_LIMIT:
                            break 
            
            # print(f"Pinging {url} complete.") # Optional logging
            
        except asyncio.CancelledError:
            # This block runs when task.cancel() is called via /delt
            print(f"Task cancelled for {url}")
            raise # Important to let asyncio know it's cancelled
            
        except Exception as e:
            print(f"Error on {url}: {e}")

        # Wait for interval
        await asyncio.sleep(CHECK_INTERVAL)
