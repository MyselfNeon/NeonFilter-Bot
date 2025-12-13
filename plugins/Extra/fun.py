# Fun_and_Games_Final.py
import random
import asyncio
import time
import os
import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient
from info import DATABASE_NAME  # Ensure this exists in info.py

# -----------------------
# ⚙️ CONFIGURATION
# -----------------------
ADMINS = [841851780]
START_BALANCE = 500
DAILY_BONUS_AMOUNT = 2000

# RPS Config
RPS_WIN = 2000
RPS_LOSE = 1000  # Deduction on loss
RPS_EMOJI = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}

# -----------------------
# 🗄️ ASYNC MONGODB SETUP
# -----------------------
DATABASE_URI = os.environ.get("DATABASE_URI")
if not DATABASE_URI:
    raise ValueError("DATABASE_URI environment variable is not set!")

mongo_client = AsyncIOMotorClient(DATABASE_URI)
db = mongo_client[DATABASE_NAME]
user_col = db["gamble_users"]

# -----------------------
# 🔧 UTILS & ECONOMY HELPERS
# -----------------------
async def get_data(user_id: int):
    """Fetch user data, insert if new."""
    user = await user_col.find_one({"_id": user_id})
    if not user:
        new_user = {"_id": user_id, "balance": START_BALANCE, "last_daily": None}
        await user_col.insert_one(new_user)
        return new_user
    return user

async def update_balance(user_id: int, amount: int):
    """Safely update user balance."""
    await user_col.update_one({"_id": user_id}, {"$inc": {"balance": amount}}, upsert=True)

async def check_balance(user_id: int) -> int:
    data = await get_data(user_id)
    return data["balance"]

async def parse_bet(user_id, args):
    """Helper to parse 'all', 'half' or specific numbers."""
    balance = await check_balance(user_id)
    if not args:
        return None, "No amount specified."
    
    val = args[0].lower()
    if val == "all":
        amount = balance
    elif val == "half":
        amount = balance // 2
    else:
        try:
            amount = int(val)
        except ValueError:
            return None, "Invalid amount."

    if amount <= 0:
        return None, "Bet must be > 0."
    if balance < amount:
        return None, "Insufficient balance."
    
    return amount, None

# -----------------------
# 💰 ECONOMY COMMANDS
# -----------------------
@Client.on_message(filters.command(["bal", "balance"]))
async def balance_check(client: Client, message: Message):
    user_id = message.from_user.id
    bal = await check_balance(user_id)
    await message.reply_text(f"**🏧 __Your Balance:\n\n💸 {bal:,} ₹__**", quote=True)

@Client.on_message(filters.command(["daily", "bonus"]))
async def daily_reward(client: Client, message: Message):
    user_id = message.from_user.id
    data = await get_data(user_id)
    now = datetime.datetime.now()
    last_claim = data.get("last_daily")
    
    if last_claim:
        delta = now - last_claim
        if delta.total_seconds() < 86400:
            time_left = str(datetime.timedelta(seconds=86400 - delta.total_seconds())).split('.')[0]
            return await message.reply_text(f"**⏳ Come back in `{time_left}`**")

    await user_col.update_one({"_id": user_id}, {"$inc": {"balance": DAILY_BONUS_AMOUNT}, "$set": {"last_daily": now}})
    await message.reply_text(f"**🎉 Daily Bonus Claimed! Added +{DAILY_BONUS_AMOUNT} ₹**")

@Client.on_message(filters.command(["addbal"]) & filters.user(ADMINS))
async def admin_add_bal(client: Client, message: Message):
    try:
        if message.reply_to_message:
            target = message.reply_to_message.from_user.id
            amount = int(message.command[1])
        else:
            target = int(message.command[1])
            amount = int(message.command[2])
        await update_balance(target, amount)
        await message.reply_text(f"**✅ Admin:** Added {amount} to {target}.")
    except:
        await message.reply_text("Usage: `/addbal <userid> <amount>` or reply.")

