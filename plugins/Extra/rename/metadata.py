import os
import subprocess
from pyrogram import Client, filters
from pyrogram.types import Message
from mutagen.easyid3 import EasyID3
from mutagen.mp4 import MP4
from mutagen.flac import FLAC

# Command: /metadata Author=Neon Video=MyVideoTitle Audio=MySong Subtitle=English
@Client.on_message(filters.command("metadata") & filters.reply)
async def edit_metadata(client: Client, message: Message):
    if not message.reply_to_message.document and not message.reply_to_message.audio and not message.reply_to_message.video:
        return await message.reply_text("⚠️ Reply to a file (audio/video) with `/metadata` command.\n\nExample:\n`/metadata Author=Neon Video=CoolTitle`")

    # Download file
    file_msg = message.reply_to_message
    file_path = await file_msg.download()
    new_file_path = "edited_" + os.path.basename(file_path)

    # Parse metadata arguments
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.reply_text("⚠️ Provide metadata as key=value.\nExample: `/metadata Author=Neon Video=Cool`")

    metadata_input = args[1].split()
    metadata_dict = {}
    for item in metadata_input:
        if "=" in item:
            k, v = item.split("=", 1)
            metadata_dict[k] = v

    try:
        # Audio metadata editing
        if file_path.endswith((".mp3", ".wav", ".flac", ".m4a")):
            if file_path.endswith(".mp3"):
                audio = EasyID3(file_path)
                for k, v in metadata_dict.items():
                    audio[k.lower()] = v
                audio.save(new_file_path)

            elif file_path.endswith(".m4a"):
                audio = MP4(file_path)
                for k, v in metadata_dict.items():
                    audio[f"\xa9{k}"] = v
                audio.save(new_file_path)

            elif file_path.endswith(".flac"):
                audio = FLAC(file_path)
                for k, v in metadata_dict.items():
                    audio[k.lower()] = v
                audio.save(new_file_path)

            else:
                os.rename(file_path, new_file_path)

        else:
            # For video/subtitle/others → ffmpeg
            meta_cmd = ["ffmpeg", "-i", file_path, "-map", "0", "-c", "copy"]
            for k, v in metadata_dict.items():
                meta_cmd.extend(["-metadata", f"{k}={v}"])
            meta_cmd.append(new_file_path)

            subprocess.run(meta_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Send file back
        await message.reply_document(new_file_path, caption="✅ Metadata updated!")

    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(new_file_path):
            os.remove(new_file_path)
