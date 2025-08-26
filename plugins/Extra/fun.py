import random
import asyncio
from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

# -----------------------
# CONFIG
# -----------------------
ADMINS = [841851780]  # replace with your Telegram ID(s)
START_BALANCE_USER = 5000
START_BALANCE_ADMIN = 10000

# MongoDB config (use your existing values)
DATABASE_URI = environ.get('DATABASE_URI', "")
DATABASE_NAME = "MyselfNeon"

# -----------------------
# CONNECT TO MONGODB
# -----------------------
mongo_client = MongoClient(DATABASE_URI)
db = mongo_client[DATABASE_NAME]
balances_col = db["balances"]

# -----------------------
# BALANCE HELPERS
# -----------------------
def get_balance(user_id: int) -> int:
    user = balances_col.find_one({"_id": user_id})
    if user:
        return user["balance"]
    else:
        default = START_BALANCE_ADMIN if user_id in ADMINS else START_BALANCE_USER
        balances_col.insert_one({"_id": user_id, "balance": default})
        return default

def update_balance(user_id: int, amount: int):
    balances_col.update_one(
        {"_id": user_id},
        {"$inc": {"balance": amount}},
        upsert=True
    )

def reset_all_balances():
    balances_col.update_many({}, {"$set": {"balance": START_BALANCE_USER}})
    for admin_id in ADMINS:
        balances_col.update_one({"_id": admin_id}, {"$set": {"balance": START_BALANCE_ADMIN}}, upsert=True)

# -----------------------
# BALANCE COMMANDS
# -----------------------
@Client.on_message(filters.command(["bal", "balance"]))
async def balance_check(_: Client, message: Message):
    user_id = message.from_user.id
    bal = get_balance(user_id)
    await message.reply_text(f"💰 Your balance: {bal} coins")

@Client.on_message(filters.command("resetbal"))
async def reset_bal(_: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        return await message.reply_text("🚫 Only admins can use this!")
    reset_all_balances()
    await message.reply_text("♻️ All balances have been reset to defaults!")

# -----------------------
# ADDMONEY (Admin Only)
# -----------------------
@Client.on_message(filters.command(["addbal", "addmoney"]))
async def addmoney(_: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        return await message.reply_text("🚫 Only admins can use this!")

    args = message.text.split()
    if len(args) < 3:
        return await message.reply_text("Usage: /addbal <user_id> <amount>")

    target = int(args[1])
    amount = int(args[2])
    update_balance(target, amount)
    await message.reply_text(f"✅ Added {amount} coins to user {target}")

# -----------------------
# LEADERBOARD (/lb)
# -----------------------
@Client.on_message(filters.command(["lb"]))
async def leaderboard(client: Client, message: Message):
    top_users = balances_col.find().sort("balance", -1).limit(10)
    text = "🏆 **Top 10 Richest Users**\n\n"

    for i, user in enumerate(top_users, start=1):
        uid = user["_id"]
        bal = user["balance"]
        try:
            user_obj = await client.get_users(int(uid))
            name = f"@{user_obj.username}" if user_obj.username else user_obj.first_name
        except:
            name = f"User {uid}"
        text += f"{i}. {name} → {bal} 💰\n"

    await message.reply_text(text)

# -----------------------
# ROCK PAPER SCISSORS
# -----------------------
RPS_EMOJI = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}

def rps_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🪨 Rock", callback_data="rps:rock"),
        InlineKeyboardButton("📄 Paper", callback_data="rps:paper"),
        InlineKeyboardButton("✂️ Scissors", callback_data="rps:scissors")
    ]])

@Client.on_message(filters.command(["rps"]))
async def rps_start(_: Client, message: Message):
    await message.reply_text("Choose your move:", reply_markup=rps_keyboard(), quote=True)

def _rps_result(user: str, bot: str) -> str:
    if user == bot:
        return "draw"
    wins = {("rock", "scissors"), ("paper", "rock"), ("scissors", "paper")}
    return "win" if (user, bot) in wins else "lose"

@Client.on_callback_query(filters.regex("^rps:(rock|paper|scissors)$"))
async def rps_play(client: Client, cq: CallbackQuery):
    user_id = cq.from_user.id
    user_choice = cq.data.split(":")[1]
    bot_choice = random.choice(["rock", "paper", "scissors"])
    outcome = _rps_result(user_choice, bot_choice)

    reward = 0
    if outcome == "win":
        reward = 2000
        update_balance(user_id, reward)
    elif outcome == "lose":
        reward = -1000
        update_balance(user_id, reward)

    txt = (
        f"**Rock-Paper-Scissors**\n"
        f"You: {RPS_EMOJI[user_choice]}  vs  Bot: {RPS_EMOJI[bot_choice]}\n\n"
        f"Result: **{'You Win 🎉' if outcome=='win' else 'Draw 😐' if outcome=='draw' else 'You Lose 💀'}**\n"
        f"Balance Change: {reward}\n"
        f"Your Balance: {get_balance(user_id)} 💰"
    )
    await cq.message.edit_text(txt, reply_markup=rps_keyboard())
    await cq.answer()

# -----------------------
# ROULETTE
# -----------------------
@Client.on_message(filters.command(["roulette","rlt"]))
async def roulette(_: Client, message: Message):
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) < 3:
        return await message.reply_text("Usage: /roulette <red/black> <amount>")

    choice, amount = args[1].lower(), int(args[2])
    if get_balance(user_id) < amount:
        return await message.reply_text("Not enough balance!")

    outcome = random.choice(["red", "black"])
    if outcome == choice:
        update_balance(user_id, amount)
        result = f"🎉 You won {amount}!"
    else:
        update_balance(user_id, -amount)
        result = f"💀 You lost {amount}!"

    await message.reply_text(f"🎰 **Roulette Result**\nLanded: {outcome.upper()}\n{result}\nBalance: {get_balance(user_id)} 💰")

# -----------------------
# CHICKEN FIGHT
# -----------------------
@Client.on_message(filters.command(["chickfight","cf"]))
async def chick_fight(_: Client, message: Message):
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) < 2:
        return await message.reply_text("Usage: /chickfight or /cf <amount>")

    amount = int(args[1])
    if get_balance(user_id) < amount:
        return await message.reply_text("Not enough balance!")

    await message.reply_text("🐔 Two chickens are fighting...")
    await asyncio.sleep(2)
    winner = random.choice(["you", "bot"])

    if winner == "you":
        update_balance(user_id, amount)
        result = f"🎉 Your chicken won! You earned {amount}."
    else:
        update_balance(user_id, -amount)
        result = f"💀 Your chicken lost! You lost {amount}."

    await message.reply_text(f"🐓 **Chicken Fight Result**\n{result}\nBalance: {get_balance(user_id)} 💰")
