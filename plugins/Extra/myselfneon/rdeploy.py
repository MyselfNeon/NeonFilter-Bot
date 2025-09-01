# render_deploy_plugin_safe.py
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import ADMINS

# ----------------------------
# CONFIG
# ----------------------------
RENDER_API_KEY = ""  # Leave empty if not using Render
SERVICE_ID = ""      # Leave empty if not using Render
ADMIN_ONLY = True
LOG_TRUNCATE = 3000
# ----------------------------

# Check if plugin is enabled
PLUGIN_ENABLED = bool(RENDER_API_KEY and SERVICE_ID)

def is_admin(user_id):
    return not ADMIN_ONLY or user_id in ADMINS

def get_latest_deploy():
    if not PLUGIN_ENABLED:
        return None, "Render not configured."
    url = f"https://api.render.com/v1/services/{SERVICE_ID}/deploys?limit=1"
    headers = {"Authorization": f"Bearer {RENDER_API_KEY}"}
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        return None, resp.text
    return resp.json()[0], None

def trigger_deploy():
    if not PLUGIN_ENABLED:
        return None, "Render not configured."
    url = f"https://api.render.com/v1/services/{SERVICE_ID}/deploys"
    headers = {"Authorization": f"Bearer {RENDER_API_KEY}", "Content-Type": "application/json"}
    data = {"clearCache": False}
    resp = requests.post(url, headers=headers, json=data)
    if resp.status_code != 201:
        return None, resp.text
    return resp.json(), None

def build_buttons(deploy):
    buttons = [
        [InlineKeyboardButton("🚀 Deploy Latest", callback_data="deploy_now")],
        [InlineKeyboardButton("📊 Status", callback_data="deploy_status")]
    ]
    if deploy['status'] == 'failed':
        buttons.append([InlineKeyboardButton("📝 View Logs", callback_data="deploy_logs")])
    return InlineKeyboardMarkup(buttons)

# ----------------------------
# /rdeploy DASHBOARD
# ----------------------------

@Client.on_message(filters.command("rdeploy") & filters.private)
async def rdeploy_dashboard(client, message):
    if not PLUGIN_ENABLED:
        return  # Plugin not configured, silently ignore

    if not is_admin(message.from_user.id):
        await message.reply_text("❌ You are not allowed to use this command.")
        return

    deploy, error = get_latest_deploy()
    if error:
        await message.reply_text(f"❌ {error}")
        return

    text = (
        f"**Render Deploy Dashboard**\n\n"
        f"Commit: `{deploy['commit']}`\n"
        f"Branch: `{deploy['branch']}`\n"
        f"Status: `{deploy['status']}`"
    )
    await message.reply_text(text, reply_markup=build_buttons(deploy))

# ----------------------------
# CALLBACKS
# ----------------------------

@Client.on_callback_query(filters.regex("deploy_now"))
async def cb_deploy_now(client, callback: CallbackQuery):
    if not PLUGIN_ENABLED:
        await callback.answer("❌ Render not configured.", show_alert=True)
        return

    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Not allowed", show_alert=True)
        return

    deploy, error = trigger_deploy()
    if error:
        await callback.answer(f"❌ {error}", show_alert=True)
        return

    await callback.answer("✅ Deploy triggered!")
    text = (
        f"🚀 Deploy Started!\n"
        f"Commit: `{deploy['commit']}`\n"
        f"Branch: `{deploy['branch']}`\n"
        f"Status: `{deploy['status']}`"
    )
    await callback.message.edit_text(text, reply_markup=build_buttons(deploy))

@Client.on_callback_query(filters.regex("deploy_status"))
async def cb_deploy_status(client, callback: CallbackQuery):
    if not PLUGIN_ENABLED:
        await callback.answer("❌ Render not configured.", show_alert=True)
        return

    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Not allowed", show_alert=True)
        return

    deploy, error = get_latest_deploy()
    if error:
        await callback.answer(f"❌ {error}", show_alert=True)
        return

    await callback.answer(f"📊 Status: {deploy['status']}", show_alert=True)

@Client.on_callback_query(filters.regex("deploy_logs"))
async def cb_deploy_logs(client, callback: CallbackQuery):
    if not PLUGIN_ENABLED:
        await callback.answer("❌ Render not configured.", show_alert=True)
        return

    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Not allowed", show_alert=True)
        return

    deploy, error = get_latest_deploy()
    if error:
        await callback.answer(f"❌ {error}", show_alert=True)
        return

    if deploy['status'] != 'failed':
        await callback.answer("✅ Latest deploy did not fail!", show_alert=True)
        return

    logs_url = deploy.get('logsUrl')
    if not logs_url:
        await callback.answer("❌ No logs available", show_alert=True)
        return

    resp = requests.get(logs_url)
    if resp.status_code != 200:
        await callback.answer("❌ Failed to fetch logs", show_alert=True)
        return

    logs_text = resp.text[:LOG_TRUNCATE]
    if len(resp.text) > LOG_TRUNCATE:
        logs_text += "\n\n...Logs truncated..."

    await callback.answer("📝 Showing logs", show_alert=True)
    await callback.message.reply_text(
        f"⚠️ Deploy failed logs (truncated):\n```\n{logs_text}\n```",
        parse_mode="markdown"
      )

