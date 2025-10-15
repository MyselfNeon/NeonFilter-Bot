# m3u8_downloader_plugin.py
"""
Standalone Pyrogram plugin: /m3u8
Downloads m3u8 (HLS) streams using yt-dlp and sends the result back to chat.
Usage:
    /m3u8 <url> [| filename.ext]         -> download URL, optional output filename after '|' 
    (reply to a message containing the URL) -> same behavior
Optional: include headers after the URL separated by space, e.g.:
    /m3u8 <url> "User-Agent: ...; Referer: https://..." 
This plugin tries to be informative but won't spam edits (rate-limited updates).
"""
import asyncio
import os
import shlex
import tempfile
import time
import traceback
from pathlib import Path

from pyrogram import Client, filters
from pyrogram.types import Message

# Ensure yt_dlp is installed in your environment
try:
    from yt_dlp import YoutubeDL
except Exception as e:
    raise RuntimeError("yt_dlp module required. Install with `pip install yt-dlp`") from e

# === CONFIG ===
# If you want a different temporary directory, change TEMP_DIR
TEMP_DIR = os.environ.get("M3U8_TEMP_DIR", tempfile.gettempdir())
# Limit progress message updates to once every N seconds to avoid flooding edits
PROGRESS_UPDATE_INTERVAL = 2.0

# Optionally restrict who can use this command by replacing None with a list of user ids:
ALLOWED_USER_IDS = None  # e.g. [12345678, 98765432] or None for everyone

# Helper: determine if a string looks like a URL
def looks_like_url(s: str) -> bool:
    s = s.strip()
    return s.startswith("http://") or s.startswith("https://") or s.startswith("m3u8:")

# Progress info keeper
class ProgressState:
    def __init__(self):
        self.last_edit = 0.0
        self.msg_text = None

