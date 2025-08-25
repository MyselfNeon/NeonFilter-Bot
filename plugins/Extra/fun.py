import random
import asyncio
import json
import os
import time
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

# -----------------------
# CONFIG
# -----------------------
BANK_FILE = "bank.json"
XP_FILE = "xp.json"
DAILY_FILE = "daily.json"

ADMINS = [841851780]  # replace with your IDs

# -----------------------
# JSON Helpers
# -----------------------
def load_json(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)

BANK = load_json(BANK_FILE)
XP = load_json(XP_FILE)
DAILY = load_json(DAILY_FILE)

# -----------------------
# BANK FUNCTIONS
# -----------------------
def get_balance(user_id: int) -> int:
    return BANK.get(str(user_id), 100)

def update_balance(user_id: int, amount: int):
    BANK[str(user_id)] = get_balance(user_id) + amount
    save_json(BANK_FILE, BANK)

def set_balance(user_id: int, amount: int):
    BANK[str(user_id)] = amount
    save_json(BANK_FILE, BANK)

# -----------------------
# XP FUNCTIONS
# -----------------------
def get_xp(user_id: int) -> int:
    return XP.get(str(user_id), 0)

def add_xp(user_id: int, amount: int):
    XP[str(user_id)] = get_xp(user_id) + amount
    save_json(XP_FILE, XP)

def get_level(user_id: int) -> int:
    return get_xp(user_id) // 100

# -----------------------
# DAILY REWARD
# -----------------------
def can_claim_daily(user_id: int) -> bool:
    last = DAILY.get(str(user_id), 0)
    return (time.time() - last) >= 86400  # 24h

def set_daily(user_id: int):
    DAILY[str(user_id)] = time.time()
    save_json(DAILY_FILE, DAILY)

# -----------------------
# ADMIN CHECK
# -----------------------
def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

# -----------------------
# ROCK PAPER SCISSORS
# -----------------------
RPS_EMOJI = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}

def rps_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("🪨 Rock", callback_data="rps:rock"),
            InlineKeyboardButton("📄 Paper", callback_data="rps:paper"),
            InlineKeyboardButton("✂️ Scissors", callback_data="rps:scissors"),
        ]]
    )

@Client.on_message(filters.command(["rps"]))
async def rps_start(_: Client, message: Message):
    await message.reply_text("Choose your move:", reply_markup=rps_keyboard(), quote=True)

def _rps_result(user: str, bot: str) -> str:
    if user == bot:
        return "draw"
    wins = {("rock", "scissors"), ("paper", "rock"), ("scissors", "paper")}
    return "win" if (user, bot) in wins else "lose"

@Client.on_callback_query(filters.regex("^rps:(rock|paper|scissors)$"))
async def rps_play(_: Client, cq: CallbackQuery):
    user_id = cq.from_user.id
    user_choice = cq.data.split(":")[1]
    bot_choice = random.choice(["rock", "paper", "scissors"])
    outcome = _rps_result(user_choice, bot_choice)

    reward = 0
    if outcome == "win":
        reward = 20
        update_balance(user_id, reward)
    elif outcome == "lose":
        reward = -10
        update_balance(user_id, reward)

    add_xp(user_id, 10)

    txt = (
        f"**Rock-Paper-Scissors**\n"
        f"You: {RPS_EMOJI[user_choice]}  vs  Bot: {RPS_EMOJI[bot_choice]}\n\n"
        f"Result: **{'You Win 🎉' if outcome=='win' else 'Draw 😐' if outcome=='draw' else 'You Lose 💀'}**\n"
        f"Balance Change: {reward}\n"
        f"Your Balance: {get_balance(user_id)} 💰\n"
        f"XP: {get_xp(user_id)} | Level: {get_level(user_id)}"
    )
    await cq.message.edit_text(txt, reply_markup=rps_keyboard())
    await cq.answer()

# -----------------------
# ROULETTE GAME
# -----------------------
@Client.on_message(filters.command(["roulette"]))
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

    add_xp(user_id, 15)

    await message.reply_text(
        f"🎰 **Roulette Result**\nLanded: {outcome.upper()}\n{result}\nBalance: {get_balance(user_id)} 💰\nXP: {get_xp(user_id)} | Level: {get_level(user_id)}"
    )

