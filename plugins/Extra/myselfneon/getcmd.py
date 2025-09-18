from pyrogram import Client, filters
from info import LOG_CHANNEL, ADMINS  # Import from info.py


@Client.on_message(filters.command("getcommands") & filters.user(ADMINS))
async def get_bot_commands(client, message):
    try:
        # Fetch all bot commands
        commands = await client.get_bot_commands()

        if not commands:
            await client.send_message(LOG_CHANNEL, "⚠️ No commands are set in the bot.")
            await message.reply_text("⚠️ No commands found.")
            return

        # Format commands
        command_list = "\n".join([f"• {cmd.command} — {cmd.description}" for cmd in commands])
        total = len(commands)

        log_text = (
            f"**🤖 Bot Commands List**\n\n"
            f"{command_list}\n\n"
            f"**📊 Total Commands:** {total}"
        )

        # Send to log channel
        await client.send_message(LOG_CHANNEL, log_text)

        # Reply to admin
        await message.reply_text(f"✅ Commands logged to LOG_CHANNEL ({total} total).")

    except Exception as e:
        await message.reply_text(f"❌ Failed to fetch commands.\nError: `{e}`")