# Main handler
@Client.on_message(filters.command("m3u8") & (filters.private | filters.group))
async def m3u8_handler(client: Client, message: Message):
    # Permission check (optional)
    if ALLOWED_USER_IDS and message.from_user and message.from_user.id not in ALLOWED_USER_IDS:
        await message.reply_text("You are not allowed to use this command.")
        return

    # Extract raw text to find url / filename / headers
    text = message.text or ""
    args = text.split(maxsplit=1)[1:] if len(text.split()) > 1 else []

    # If message is a reply and no args, try to pull URL from replied message
    if not args and message.reply_to_message:
        # prefer caption or text
        reply_text = message.reply_to_message.text or message.reply_to_message.caption or ""
        args = [reply_text.strip()] if reply_text.strip() else []

    if not args:
        await message.reply_text("Usage: `/m3u8 <url> [| filename.ext]`\nYou can also reply to a message containing the m3u8 link.", quote=True)
        return

    raw = args[0].strip()

    # Allow syntax: <url> | filename.ext  OR <url> "Header: value; Header2: value"
    custom_filename = None
    custom_headers = None

    # Split by '|' first for explicit filename selection
    if "|" in raw:
        url_part, filename_part = raw.split("|", 1)
        url = url_part.strip()
        custom_filename = filename_part.strip().strip('"').strip("'")
    else:
        # no filename; maybe headers are present in quotes
        # We'll try to detect quoted header string after space
        pieces = shlex.split(raw)
        url = pieces[0]
        if len(pieces) > 1:
            # treat the rest as headers string (e.g. "User-Agent: ...; Referer: ...")
            possible_headers = " ".join(pieces[1:])
            custom_headers = possible_headers.strip().strip('"').strip("'")

    # fallback: if `raw` itself looks like a URL and there are more words in the message text, append them
    if not looks_like_url(url):
        # try to find url anywhere in original message or the replied message
        found = None
        words = (message.text or "") + " " + (message.reply_to_message.text or "" if message.reply_to_message else "")
        for w in words.split():
            if looks_like_url(w):
                found = w
                break
        if found:
            url = found
        else:
            await message.reply_text("Couldn't find a valid URL in your message. Please pass a direct m3u8 URL.", quote=True)
            return

    # Create a unique temp dir per download
    session_dir = Path(TEMP_DIR) / f"m3u8_{int(time.time())}_{message.message_id}"
    session_dir.mkdir(parents=True, exist_ok=True)

    status_msg = await message.reply_text(f"⏳ Preparing to download:\n{url}", quote=True)
    progress = ProgressState()

    # Build yt-dlp options
    outtmpl = str(session_dir / "%(title)s.%(ext)s")
    ydl_opts = {
        "outtmpl": outtmpl,
        "format": "best",            # best available format
        "noplaylist": True,
        "merge_output_format": "mp4",# try to merge to mp4 when possible
        "hls_prefer_native": False,  # prefer ffmpeg to handle HLS (more reliable)
        "hls_use_mpegts": True,
        # no console output from yt-dlp, we use progress hook
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [],
        # postprocessors could be added if you want more control
    }

    # If user provided headers, parse them into dict and pass to ydl_opts via 'http_headers'
    if custom_headers:
        try:
            headers = {}
            # Expect headers like: "User-Agent: xyz; Referer: https://..."
            for part in custom_headers.split(";"):
                if ":" in part:
                    k, v = part.split(":", 1)
                    headers[k.strip()] = v.strip()
            if headers:
                ydl_opts["http_headers"] = headers
        except Exception:
            # ignore headers parse errors and continue without custom headers
            pass

    # If user wants a custom filename (and includes an extension), add post-download rename logic
    want_custom_name = bool(custom_filename and "." in custom_filename)

    last_update_time = 0.0

    def ytdl_hook(d):
        # this runs in yt-dlp thread / sync context; we should only prepare text for edit
        nonlocal last_update_time, progress, status_msg
        try:
            status = d.get("status")
            now = time.time()
            if status == "downloading":
                speed = d.get("speed") or 0
                eta = d.get("eta") or 0
                downloaded_bytes = d.get("downloaded_bytes") or 0
                total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                percent = 0.0
                if total_bytes:
                    try:
                        percent = downloaded_bytes / total_bytes * 100
                    except Exception:
                        percent = 0.0
                _text = f"⏬ Downloading: {d.get('filename', '')}\n" \
                        f"{percent:.2f}% • {downloaded_bytes//1024} KiB of {total_bytes//1024 if total_bytes else '??'} KiB\n" \
                        f"Speed: {speed/1024:.2f} KiB/s • ETA: {int(eta)}s"
                # throttle edits to once every PROGRESS_UPDATE_INTERVAL seconds
                if now - last_update_time >= PROGRESS_UPDATE_INTERVAL:
                    progress.msg_text = _text
                    last_update_time = now
            elif status == "finished":
                progress.msg_text = f"✅ Download finished: {d.get('filename', '')}\nPost-processing..."
            elif status == "error":
                progress.msg_text = f"❌ Error while downloading: {d.get('filename', '')}"
        except Exception:
            # non-fatal; we won't crash yt-dlp because of progress hook
            pass

    ydl_opts["progress_hooks"].append(ytdl_hook)

    # Run the download in a thread to avoid blocking asyncio loop
    loop = asyncio.get_event_loop()
    download_exc = None
    downloaded_file_path = None

    try:
        def run_ydl():
            nonlocal downloaded_file_path
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)  # this downloads
                # info may be a dict for single video
                # determine filename from info
                if info:
                    # yt-dlp can return 'requested_downloads' list in some configs; fallback to ydl.prepare_filename
                    try:
                        fname = ydl.prepare_filename(info)
                    except Exception:
                        # try to find file in session_dir matching pattern
                        matches = list(session_dir.glob("*"))
                        fname = str(matches[0]) if matches else None
                    downloaded_file_path = fname
                # if no info, try to pick any file in session dir
                if not downloaded_file_path:
                    matches = list(session_dir.glob("*"))
                    downloaded_file_path = str(matches[0]) if matches else None

        # start background task
        await loop.run_in_executor(None, run_ydl)

        # Periodically update the status message with progress text available from hook
        # Continue doing this until yt-dlp finishes (downloaded_file_path set)
        # But we already awaited run_in_executor above; hooks updated progress.msg_text during the download
        # To ensure we show latest hook messages (in case they arrived after executor finished), do a final few edits
        if progress.msg_text:
            try:
                await status_msg.edit(progress.msg_text)
            except Exception:
                pass

    except Exception as e:
        download_exc = e
        tb = traceback.format_exc()
        try:
            await status_msg.edit(f"❌ Download failed:\n{str(e)}")
        except Exception:
            pass

    # If an exception happened, cleanup and return
    if download_exc:
        # try to send traceback in private if it's not too long
        try:
            await message.reply_text("Download failed. Check bot logs for details.", quote=True)
        finally:
            # cleanup
            try:
                for p in session_dir.glob("*"):
                    p.unlink()
                session_dir.rmdir()
            except Exception:
                pass
        return

    # If downloaded_file_path is a list or youtube-dl returned playlist, choose the best match
    if not downloaded_file_path:
        # nothing found
        await status_msg.edit("❌ Couldn't find downloaded file after yt-dlp finished.")
        # cleanup
        try:
            for p in session_dir.glob("*"):
                p.unlink()
            session_dir.rmdir()
        except Exception:
            pass
        return

    # If user asked for a custom filename, rename
    downloaded_path = Path(downloaded_file_path)
    if want_custom_name:
        target = session_dir / custom_filename
        try:
            downloaded_path.rename(target)
            downloaded_path = target
        except Exception:
            # if rename fails, ignore and continue with original filename
            pass

    # Send file back to chat
    # Choose send_video if extension indicates a video-like container
    ext = downloaded_path.suffix.lower()
    try:
        await status_msg.edit("📤 Uploading to chat...")
    except Exception:
        pass

    try:
        if ext in {".mp4", ".mkv", ".webm", ".mov", ".ts"}:
            await client.send_video(
                chat_id=message.chat.id,
                video=str(downloaded_path),
                caption=f"Downloaded from: {url}",
                reply_to_message_id=message.message_id
            )
        else:
            # fallback to document
            await client.send_document(
                chat_id=message.chat.id,
                document=str(downloaded_path),
                caption=f"Downloaded from: {url}",
                reply_to_message_id=message.message_id
            )
        await status_msg.delete()
    except Exception as e:
        # If upload fails, show error text and try to upload as document
        try:
            await status_msg.edit(f"⚠️ Upload failed with {e}\nTrying as document...")
            await client.send_document(
                chat_id=message.chat.id,
                document=str(downloaded_path),
                caption=f"Downloaded from: {url}",
                reply_to_message_id=message.message_id
            )
            await status_msg.delete()
        except Exception as e2:
            try:
                await status_msg.edit(f"❌ Upload failed: {e2}")
            except Exception:
                pass

    # Cleanup files
    try:
        for p in session_dir.glob("*"):
            try:
                p.unlink()
            except Exception:
                pass
        try:
            session_dir.rmdir()
        except Exception:
            pass
    except Exception:
        pass