# -----------------------
# 🐔 GAME 1: CHICKEN FIGHT (Restored)
# -----------------------
@Client.on_message(filters.command(["chickfight", "cf"]))
async def chick_fight(client: Client, message: Message):
    user_id = message.from_user.id
    amount, error = await parse_bet(user_id, message.command[1:])
    if error:
        return await message.reply_text(f"**__Usage:__ /cf Amount/All/Half**")

    # Deduct bet
    await update_balance(user_id, -amount)

    # Fight Animation
    fight_msg = await message.reply_text("**🐔 __Two Chickens Are Fighting ...__**")
    await asyncio.sleep(2)
    
    winner = random.choice(["you", "bot"])
    if winner == "you":
        payout = amount * 2
        await update_balance(user_id, payout)
        await fight_msg.edit_text(
            f"**🐔 Chicken Fight Result**\n\n"
            f"**🎉 __Your Chicken Won !!__**\n"
            f"**😎 Profit: +{amount} ₹**\n\n"
            f"**🏧 Balance: {await check_balance(user_id)} ₹**"
        )
    else:
        await fight_msg.edit_text(
            f"**🐔 Chicken Fight Result**\n\n"
            f"**💀 __Your Chicken Lost !!__**\n"
            f"**🥹 Loss: -{amount} ₹**\n\n"
            f"**🏧 Balance: {await check_balance(user_id)} ₹**"
        )

# -----------------------
# 🔴 GAME 2: ROULETTE (Restored)
# -----------------------
@Client.on_message(filters.command(["roulette", "rlt"]))
async def roulette(client: Client, message: Message):
    user_id = message.from_user.id
    args = message.text.split()
    
    if len(args) < 3:
        return await message.reply_text("**__Usage:__ /roulette Red/Black Amount**")

    choice = args[1].lower()
    if choice not in ["red", "black"]:
        return await message.reply_text("**❌ Invalid Color! Use Red or Black**")

    # Use modern parser for bet safety
    amount, error = await parse_bet(user_id, [args[2]])
    if error: return await message.reply_text(error)

    await update_balance(user_id, -amount)
    outcome = random.choice(["red", "black"])
    
    if outcome == choice:
        payout = amount * 2
        await update_balance(user_id, payout)
        result_text = f"**🎉 You Won {amount} ₹**"
    else:
        result_text = f"**💀 You Lost {amount} ₹**"

    await message.reply_text(
        f"**🎰 Roulette Result**\n\n"
        f"**🎯 Landed: {outcome.upper()}**\n"
        f"{result_text}\n\n"
        f"**🏧 Balance: {await check_balance(user_id)} ₹**"
    )

# -----------------------
# ✂️ GAME 3: ROCK PAPER SCISSORS (Restored)
# -----------------------
@Client.on_message(filters.command(["rps"]))
async def rps_start(client: Client, message: Message):
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🪨", callback_data="rps:rock"),
        InlineKeyboardButton("📄", callback_data="rps:paper"),
        InlineKeyboardButton("✂️", callback_data="rps:scissors")
    ]])
    await message.reply_text(
        "**__Lets Start This Game 😁\n\nChoose Your Ultimate Move__**", 
        reply_markup=kb, 
        quote=True
    )

@Client.on_callback_query(filters.regex("^rps:(rock|paper|scissors)$"))
async def rps_play(client: Client, cq: CallbackQuery):
    user_id = cq.from_user.id
    user_choice = cq.data.split(":")[1]
    
    # Check if user has enough balance to risk playing (since loss is -1000)
    bal = await check_balance(user_id)
    if bal < RPS_LOSE:
        return await cq.answer(f"🚫 You need at least {RPS_LOSE} ₹ to play!", show_alert=True)

    bot_choice = random.choice(["rock", "paper", "scissors"])
    
    # Logic
    if user_choice == bot_choice:
        outcome = "draw"
        reward = 0
        msg_res = "Draw 😐"
    elif (user_choice == "rock" and bot_choice == "scissors") or \
         (user_choice == "paper" and bot_choice == "rock") or \
         (user_choice == "scissors" and bot_choice == "paper"):
        outcome = "win"
        reward = RPS_WIN
        msg_res = "You Win 🎉"
    else:
        outcome = "lose"
        reward = -RPS_LOSE
        msg_res = "You Lose 💀"

    if reward != 0:
        await update_balance(user_id, reward)

    new_bal = await check_balance(user_id)
    
    txt = (
        f"**__Rock-Paper-Scissors__**\n\n"
        f"**__You:__ {RPS_EMOJI[user_choice]} __vs Bot:__ {RPS_EMOJI[bot_choice]}**\n\n"
        f"**__🎲 Result: {msg_res}__**\n"
        f"**__💰 Change: {reward} ₹__**\n"
        f"**__🏧 Your Balance: {new_bal} ₹__**"
    )
    
    # Re-attach buttons so they can play again instantly
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🪨", callback_data="rps:rock"),
        InlineKeyboardButton("📄", callback_data="rps:paper"),
        InlineKeyboardButton("✂️", callback_data="rps:scissors")
    ]])
    
    await cq.message.edit_text(txt, reply_markup=kb)

