import random
import asyncio
import json
import os
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

# -----------------------
# CONFIG
# -----------------------
ADMINS = [841851780]  # replace with your Telegram ID(s)
START_BALANCE_USER = 5000
START_BALANCE_ADMIN = 10000
DATA_FILE = "balances.json"

# -----------------------
# BALANCE SYSTEM (Persistent)
# -----------------------
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        BALANCES = json.load(f)
else:
    BALANCES = {}

def save_balances():
    with open(DATA_FILE, "w") as f:
        json.dump(BALANCES, f)

def get_balance(user_id: int) -> int:
    if str(user_id) not in BALANCES:
        BALANCES[str(user_id)] = START_BALANCE_ADMIN if user_id in ADMINS else START_BALANCE_USER
        save_balances()
    return BALANCES[str(user_id)]

def update_balance(user_id: int, amount: int):
    BALANCES[str(user_id)] = get_balance(user_id) + amount
    save_balances()

def reset_all_balances():
    global BALANCES
    BALANCES = {}
    save_balances()

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
        return await message.reply_text("Usage: /chickfight <amount>")

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

# -----------------------
# LEADERBOARD (/lb)
# -----------------------
@Client.on_message(filters.command(["lb"]))
async def leaderboard(client: Client, message: Message):
    top_users = sorted(BALANCES.items(), key=lambda x: x[1], reverse=True)[:10]
    text = "🏆 **Top 10 Richest Users**\n\n"

    for i, (uid, bal) in enumerate(top_users, start=1):
        try:
            user = await client.get_users(int(uid))
            name = f"@{user.username}" if user.username else user.first_name
        except:
            name = f"User {uid}"

        text += f"{i}. {name} → {bal} 💰\n"

    await message.reply_text(text)

# -----------------------
# ADDMONEY (Admin Only)
# -----------------------
@Client.on_message(filters.command(["addmoney"]))
async def addmoney(_: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        return await message.reply_text("🚫 Only admins can use this!")

    args = message.text.split()
    if len(args) < 3:
        return await message.reply_text("Usage: /addmoney <user_id> <amount>")

    target = int(args[1])
    amount = int(args[2])
    update_balance(target, amount)
    await message.reply_text(f"✅ Added {amount} coins to user {target}")
