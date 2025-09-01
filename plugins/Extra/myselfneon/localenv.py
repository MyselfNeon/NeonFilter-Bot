import os
from pyrogram import Client, filters
from pyrogram.types import Message
from pymongo import MongoClient
from info import DATABASE_URI, DATABASE_NAME, ADMINS

# -------------------
# MongoDB setup
# -------------------
mongo_client = MongoClient(DATABASE_URI)
db = mongo_client[DATABASE_NAME]
env_collection = db.get_collection("env_vars")  # only this collection

# -------------------
# Load envs from MongoDB at startup
# -------------------
for item in env_collection.find():
    os.environ[item["var_name"]] = item["var_value"]

# -------------------
# Helper: Admin check
# -------------------
def is_admin(user_id):
    return user_id in ADMINS

# -------------------
# /setenv (Admin Only)
# -------------------
@Client.on_message(filters.command("setenv") & filters.private)
async def set_env(bot: Client, message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply_text("**❌ You are not authorized.**")
    if len(message.command) < 3:
        return await message.reply_text(
            "**❌ Usage:**\n/setenv VAR_NAME VAR_VALUE"
        )
    var_name = message.command[1].strip()
    var_value = " ".join(message.command[2:]).strip()
    try:
        os.environ[var_name] = var_value
        env_collection.update_one(
            {"var_name": var_name},
            {"$set": {"var_value": var_value}},
            upsert=True
        )
        await message.reply_text(
            f"**✅ Set env:** `{var_name} = {var_value}`\n"
            "⚠️ Restart bot to apply."
        )
    except Exception as e:
        await message.reply_text(f"**❌ Failed:** `{e}`")

# -------------------
# /getenvs (Admin Only)
# -------------------
@Client.on_message(filters.command("getenvs") & filters.private)
async def get_envs(bot: Client, message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply_text("**❌ You are not authorized.**")
    env_list = "\n".join(f"{item['var_name']} = {item['var_value']}" for item in env_collection.find())
    if not env_list:
        env_list = "**ℹ️ No env variables found.**"
    await message.reply_text(f"**📋 Env variables:**\n{env_list}")

# -------------------
# /delenv (Admin Only)
# -------------------
@Client.on_message(filters.command("delenv") & filters.private)
async def del_env(bot: Client, message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply_text("**❌ You are not authorized.**")
    if len(message.command) != 2:
        return await message.reply_text("**❌ Usage:**\n/delenv VAR_NAME")
    var_name = message.command[1].strip()
    result = env_collection.delete_one({"var_name": var_name})
    os.environ.pop(var_name, None)
    if result.deleted_count:
        await message.reply_text(f"**✅ Deleted env:** `{var_name}`")
    else:
        await message.reply_text(f"**⚠️ Variable `{var_name}` not found.**")
        
