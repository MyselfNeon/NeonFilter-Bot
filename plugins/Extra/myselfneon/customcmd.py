# plugins/custom_commands.py

import os
import json
from pyrogram import Client, filters
from pyrogram.types import Message

COMMANDS_FILE = "custom_commands.json"

# Load existing commands from file
if os.path.exists(COMMANDS_FILE):
    with open(COMMANDS_FILE, "r") as f:
        custom_commands = json.load(f)
else:
    custom_commands = {}


def save_commands():
    with open(COMMANDS_FILE, "w") as f:
        json.dump(custom_commands, f, indent=2)


# ====================== ADD CUSTOM COMMAND ======================
@Client.on_message(filters.command("addcmd") & filters.me)
async def add_command(client: Client, message: Message):
    args = message.text.split(" ", 2)
    if len(args) < 3:
        return await message.reply("⚠️ **Usage:** `/addcmd command_name reply_text`")

    cmd, reply_text = args[1].lower(), args[2]
    custom_commands[cmd] = reply_text
    save_commands()

    await message.reply(f"✅ **Custom Command Added**\n\n`/{cmd}` → {reply_text}")


# ====================== REMOVE CUSTOM COMMAND ======================
@Client.on_message(filters.command("removecmd") & filters.me)
async def remove_command(client: Client, message: Message):
    args = message.text.split(" ", 1)
    if len(args) < 2:
        return await message.reply("⚠️ **Usage:** `/removecmd command_name`")

    cmd = args[1].lower()
    if cmd in custom_commands:
        del custom_commands[cmd]
        save_commands()
        await message.reply(f"🗑️ **Custom Command Removed**: `/{cmd}`")
    else:
        await message.reply("❌ **Command Not Found**")


# ====================== LIST CUSTOM COMMANDS ======================
@Client.on_message(filters.command("listcmd") & filters.me)
async def list_commands(client: Client, message: Message):
    if not custom_commands:
        return await message.reply("⚠️ **No Custom Commands Added Yet**")

    text = "📜 **Custom Commands List:**\n\n"
    for cmd, reply in custom_commands.items():
        text += f"• `/{cmd}` → {reply}\n"

    await message.reply(text)


# ====================== HANDLE CUSTOM COMMANDS ======================
def register_custom_commands(client: Client):
    """Unregister old handler and register a new one with updated commands."""
    global custom_commands

    # Remove old handler if exists
    for handler in client.handlers[filters.command]:
        if getattr(handler, "_is_custom_commands_handler", False):
            client.remove_handler(handler)

    # Only register if we have commands
    if custom_commands:
        @Client.on_message(filters.command(list(custom_commands.keys())))
        async def handle_custom_commands(client: Client, message: Message):
            cmd = message.command[0].lower()
            if cmd in custom_commands:
                await message.reply(custom_commands[cmd])

        handle_custom_commands._is_custom_commands_handler = True


# ====================== AUTO REGISTER ======================
# Register initially when bot starts
def setup(client: Client):
    register_custom_commands(client)

    # Patch add/remove command functions to re-register handler dynamically
    original_add = add_command
    original_remove = remove_command

    async def add_wrapper(client, message):
        await original_add(client, message)
        register_custom_commands(client)

    async def remove_wrapper(client, message):
        await original_remove(client, message)
        register_custom_commands(client)

    add_command.__func__ = add_wrapper
    remove_command.__func__ = remove_wrapper
