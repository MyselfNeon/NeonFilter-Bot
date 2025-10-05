# ====================== PLUGINS/CARBON.PY ======================
from pyrogram import Client, filters
from pyrogram.types import Message
import aiohttp
import os
import asyncio

# ====================== CARBON GENERATOR ======================
async def make_carbon(text: str):
    """Generate a carbon image using the Carbon API."""
    carbon_api = "https://carbon-api.vercel.app/api/carbon"
    async with aiohttp.ClientSession() as session:
        async with session.post(carbon_api, json={"code": text}) as resp:
            if resp.status == 200:
                image_data = await resp.read()
                file_path = "carbon.png"
                with open(file_path, "wb") as f:
                    f.write(image_data)
                return file_path
    return None


# ====================== /carbon COMMAND ======================
@Client.on_message(filters.command("carbon") & filters.private)
async def carbon_create(client: Client, message: Message):
    # Check if message is a reply or contains text directly
    replied = message.reply_to_message
    text = None

    if replied and replied.text:
        text = replied.text
    elif len(message.command) > 1:
        text = " ".join(message.command[1:])
    else:
        return await message.reply(
            "**❌ __Please Reply To A Text Message Or Use:__**\n`/carbon your_text_here`"
        )

    wait = await message.reply("**🖌️ Generating Your Carbon... Please Wait ⏳**")

    try:
        # Step 1: Generate the Carbon image
        image_path = await make_carbon(text)
        if not image_path:
            await wait.edit("**⚠️ Failed To Generate Carbon Image. Try Again Later.**")
            return

        # Step 2: Update message before sending
        await wait.edit("**📤 Uploading Carbon Image... Almost Done ⏫**")
        await asyncio.sleep(0.5)

        # Step 3: Send the generated image
        await client.send_photo(
            chat_id=message.chat.id,
            photo=image_path,
            caption=(
                "✨ **𝐂𝐚𝐫𝐛𝐨𝐧 𝐆𝐞𝐧𝐞𝐫𝐚𝐭𝐞𝐝 𝐒𝐮𝐜𝐜𝐞𝐬𝐬𝐟𝐮𝐥𝐥𝐲** ✨\n\n"
                f"**🧩 Text:**\n`{text[:500]}`"
            ),
        )
        await wait.delete()
        os.remove(image_path)

    except Exception as e:
        await wait.edit(f"**❌ Error Occurred:** `{str(e)}`")


# ====================== CARBON HELP MENU ======================
@Client.on_message(filters.command("carbonhelp") & filters.private)
async def carbon_help(client: Client, message: Message):
    help_text = (
        "<blockquote>🎨 **𝐂𝐀𝐑𝐁𝐎𝐍 𝐇𝐄𝐋𝐏** 🎨</blockquote>\n\n"
        "**What It Does:**\n"
        "Creates a beautiful *Carbon-styled image* from your replied text or code.\n\n"
        "**📘 Commands:**\n"
        "➤ `/carbon` — Reply To Any Text To Generate Image\n"
        "➤ `/carbon your_text` — Generate Image Directly\n"
        "➤ `/carbonhelp` — Show This Help Menu\n\n"
        "**🧠 Example:**\n"
        "`print('Hello, world!')`\n"
        "→ Reply with `/carbon`\n\n"
        "**🖌️ Progress Flow:**\n"
        "`Generating...` → `Uploading...` → `Done ✅`\n\n"
        "**🔥 Powered By @NeonFiles 🔥**"
    )
    await message.reply(help_text)