# -----------------------
# 🎲 NEW GAMES (Slots & Dart)
# -----------------------
@Client.on_message(filters.command(["slots", "luck"]))
async def play_slots(client: Client, message: Message):
    user_id = message.from_user.id
    amount, error = await parse_bet(user_id, message.command[1:])
    if error: return await message.reply_text(error)

    await update_balance(user_id, -amount)
    sent_dice = await client.send_dice(message.chat.id, "🎰")
    val = sent_dice.dice.value
    await asyncio.sleep(3)

    # 64=Jackpot(Triple 7), 1/22/43=Grapes/Bar(Small win)
    if val == 64:
        payout = amount * 5
        res = "JACKPOT! 🎰"
    elif val in [1, 22, 43]:
        payout = int(amount * 1.5)
        res = "Win! 🍒"
    else:
        payout = 0
        res = "Lost 😢"

    if payout > 0: await update_balance(user_id, payout)
    await message.reply_text(f"**{res}**\n💰 Won: {payout}\n🏧 Bal: {await check_balance(user_id)}")

@Client.on_message(filters.command(["math"]))
async def math_game(client: Client, message: Message):
    num1, num2 = random.randint(10, 99), random.randint(10, 99)
    op = random.choice(['+', '-', '*'])
    ans = eval(f"{num1}{op}{num2}")
    
    q_msg = await message.reply_text(f"**🧮 Fast Math:** `{num1} {op} {num2}` ?")
    try:
        resp = await client.wait_for_message(message.chat.id, filters.user(message.from_user.id) & filters.text, timeout=10)
        if str(resp.text).strip() == str(ans):
            bonus = 100
            await update_balance(message.from_user.id, bonus)
            await resp.reply_text(f"**✅ Correct! Earned {bonus} ₹**")
        else:
            await resp.reply_text(f"**❌ Wrong. Answer: {ans}**")
    except:
        await q_msg.edit_text(f"**⏰ Time Up! Ans: {ans}**")

# -----------------------
# 🏆 LEADERBOARD
# -----------------------
@Client.on_message(filters.command(["lb"]))
async def leaderboard(client: Client, message: Message):
    cursor = user_col.find().sort("balance", -1).limit(10)
    text = "🏆 **__Top 10 Richest Users__**\n\n"
    i = 1
    async for user in cursor:
        uid = user["_id"]
        bal = user["balance"]
        try:
            u = await client.get_users(uid)
            name = u.first_name
        except:
            name = f"User {uid}"
        text += f"**__{i}. {name} - {bal:,} ₹__**\n"
        i += 1
    await message.reply_text(text)

@Client.on_message(filters.command(["funhelp"]))
async def fun_help(client: Client, message: Message):
    text = (
        "**🎮 FUN & GAMES MENU**\n\n"
        "**Classic Games:**\n"
        "• `/rps` - Rock Paper Scissors\n"
        "• `/roulette <Red/Black> <bet>`\n"
        "• `/cf <bet>` - Chicken Fight\n\n"
        "**New Games:**\n"
        "• `/slots <bet>` - Slot Machine\n"
        "• `/math` - Math Challenge\n\n"
        "**Economy:**\n"
        "• `/bal` | `/daily` | `/lb`"
    )
    await message.reply_text(text)
    
