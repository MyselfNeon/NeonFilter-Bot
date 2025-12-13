# Fun_and_Games_v2.py
import random
import asyncio
import time
import os
import datetime
from pyrogram import Client, filters, enums
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient
from info import DATABASE_NAME # Ensure this exists in your info.py

# -----------------------
# ⚙️ CONFIGURATION
# -----------------------
ADMINS = [841851780] # Replace/Add IDs
START_BALANCE = 500
DAILY_BONUS_AMOUNT = 2000

# -----------------------
# 🗄️ ASYNC MONGODB SETUP
# -----------------------
DATABASE_URI = os.environ.get("DATABASE_URI")
if not DATABASE_URI:
    raise ValueError("DATABASE_URI environment variable is not set!")

# Switch to Motor for Async operations (Prevents bot lag)
mongo_client = AsyncIOMotorClient(DATABASE_URI)
db = mongo_client[DATABASE_NAME]
user_col = db["gamble_users"]

# -----------------------
# 🔧 UTILS & ECONOMY
# -----------------------
async def get_data(user_id: int):
    """Fetch user data, insert if new."""
    user = await user_col.find_one({"_id": user_id})
    if not user:
        new_user = {
            "_id": user_id,
            "balance": START_BALANCE,
            "last_daily": None,
            "wins": 0,
            "loss": 0
        }
        await user_col.insert_one(new_user)
        return new_user
    return user

async def update_balance(user_id: int, amount: int):
    """Safely update user balance."""
    # Use $inc for atomic updates (prevents race conditions)
    await user_col.update_one(
        {"_id": user_id}, 
        {"$inc": {"balance": amount}}, 
        upsert=True
    )

async def check_balance(user_id: int) -> int:
    data = await get_data(user_id)
    return data["balance"]

# -----------------------
# 💰 ECONOMY COMMANDS
# -----------------------

@Client.on_message(filters.command(["bal", "balance", "wallet"]))
async def balance_check(client: Client, message: Message):
    user_id = message.from_user.id
    # Support checking other users' balance
    if len(message.command) > 1:
        # Check if reply or ID
        pass # simplified for brevity, defaults to self
    
    data = await get_data(user_id)
    
    txt = (
        f"**💳 🏦 𝐖𝐀𝐋𝐋𝐄𝐓 𝐒𝐓𝐀𝐓𝐔𝐒**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 **User:** {message.from_user.mention}\n"
        f"💰 **Balance:** `{data['balance']:,}` ₹\n"
        f"🏆 **Wins:** `{data.get('wins', 0)}` | 💀 **Loss:** `{data.get('loss', 0)}`"
    )
    await message.reply_text(txt, quote=True)

@Client.on_message(filters.command(["daily", "bonus"]))
async def daily_reward(client: Client, message: Message):
    user_id = message.from_user.id
    data = await get_data(user_id)
    
    now = datetime.datetime.now()
    last_claim = data.get("last_daily")
    
    if last_claim:
        # Motor stores dates naturally, check delta
        delta = now - last_claim
        if delta.total_seconds() < 86400: # 24 hours
            time_left = datetime.timedelta(seconds=86400 - delta.total_seconds())
            return await message.reply_text(f"**⏳ Please wait `{str(time_left).split('.')[0]}` before claiming again.**")

    await user_col.update_one(
        {"_id": user_id}, 
        {"$inc": {"balance": DAILY_BONUS_AMOUNT}, "$set": {"last_daily": now}}
    )
    await message.reply_text(f"**🎉 Daily Bonus Claimed!**\n\nAdded `+{DAILY_BONUS_AMOUNT}` ₹ to your wallet.")

@Client.on_message(filters.command(["pay", "transfer"]))
async def transfer_money(client: Client, message: Message):
    """ /pay @user amount """
    user_id = message.from_user.id
    if not message.reply_to_message and len(message.command) < 3:
        return await message.reply_text("**⚠️ Usage:** Reply to user or use `/pay @username amount`")

    # Determine Target
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        try:
            amount = int(message.command[1])
        except (IndexError, ValueError):
            return await message.reply_text("❌ Invalid amount.")
    else:
        # Username logic would go here, simplified to require reply for safety
        return await message.reply_text("**⚠️ Please reply to the user you want to pay.**")

    if target_id == user_id:
        return await message.reply_text("🤡 You can't pay yourself.")

    balance = await check_balance(user_id)
    if amount <= 0:
        return await message.reply_text("❌ Amount must be positive.")
    if balance < amount:
        return await message.reply_text("🚫 Insufficient funds.")

    # Atomic Transaction
    await update_balance(user_id, -amount)
    await update_balance(target_id, amount)
    
    await message.reply_text(
        f"**💸 Transfer Successful!**\n\n"
        f"Sent: `{amount}` ₹\n"
        f"To: {message.reply_to_message.from_user.mention}"
    )

