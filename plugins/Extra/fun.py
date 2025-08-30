allort random
import asyncio
import os
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
from info import DATABASE_NAME  # your existing config

# -----------------------
# CONFIG
# -----------------------
ADMINS = [841851780]  # replace with your Telegram ID(s)
START_BALANCE_USER = 5000
START_BALANCE_ADMIN = 10000

# -----------------------
# MONGODB SETUP
# -----------------------
DATABASE_URI = os.environ.get("DATABASE_URI")
if not DATABASE_URI:
    raise ValueError("DATABASE_URI environment variable is not set!")

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
    default = START_BALANCE_ADMIN if user_id in ADMINS else START_BALANCE_USER
    balances_col.insert_one({"_id": user_id, "balance": default})
    return default

def update_balance(user_id: int, amount: int):
    balances_col.update_one({"_id": user_id}, {"$inc": {"balance": amount}}, upsert=True)

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

@Client.on_message(filters.command(["addbal"]))
async def addmoney(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        return await message.reply_text("🚫 Only admins can use this!")

    args = message.text.split()

    # Case 1: /addbal me <amount>
    if len(args) == 3 and args[1].lower() == "me":
        target = user_id
        amount = int(args[2])

    # Case 2: Reply to a user with /addbal <amount>
    elif len(args) == 2 and message.reply_to_message:
        target = message.reply_to_message.from_user.id
        amount = int(args[1])

    # Case 3: /addbal <user_id> <amount>
    elif len(args) == 3:
        target = int(args[1])
        amount = int(args[2])

    else:
        return await message.reply_text(
            "Usage:\n"
            "`/addbal me <amount>`\n"
            "`/addbal <user_id> <amount>`\n"
            "Or reply to a user with `/addbal <amount>`"
        )

    update_balance(target, amount)

    try:
        u = await client.get_users(target)
        name = f"@{u.username}" if u.username else u.first_name
    except:
        name = f"User {target}"

    await message.reply_text(f"✅ Added {amount} coins to {name} ({target})")

# -----------------------
# LEADERBOARD
# -----------------------
@Client.on_message(filters.command(["lb"]))
async def leaderboard(client: Client, message: Message):
    top_users = list(balances_col.find().sort("balance", -1).limit(10))
    text = "🏆 **Top 10 Richest Users**\n\n"
    for i, user in enumerate(top_users, start=1):
        uid = user["_id"]
        bal = user["balance"]
        try:
            u = await client.get_users(int(uid))
            name = f"@{u.username}" if u.username else u.first_name
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
@Client.on_message(filters.command(["roulette", "rlt"]))
async def roulette(_: Client, message: Message):
    user_id = message.from_user.id
    args = message.text.split()

    if len(args) < 3:
        return await message.reply_text("**⁉️ Usage :** \n/roulette Red/Black Amount|All|Half")

    choice = args[1].lower()
    if choice not in ["red", "black"]:
        return await message.reply_text("**❌ __Invalid Choice !! Use Red or Black__**")

    user_balance = get_balance(user_id)
    bet_arg = args[2].lower()

    if bet_arg == "all":
        amount = user_balance
    elif bet_arg == "half":
        amount = user_balance // 2
    else:
        try:
            amount = int(bet_arg)
        except ValueError:
            return await message.reply_text("**❌ __Invalid Amount ! Use a Number, All, or Half__**")

    if amount <= 0:
        return await message.reply_text("**❌ __You Must Bet More Than 0 ₹ !!__**")
    if user_balance < amount:
        return await message.reply_text("**🚫 __Not Enough Balance !!__**")

    outcome = random.choice(["red", "black"])
    if outcome == choice:
        update_balance(user_id, amount)
        result = f"**🎉 __You Won {amount} ₹__**"
    else:
        update_balance(user_id, -amount)
        result = f"**💀 __You Lost {amount} ₹__**"

    await message.reply_text(
        f"**🎰 Roulette Result**\n\n"
        f"**🎯 __Landed: {outcome.upper()}__**\n"
        f"{result}\n\n"
        f"**🏧 __Balance: {get_balance(user_id)} ₹__**"
    )

# -----------------------
# CHICKEN FIGHT
# -----------------------
@Client.on_message(filters.command(["chickfight", "cf"]))
async def chick_fight(_: Client, message: Message):
    user_id = message.from_user.id
    args = message.text.split()

    if len(args) < 2:
        return await message.reply_text("**⁉️ Usage :**\n/chickfight Amount|All|Half")
    
    user_balance = get_balance(user_id)
    bet_arg = args[1].lower()

    if bet_arg == "all":
        amount = user_balance
    elif bet_arg == "half":
        amount = user_balance // 2
    else:
        try:
            amount = int(bet_arg)
        except ValueError:
            return await message.reply_text("**__Invalid Amount ❌\nUse a Number, All, or Half__**")
    
    if amount <= 0:
        return await message.reply_text("**❌ __You Must Bet More Than 0 ₹__**")
    if user_balance < amount:
        return await message.reply_text("**🚫 __Not Enough Balance !!__**")

    fight_msg = await message.reply_text("**🐔 __Two Chickens Are Fighting ...__**")
    await asyncio.sleep(3)
    await fight_msg.delete()

    winner = random.choice(["you", "bot"])
    if winner == "you":
        update_balance(user_id, amount)
        result = f"**🎉 __Your Chicken Won !!\n😎 You earned {amount} ₹__**"
    else:
        update_balance(user_id, -amount)
        result = f"**💀 __Your Chicken Lost !!\n🥹 You lost {amount} ₹__**"

    await message.reply_text(
        f"🐓 **Chicken Fight Result**\n\n{result}\n\n**🏧 __Balance : {get_balance(user_id)} ₹__**"
    )

# -----------------------
# FUN HELP MENU
# -----------------------
@Client.on_message(filters.command(["funhelp"]))
async def fun_help(_: Client, message: Message):
    text = (
        "🎮 **Fun & Games Menu** 🎮\n\n"
        "💰 Balance System:\n"
        "• `/bal` or `/balance` → Check your balance\n"
        "• `/lb` → Show Top 10 richest users\n"
        "• `/addbal` → (Admin only) Add coins\n"
        "• `/resetbal` → (Admin only) Reset all balances\n\n"
        
        "🎲 Games:\n"
        "• `/rps` → Rock-Paper-Scissors (Win: +2000 | Lose: -1000)\n"
        "• `/roulette <red/black> <amount|all|half>` → Bet on roulette colors\n"
        "• `/chickfight <amount|all|half>` → Bet on a chicken fight 🐔\n\n"
        
        "✨ Enjoy the games and try to climb the leaderboard!"
    )
    await message.reply_text(text)
    
