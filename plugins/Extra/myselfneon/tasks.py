#Tasks.py + Help Plugin seperately
# ====================== PLUGINS/TODO.PY ======================
from pyrogram import Client, filters
from pyrogram.types import Message

# ====================== IN-MEMORY STORAGE (per user basis) ======================
todo_list = {}

def get_user_tasks(user_id: int):
    return todo_list.get(user_id, [])

# ====================== ADD TASK /addtask <task> ======================
@Client.on_message(filters.command("addtask") & filters.private)
async def add_task(client: Client, message: Message):
    user_id = message.from_user.id
    task_text = " ".join(message.command[1:])

    if not task_text:
        return await message.reply("**❌ __Please Provide A Task To Add.\n\nUsage:__** `/addtask Buy milk`")

    tasks = get_user_tasks(user_id)
    tasks.append(task_text)
    todo_list[user_id] = tasks

    await message.reply(f"**Tᴀsᴋ Aᴅᴅᴇᴅ ✅**\n\n`{task_text}`")

# ====================== SHOW ALL TASKS ======================
@Client.on_message(filters.command("listtask") & filters.private)
async def list_tasks(client: Client, message: Message):
    user_id = message.from_user.id
    tasks = get_user_tasks(user_id)

    if not tasks:
        return await message.reply("**📭 __Your To-Do List Is Empty__**.")

    reply_text = "**Yᴏᴜʀ Tᴏ-Dᴏ Lɪsᴛ 📝**\n\n"
    for i, task in enumerate(tasks, start=1):
        reply_text += f"{i}. {task}\n"

    await message.reply(reply_text)

# ====================== DELETE TASK BY NUMBER ======================
@Client.on_message(filters.command("deltask") & filters.private)
async def delete_task(client: Client, message: Message):
    user_id = message.from_user.id
    tasks = get_user_tasks(user_id)

    if not tasks:
        return await message.reply("**❌ __Don't Have Any Tasks To Delete.__**")

    try:
        index = int(message.command[1]) - 1
        if index < 0 or index >= len(tasks):
            return await message.reply("**__Invalid Task Number__ 🚫**.")

        removed = tasks.pop(index)
        todo_list[user_id] = tasks
        await message.reply(f"**Rᴇᴍᴏᴠᴇᴅ Tᴀsᴋ** 🗑️\n\n`{removed}`")
    except (IndexError, ValueError):
        await message.reply("**😏 __Provide a Valid Task Number.\n\nUsage__**: `/deltask 2`")

# ====================== HELP MENU ======================
@Client.on_message(filters.command(["taskhelp"]) & filters.private)
async def todo_help(client: Client, message: Message):
    help_text = (
    "<blockquote>✨ **𝐓𝐀𝐒𝐊 𝐇𝐄𝐋𝐏** ✨</blockquote>\n\n"
    "1️⃣ __/addtask – **Add a New Task__**\n"
    "2️⃣ __/deltask – **Delete a Task__**\n"
    "3️⃣ __/listtask – **Show All Your Tasks__**\n"
    "4️⃣ __/taskhelp – **Show This Help Menu__**\n\n"
    "🔹 **__Example:__**\n"
    "`/addtask Finish Homework`\n\n**🔥 __Powered By @NeonFiles__ 🔥**"
    )
    await message.reply(help_text)

# ====================== NEW /help HANDLER (separate HELP_TEXT) ======================
HELP_TEXT = (
    "<blockquote>🆘 **QUICK HELP — TODO PLUGIN** 🆘</blockquote>\n\n"
    "• `/addtask <task>` — Add a new task quickly (e.g. `/addtask Buy milk`).\n"
    "• `/listtask` — View all your tasks (numbered).\n"
    "• `/deltask <number>` — Delete a task by its number from `/listtask`.\n\n"
    "💡 Tip: Keep tasks short & actionable. Use the task number shown by `/listtask` when deleting.\n\n"
    "**Powered By @NeonFiles**"
)

@Client.on_message(filters.command("help") & filters.private)
async def help_command(client: Client, message: Message):
    await message.reply(HELP_TEXT)
    
