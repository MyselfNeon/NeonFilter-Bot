#Fun and Games.py
import random
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
START_BALANCE_USER = 25000
START_BALANCE_ADMIN = 50000

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
    await message.reply_text(f"**🏧 __Your Balance:\n\n💸 {bal} ₹__**")

@Client.on_message(filters.command("resetbal"))
async def reset_bal(_: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        return await message.reply_text("**🚫 __Only Admins Can Use This !__**")
    reset_all_balances()
    await message.reply_text("**__Amigo Samigo 🖐️ \n\nAll Balances Have Been Reset To Defaults !!__ ♻️♻️**")

@Client.on_message(filters.command(["addbal"]))
async def addmoney(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        return await message.reply_text("**🚫 __Only Admins Can Use This !__**")

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

    await message.reply_text(f"**__Added {amount} ₹ to {name} ({target})__ ✅**")

# -----------------------
# LEADERBOARD
# -----------------------
@Client.on_message(filters.command(["lb"]))
async def leaderboard(client: Client, message: Message):
    top_users = list(balances_col.find().sort("balance", -1).limit(10))
    text = "🏆 **__Top 10 Richest Users__**\n\n"
    for i, user in enumerate(top_users, start=1):
        uid = user["_id"]
        bal = user["balance"]
        try:
            u = await client.get_users(int(uid))
            name = f"@{u.username}" if u.username else u.first_name
        except:
            name = f"User {uid}"
        text += f"**__{i}. {name} - {bal} ₹__**\n"
    await message.reply_text(text)

# -----------------------
# ROCK PAPER SCISSORS
# -----------------------
RPS_EMOJI = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}

def rps_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🪨", callback_data="rps:rock"),
        InlineKeyboardButton("📄", callback_data="rps:paper"),
        InlineKeyboardButton("✂️", callback_data="rps:scissors")
    ]])

@Client.on_message(filters.command(["rps"]))
async def rps_start(_: Client, message: Message):
    await message.reply_text("**__Lets Start This Game 😁\n\nChoose Your Ultimate Move__**", reply_markup=rps_keyboard(), quote=True)

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
        f"**__Rock-Paper-Scissors__**\n\n"
        f"**__You:__  {RPS_EMOJI[user_choice]}  __vs  Bot:__  {RPS_EMOJI[bot_choice]}**\n\n"
        f"**__🎲 Result: {'You Win 🎉' if outcome=='win' else 'Draw 😐' if outcome=='draw' else 'You Lose 💀'}__**\n"
        f"**__💰 Balance Change: {reward}__**\n\n"
        f"**__🏧 Your Balance: {get_balance(user_id)} ₹__**"
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
        return await message.reply_text("**__How To Use Me__ 🫠\n\n__/roulette Red/Black Amount|All|Half__**")

    choice = args[1].lower()
    if choice not in ["red", "black"]:
        return await message.reply_text("**❌ __Invalid Choice !! Use Red Or Black__**")

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
            return await message.reply_text("**__Invalid Amount ❌\n\nUse a Number, All, Or Half__**")

    if amount <= 0:
        return await message.reply_text("**❌ __You Must Bet More Than 0 ₹__**")
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
        return await message.reply_text("** __Usage 🤔\n\n/chickfight Amount|All|Half__**")
    
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
            return await message.reply_text("**__Invalid Amount ❌\n\nUse a Number, All, or Half__**")
    
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
        "<blockquote>**‣ 𝐆𝐀𝐌𝐄𝐒 𝐌𝐄𝐍𝐔**</blockquote>\n\n"
        "**🏧 __Balance System__**\n\n"
        "• __/bal **Or** /balance - **Check Balance__**\n"
        "• __/lb - **Show LeaderBoard__**\n"
        "• __/addbal - **Add Money (Admin only)__**\n"
        "• __/resetbal - **Reset All (Admin only)__**\n\n"
        
        "**🎲 __Games__**\n\n"
        "• __/rps - **Rock-Paper-Scissors__**\n"
        "• __/roulette - **Bet On Roulette Colors__**\n"
        "• __/chickfight - **Chicken Fight__ 🐔**\n\n"
        
        "**__Enjoy The Games And Try To Climb The Leaderboard !!__\n\n🔥 __Powered By @NeonFiles__ 🔥**"
    )
    await message.reply_text(text)
    
