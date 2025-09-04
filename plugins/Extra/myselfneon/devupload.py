from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

class DevUploadPlugin:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.chat_files = {}  # {chat_id: [file_dict]}

    # ----- Set or update API -----
    async def set_api(self, client, message, api_key=None):
        if not api_key:
            await message.reply("⚠️ Please provide a valid API key. Usage: /api <your_key>")
            return
        self.api_key = api_key
        await message.reply("✅ DevUpload API key set successfully!")

    # ----- Helper to check API -----
    async def _check_api(self, message):
        if not self.api_key:
            await message.reply("⚠️ DevUpload API key not configured. Please set your API key using /api <your_key>")
            return False
        return True

    # ----- Upload -----
    async def upload_file(self, client, message, file_path=None, link=None):
        if not await self._check_api(message):
            return
        # Here call DevUpload API using self.api_key
        file_info = {"id": "abc123", "name": "demo.txt", "size": 12345, "uploader": message.from_user.id}
        chat_id = message.chat.id
        self.chat_files.setdefault(chat_id, []).append(file_info)
        await message.reply(f"File uploaded: {file_info['name']} ({file_info['size']} bytes)")
        return file_info

    # ----- Delete -----
    async def delete_file(self, client, message, number):
        if not await self._check_api(message):
            return
        chat_id = message.chat.id
        files = self.chat_files.get(chat_id, [])
        if 0 < number <= len(files):
            file_info = files.pop(number-1)
            await message.reply(f"Deleted: {file_info['name']}")
        else:
            await message.reply("Invalid file number.")

    # ----- Rename -----
    async def rename_file(self, client, message, number, new_name):
        if not await self._check_api(message):
            return
        chat_id = message.chat.id
        files = self.chat_files.get(chat_id, [])
        if 0 < number <= len(files):
            file_info = files[number-1]
            old_name = file_info['name']
            file_info['name'] = new_name
            await message.reply(f"Renamed: {old_name} → {new_name}")
        else:
            await message.reply("Invalid file number.")

    # ----- List Files -----
    async def list_files(self, client, message, page=1):
        if not await self._check_api(message):
            return
        chat_id = message.chat.id
        files = self.chat_files.get(chat_id, [])
        per_page = 10
        start = (page-1)*per_page
        end = start+per_page
        page_files = files[start:end]
        if not page_files:
            await message.reply("No files found.")
            return

        text = "\n".join([f"{i+1}. {f['name']} - {f['size']} bytes" for i, f in enumerate(page_files, start=start)])
        keyboard = []
        if start > 0:
            keyboard.append(InlineKeyboardButton("Prev", callback_data=f"dfile_{page-1}"))
        if end < len(files):
            keyboard.append(InlineKeyboardButton("Next", callback_data=f"dfile_{page+1}"))

        await message.reply(
            text,
            reply_markup=InlineKeyboardMarkup([keyboard]) if keyboard else None
        )

    # ----- Stats -----
    async def stats(self, client, message):
        if not await self._check_api(message):
            return
        chat_id = message.chat.id
        files = self.chat_files.get(chat_id, [])
        total_size = sum(f['size'] for f in files)
        await message.reply(f"Total files: {len(files)}\nTotal size: {total_size} bytes")

    # ----- User Files -----
    async def user_files(self, client, message):
        if not await self._check_api(message):
            return
        chat_id = message.chat.id
        user_id = message.from_user.id
        files = [f for f in self.chat_files.get(chat_id, []) if f['uploader'] == user_id]
        if not files:
            await message.reply("You haven't uploaded any files.")
            return
        text = "\n".join([f"{i+1}. {f['name']} - {f['size']} bytes" for i, f in enumerate(files)])
        await message.reply(text)

    # ----- Help -----
    async def help(self, client, message):
        help_text = """
<b>📁 DevUpload Plugin Commands</b>

/dupload - Reply to a file or link to upload
/duser - Show your uploaded files
/dstats - Show chat stats (total files & size)
/ddel {number} - Delete a file by number
/dfile - List all uploaded files (Next/Prev buttons if >10)
/drename {number} {new_name} - Rename a file by number
/api <your_key> - Set or update DevUpload API key
/dhelp - Show this help message
"""
        await message.reply(help_text)
        