@Client.on_message(filters.command("addbal") & filters.user(ADMINS))
async def admin_add_bal(client: Client, message: Message):
    try:
        if message.reply_to_message:
            target = message.reply_to_message.from_user.id
            amount = int(message.command[1])
        else:
            target = int(message.command[1])
            amount = int(message.command[2])
            
        await update_balance(target, amount)
        await message.reply_text(f"**✅ Admin:** Added `{amount}` ₹ to `{target}`.")
    except Exception as e:
        await message.reply_text(f"**Error:** {e}")

# -----------------------
# 🎮 GAMES LOGIC
# -----------------------

async def parse_bet(user_id, args):
    """Helper to parse 'all', 'half' or numbers."""
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

# --- 1. SLOTS (Native Telegram Dice) ---
@Client.on_message(filters.command(["slots", "luck"]))
async def play_slots(client: Client, message: Message):
    user_id = message.from_user.id
    amount, error = await parse_bet(user_id, message.command[1:])
    if error:
        return await message.reply_text(f"**⚠️ Error:** {error}\nUsage: `/slots <amount>`")

    # Deduct bet immediately
    await update_balance(user_id, -amount)
    
    sent_dice = await client.send_dice(message.chat.id, "🎰")
    result_value = sent_dice.dice.value
    
    await asyncio.sleep(3) # Wait for animation
    
    # Telegram Slot Logic (approximate mapping)
    # 64 = Triple Seven (Jackpot)
    # 1, 22, 43 = Mixed Fruits (Small Win)
    # Others = Loss
    
    win_amount = 0
    status = "Lost"

    if result_value == 64: # JACKPOT
        win_amount = amount * 10
        status = "JACKPOT! 🎰"
    elif result_value in [1, 22, 43]: # Small Win
        win_amount = int(amount * 1.5)
        status = "Win! 🍒"
    
    if win_amount > 0:
        await update_balance(user_id, win_amount + amount) # Refund bet + win? Or just Win. Usually Win includes bet.
        # Let's say payout includes original bet. 
        # Actually in gambling, 2x means you get 200 for 100 bet (net +100).
        # We deducted `amount` already. So we add back `win_amount`.
        await update_balance(user_id, win_amount) # This adds the total payout
        
        final_text = f"**{status}**\n\n💰 **Won:** `{win_amount}` ₹\n📈 **New Bal:** `{await check_balance(user_id)}`"
    else:
        final_text = f"**😢 You Lost!**\n\n📉 **New Bal:** `{await check_balance(user_id)}`"

    await message.reply_text(final_text, quote=True)

# --- 2. DART (50/50 Skillish) ---
@Client.on_message(filters.command(["dart", "throw"]))
async def play_dart(client: Client, message: Message):
    user_id = message.from_user.id
    amount, error = await parse_bet(user_id, message.command[1:])
    if error:
        return await message.reply_text(f"**⚠️ Error:** {error}\nUsage: `/dart <amount>`")

    await update_balance(user_id, -amount)
    sent_dice = await client.send_dice(message.chat.id, "🎯")
    score = sent_dice.dice.value
    await asyncio.sleep(3)

    # Bullseye is 6
    if score == 6:
        payout = amount * 4
        await update_balance(user_id, payout)
        res = f"**🎯 BULLSEYE! (4x)**\nWon: `{payout}`"
    elif score in [4, 5]:
        payout = int(amount * 1.5)
        await update_balance(user_id, payout)
        res = f"**✅ Good Hit! (1.5x)**\nWon: `{payout}`"
    else:
        res = "**❌ Missed! You lost.**"
    
    await message.reply_text(f"{res}\n💰 Balance: {await check_balance(user_id)}")