# -----------------------
# CHICKEN FIGHT
# -----------------------
@Client.on_message(filters.command(["chickfight"]))
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

    add_xp(user_id, 20)

    await message.reply_text(f"🐓 **Chicken Fight Result**\n{result}\nBalance: {get_balance(user_id)} 💰\nXP: {get_xp(user_id)} | Level: {get_level(user_id)}")

# -----------------------
# BALANCE COMMANDS
# -----------------------
@Client.on_message(filters.command(["balance"]))
async def check_balance(_: Client, message: Message):
    user_id = message.from_user.id
    await message.reply_text(f"💰 Your balance: {get_balance(user_id)} coins\nXP: {get_xp(user_id)} | Level: {get_level(user_id)}")

@Client.on_message(filters.command(["earn"]))
async def earn(_: Client, message: Message):
    user_id = message.from_user.id
    amount = random.randint(5, 25)
    update_balance(user_id, amount)
    add_xp(user_id, 5)
    await message.reply_text(f"✨ You worked and earned {amount} coins!\nNew balance: {get_balance(user_id)} 💰 | XP: {get_xp(user_id)}")

# -----------------------
# DAILY REWARD
# -----------------------
@Client.on_message(filters.command(["daily"]))
async def daily(_: Client, message: Message):
    user_id = message.from_user.id
    if not can_claim_daily(user_id):
        return await message.reply_text("⏳ You already claimed daily today! Try again later.")

    reward = random.randint(50, 100)
    update_balance(user_id, reward)
    add_xp(user_id, 30)
    set_daily(user_id)

    await message.reply_text(f"🎁 Daily reward: {reward} coins!\nBalance: {get_balance(user_id)} 💰 | XP: {get_xp(user_id)} | Level: {get_level(user_id)}")

# -----------------------
# LEADERBOARD
# -----------------------
@Client.on_message(filters.command(["top", "leaderboard"]))
async def leaderboard(client: Client, message: Message):
    # Sort by balance
    top_users = sorted(BANK.items(), key=lambda x: x[1], reverse=True)[:10]
    text = "🏆 Top 10 Richest Users\n"
    for i, (uid, bal) in enumerate(top_users, start=1):
        try:
            user_obj = await client.get_users(int(uid))
            name = user_obj.first_name if user_obj else str(uid)
        except:
            name = str(uid)
        xp = XP.get(uid, 0)
        lvl = xp // 100
        text += f"{i}. {name} → {bal} 💰 | Lvl {lvl}\n"
    await message.reply_text(text)

# -----------------------
# ADMIN ECONOMY COMMANDS
# -----------------------
@Client.on_message(filters.command(["givemoney"]))
async def give_money(_: Client, message: Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return await message.reply_text("🚫 You need to be admin to use this command!")

    args = message.text.split()
    if len(args) < 3:
        return await message.reply_text("Usage: /givemoney <user_id> <amount>")

    target, amount = int(args[1]), int(args[2])
    update_balance(target, amount)
    await message.reply_text(f"✅ Gave {amount} coins to {target}")

@Client.on_message(filters.command(["removemoney"]))
async def remove_money(_: Client, message: Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return await message.reply_text("🚫 You need to be admin to use this command!")

    args = message.text.split()
    if len(args) < 3:
        return await message.reply_text("Usage: /removemoney <user_id> <amount>")

    target, amount = int(args[1]), int(args[2])
    update_balance(target, -amount)
    await message.reply_text(f"✅ Removed {amount} coins from {target}")

@Client.on_message(filters.command(["setmoney"]))
async def set_money(_: Client, message: Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return await message.reply_text("🚫 You need to be admin to use this command!")

    args = message.text.split()
    if len(args) < 3:
        return await message.reply_text("Usage: /setmoney <user_id> <amount>")

    target, amount = int(args[1]), int(args[2])
    set_balance(target, amount)
    await message.reply_text(f"✅ Set {target}'s balance to {amount}")

# -----------------------
# AUTO XP ON MESSAGES (30s cooldown)
# -----------------------
LAST_XP = {}

@Client.on_message(filters.text & ~filters.command(["rps","roulette","chickfight","balance","earn","daily","top","givemoney","removemoney","setmoney"]))
async def auto_xp(_: Client, message: Message):
    user_id = message.from_user.id
    now = time.time()
    last = LAST_XP.get(user_id, 0)
    if now - last >= 30:  # cooldown 30s
        xp_gain = random.randint(1, 3)
        add_xp(user_id, xp_gain)
        LAST_XP[user_id] = now