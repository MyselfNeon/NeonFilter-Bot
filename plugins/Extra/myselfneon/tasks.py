# plugins/todo.py
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message

# In-memory storage (per user basis)
todo_list = {}
waiting_for_task = {}

def get_user_tasks(user_id: int):
    return todo_list.get(user_id, [])

# Step 1: User asks to add a task
@Client.on_message(filters.command("addtask") & filters.private)
async def add_task_command(client: Client, message: Message):
    user_id = message.from_user.id

    if user_id in waiting_for_task:
        await message.reply("⚠️ You already have a pending task input. Send it, use /cancel, or wait for timeout.")
        return

    waiting_for_task[user_id] = True
    await message.reply("✍️ Send your task now... (30s timeout)\nYou can type /cancel to stop.")

    async def timeout_task():
        await asyncio.sleep(30)
        if user_id in waiting_for_task:
            waiting_for_task.pop(user_id, None)
            try:
                await message.reply("⌛ Timeout! You didn’t send any task. Cancelled.")
            except:
                pass
    
    asyncio.create_task(timeout_task())

# Step 2: Capture next message as task
@Client.on_message(filters.private & ~filters.command(["addtask", "listtask", "deltask", "cancel"]))
async def save_task(client: Client, message: Message):
    user_id = message.from_user.id

    if user_id in waiting_for_task:
        task_text = message.text.strip()
        if not task_text:
            return await message.reply("❌ Task cannot be empty.")
        
        tasks = get_user_tasks(user_id)
        tasks.append(task_text)
        todo_list[user_id] = tasks

        waiting_for_task.pop(user_id, None)
        await message.reply(f"✅ Task added:\n`{task_text}`")

# Step 3: Manual cancel
@Client.on_message(filters.command("cancel") & filters.private)
async def cancel_task(client: Client, message: Message):
    user_id = message.from_user.id

    if user_id in waiting_for_task:
        waiting_for_task.pop(user_id, None)
        await message.reply("❌ Task adding cancelled.")
    else:
        await message.reply("ℹ️ You don’t have any active task input.")

# Show list of tasks
@Client.on_message(filters.command("listtask") & filters.private)
async def list_tasks(client: Client, message: Message):
    user_id = message.from_user.id
    tasks = get_user_tasks(user_id)

    if not tasks:
        return await message.reply("📭 Your to-do list is empty.")

    reply_text = "📝 **Your To-Do List:**\n\n"
    for i, task in enumerate(tasks, start=1):
        reply_text += f"{i}. {task}\n"

    await message.reply(reply_text)

# Delete a task by number
@Client.on_message(filters.command("deltask") & filters.private)
async def delete_task(client: Client, message: Message):
    user_id = message.from_user.id
    tasks = get_user_tasks(user_id)

    if not tasks:
        return await message.reply("❌ You don't have any tasks to delete.")

    try:
        index = int(message.command[1]) - 1
        if index < 0 or index >= len(tasks):
            return await message.reply("⚠️ Invalid task number.")

        removed = tasks.pop(index)
        todo_list[user_id] = tasks
        await message.reply(f"🗑️ Removed task:\n`{removed}`")
    except (IndexError, ValueError):
        await message.reply("❌ Please provide a valid task number.\nUsage: `/deltask 2`")
      
