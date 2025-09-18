from pyrogram import Client, filters
from info import LOG_CHANNEL, ADMINS


@Client.on_message(filters.command("getcommands") & filters.user(ADMINS))
async def get_bot_commands(client, message):
    try:
        # Fetch all bot commands
        commands = await client.get_bot_commands()

        if not commands:
            await client.send_message(LOG_CHANNEL, "⚠️ No commands are set in the bot.")
            return await message.reply_text("⚠️ No commands found.")

        # Format commands list
        command_list = "\n".join(
            [f"➤ `{cmd.command}` — {cmd.description or 'No description'}"
             for cmd in commands]
        )
        total = len(commands)

        # Prepare full text
        log_text = (
            f"**🤖 __Current Bot Commands__**\n\n"
            f"{command_list}\n\n"
            f"**📊 __Total Commands:** {total}__"
        )

        # Split into chunks if text is too long
        chunks = [log_text[i:i + 4000] for i in range(0, len(log_text), 4000)]

        for idx, chunk in enumerate(chunks, start=1):
            header = f"📦 Commands List (Part {idx}/{len(chunks)})\n\n" if len(chunks) > 1 else ""
            await client.send_message(LOG_CHANNEL, header + chunk)

        # Reply to admin confirming
        await message.reply_text(f"**✅ __Commands logged to LOG_CHANNEL ({total} total)__.**")

    except Exception as e:
        await message.reply_text(f"**❌ __Failed to fetch commands.\nError: `{e}`__**")
