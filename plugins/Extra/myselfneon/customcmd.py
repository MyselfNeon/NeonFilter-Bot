import json
import os
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


# ─────────────────────────────
# Add a new custom command
# ─────────────────────────────
@Client.on_message(filters.command("addcommand") & filters.private)
async def add_command(client: Client, message: Message):
    if not message.text:
        return

    parts = message.text.split(" ", 2)
    if len(parts) < 3:
        return await message.reply("❌ Usage: `/addcommand command_name response`", quote=True)

    cmd, response = parts[1], parts[2]
    if not cmd.startswith("/"):
        cmd = "/" + cmd

    custom_commands[cmd] = response
    save_commands()

    await message.reply(f"✅ Command `{cmd}` added with response:\n\n{response}", quote=True)


# ─────────────────────────────
# Delete an existing custom command
# ─────────────────────────────
@Client.on_message(filters.command("delcommand") & filters.private)
async def delete_command(client: Client, message: Message):
    if not message.text:
        return

    parts = message.text.split(" ", 1)
    if len(parts) < 2:
        return await message.reply("❌ Usage: `/delcommand command_name`", quote=True)

    cmd = parts[1]
    if not cmd.startswith("/"):
        cmd = "/" + cmd

    if cmd in custom_commands:
        del custom_commands[cmd]
        save_commands()
        await message.reply(f"🗑 Deleted command `{cmd}`", quote=True)
    else:
        await message.reply("❌ Command not found.", quote=True)


# ─────────────────────────────
# List all saved custom commands
# ─────────────────────────────
@Client.on_message(filters.command("listcommands") & filters.private)
async def list_commands(client: Client, message: Message):
    if not custom_commands:
        return await message.reply("ℹ️ No custom commands yet.", quote=True)

    text = "📜 **Custom Commands:**\n\n"
    for cmd, response in custom_commands.items():
        text += f"**{cmd}** → {response[:40]}...\n"
    await message.reply(text, quote=True)


# ─────────────────────────────
# Handle custom commands dynamically
# ─────────────────────────────
@Client.on_message(filters.text & filters.private)
async def handle_custom(client: Client, message: Message):
    if not message.text:
        return

    if message.text in custom_commands:
        await message.reply(custom_commands[message.text], quote=True)
        
