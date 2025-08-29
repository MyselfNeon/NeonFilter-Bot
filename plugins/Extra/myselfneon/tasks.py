# plugins/todo.py
from pyrogram import Client, filters
from pyrogram.types import Message

# In-memory storage (per user basis)
todo_list = {}

def get_user_tasks(user_id: int):
    return todo_list.get(user_id, [])

# Add task directly with /addtask <task>
@Client.on_message(filters.command("addtask") & filters.private)
async def add_task(client: Client, message: Message):
    user_id = message.from_user.id
    task_text = " ".join(message.command[1:])

    if not task_text:
        return await message.reply("❌ Please provide a task to add.\nUsage: `/addtask Buy milk`")

    tasks = get_user_tasks(user_id)
    tasks.append(task_text)
    todo_list[user_id] = tasks

    await message.reply(f"✅ Task added:\n`{task_text}`")

# Show all tasks
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

# Delete task by number
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

# Help menu
@Client.on_message(filters.command(["taskhelp"]) & filters.private)
async def todo_help(client: Client, message: Message):
    help_text = (
        "📝 **To-Do Bot Commands:**\n\n"
        "/addtask <task> - Add a new task\n"
        "/listtask - Show all your tasks\n"
        "/deltask <number> - Delete a task by its number\n"
        "/todohelp - Show this help menu\n\n"
        "Example:\n"
        "`/addtask Finish homework`\n"
        "`/deltask 2`\n"
        "`/listtask`"
    )
    await message.reply(help_text)
    