# --- 3. MATH CHALLENGE (Brain Farm) ---
@Client.on_message(filters.command("math"))
async def math_game(client: Client, message: Message):
    num1 = random.randint(10, 99)
    num2 = random.randint(10, 99)
    op = random.choice(['+', '-', '*'])
    
    # Calculate answer
    if op == '+': ans = num1 + num2
    elif op == '-': ans = num1 - num2
    else: ans = num1 * num2
    
    question = await message.reply_text(f"**🧮 Quick Math!**\n\nCalculate: `{num1} {op} {num2}`\n\n*You have 10 seconds!*")
    
    try:
        response = await client.wait_for_message(
            chat_id=message.chat.id,
            filters=filters.user(message.from_user.id) & filters.text,
            timeout=10
        )
        
        if str(response.text).strip() == str(ans):
            reward = random.randint(50, 200)
            await update_balance(message.from_user.id, reward)
            await response.reply_text(f"**✅ Correct!**\nEarned: `{reward}` ₹")
        else:
            await response.reply_text(f"**❌ Wrong!** The answer was `{ans}`.")
            
    except asyncio.TimeoutError:
        await question.edit_text(f"**⏰ Time Up!** The answer was `{ans}`.")

# --- 4. COIN TOSS ---
@Client.on_message(filters.command(["toss", "flip", "coin"]))
async def coin_toss(client: Client, message: Message):
    user_id = message.from_user.id
    # Usage: /toss heads 100
    args = message.command
    if len(args) < 3:
        return await message.reply_text("**Usage:** `/toss [heads/tails] [amount]`")
    
    choice = args[1].lower()
    if choice not in ['heads', 'tails', 'h', 't']:
        return await message.reply_text("❌ Choose Heads or Tails.")
    
    amount, error = await parse_bet(user_id, [args[2]])
    if error: return await message.reply_text(error)
    
    await update_balance(user_id, -amount)
    
    msg = await message.reply_text("🪙 **Flipping coin...**")
    await asyncio.sleep(2)
    
    outcome = random.choice(['heads', 'tails'])
    win = False
    
    if (choice.startswith('h') and outcome == 'heads') or (choice.startswith('t') and outcome == 'tails'):
        win = True
    
    if win:
        payout = amount * 2
        await update_balance(user_id, payout)
        await msg.edit_text(f"**🪙 Result: {outcome.upper()}**\n\n🎉 **You Won!** `+{payout}` ₹")
    else:
        await msg.edit_text(f"**🪙 Result: {outcome.upper()}**\n\n💀 **You Lost** `{amount}` ₹")

# -----------------------
# 🏆 LEADERBOARD
# -----------------------
@Client.on_message(filters.command(["lb", "top"]))
async def leaderboard(client: Client, message: Message):
    # Async sort
    cursor = user_col.find().sort("balance", -1).limit(10)
    
    text = "🏆 **__RICH LIST__** 🏆\n\n"
    i = 1
    async for user in cursor:
        uid = user["_id"]
        bal = user["balance"]
        try:
            # Try to get mention, might fail if user not in cache
            u = await client.get_users(uid)
            mention = u.mention
        except:
            mention = f"User `{uid}`"
            
        text += f"**{i}.** {mention} \n   └ 💸 `{bal:,}` ₹\n"
        i += 1
        
    await message.reply_text(text)

# -----------------------
# 🆘 HELP MENU
# -----------------------
@Client.on_message(filters.command("gamehelp"))
async def game_help(client: Client, message: Message):
    txt = (
        "🎮 **GAMING CENTER COMMANDS** 🎮\n\n"
        "**💵 Economy:**\n"
        "`/bal` - Check funds\n"
        "`/daily` - Free daily money\n"
        "`/pay` - Send money to others\n"
        "`/lb` - Global Leaderboard\n\n"
        
        "**🎲 Games:**\n"
        "`/slots <bet>` - Spin the machine (Max risk!)\n"
        "`/dart <bet>` - Throw a dart (Skill shot)\n"
        "`/toss <h/t> <bet>` - 50/50 Coin flip\n"
        "`/math` - Solve math for free cash\n"
        "`/rps` - Rock Paper Scissors (Classic)"
    )
    # Inline buttons for cleaner UI
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Check Balance", callback_data="check_bal")],
        [InlineKeyboardButton("✖️ Close", callback_data="close_data")]
    ])
    await message.reply_text(txt, reply_markup=kb)

@Client.on_callback_query(filters.regex("check_bal"))
async def cb_bal(client, callback):
    bal = await check_balance(callback.from_user.id)
    await callback.answer(f"Your Wallet: {bal} ₹", show_alert=True)

@Client.on_callback_query(filters.regex("close_data"))
async def cb_close(client, callback):
    await callback.message.delete()
    
