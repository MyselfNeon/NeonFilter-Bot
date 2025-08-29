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
        return await message.reply("**❌ __Please Provide A Task To Add.\n\nUsage:__** `/addtask Buy milk`")

    tasks = get_user_tasks(user_id)
    tasks.append(task_text)
    todo_list[user_id] = tasks

    await message.reply(f"**✅ __Tᴀsᴋ Aᴅᴅᴇᴅ:__**\n\n`{task_text}`")

# Show all tasks
@Client.on_message(filters.command("listtask") & filters.private)
async def list_tasks(client: Client, message: Message):
    user_id = message.from_user.id
    tasks = get_user_tasks(user_id)

    if not tasks:
        return await message.reply("**📭 __Your To-Do List Is Empty__**.")

    reply_text = "**📝 __Your To-Do List:__**\n\n"
    for i, task in enumerate(tasks, start=1):
        reply_text += f"{i}. {task}\n"

    await message.reply(reply_text)

# Delete task by number
@Client.on_message(filters.command("deltask") & filters.private)
async def delete_task(client: Client, message: Message):
    user_id = message.from_user.id
    tasks = get_user_tasks(user_id)

    if not tasks:
        return await message.reply("**❌ __You Don't Have Any Tasks To Delete.__**")

    try:
        index = int(message.command[1]) - 1
        if index < 0 or index >= len(tasks):
            return await message.reply("**🚫 __Iɴᴠᴀʟɪᴅ Tᴀsᴋ Nᴜᴍʙᴇʀ__**.")

        removed = tasks.pop(index)
        todo_list[user_id] = tasks
        await message.reply(f"🗑️ Removed task:\n`{removed}`")
    except (IndexError, ValueError):
        await message.reply("**❌ __Please provide a valid task number.\n\nUsage__**: `/deltask 2`")

# Help menu
@Client.on_message(filters.command(["taskhelp"]) & filters.private)
async def todo_help(client: Client, message: Message):
    help_text = (
        "**📝 __To-Do Bot Commands__:**\n\n"
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
    
