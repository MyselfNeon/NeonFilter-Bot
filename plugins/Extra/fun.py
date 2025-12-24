# ---------------------------------------------------
# File Name: Fun.2.py
# Author: MyselfNeon
# Original Repo: https://github.com/MyselfNeon/NeonFilter-Bot
# GitHub: https://github.com/MyselfNeon/
# Telegram: https://t.me/MyelfNeon
# ---------------------------------------------------

import random
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# --- ✂️ ROCK PAPER SCISSORS ---
RPS_EMOJI = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}

@Client.on_message(filters.command(["rps"]))
async def rps_start(client: Client, message: Message):
    # Send the buttons for the user to choose
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🪨 Rock", callback_data="play_rps|rock"),
            InlineKeyboardButton("📄 Paper", callback_data="play_rps|paper"),
            InlineKeyboardButton("✂️ Scissors", callback_data="play_rps|scissors")
        ]
    ])
    await message.reply_text(
        "**👾 Rock-Paper-Scissors!**\n\n__Choose your move:__",
        reply_markup=buttons,
        quote=True
    )

@Client.on_callback_query(filters.regex(r"^play_rps\|"))
async def rps_callback(client: Client, query: CallbackQuery):
    user_move = query.data.split("|")[1]
    bot_move = random.choice(["rock", "paper", "scissors"])
    
    # Determine Winner
    if user_move == bot_move:
        result = "It's a Draw! 😐"
    elif (user_move == "rock" and bot_move == "scissors") or \
         (user_move == "paper" and bot_move == "rock") or \
         (user_move == "scissors" and bot_move == "paper"):
        result = "You Won! 🎉"
    else:
        result = "You Lost! 💀"

    text = (
        f"**👾 RPS Result**\n\n"
        f"**You:** {RPS_EMOJI[user_move]}\n"
        f"**Bot:** {RPS_EMOJI[bot_move]}\n\n"
        f"**{result}**"
    )
    
    # Allow playing again
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🪨", callback_data="play_rps|rock"),
            InlineKeyboardButton("📄", callback_data="play_rps|paper"),
            InlineKeyboardButton("✂️", callback_data="play_rps|scissors")
        ]
    ])
    await query.message.edit_text(text, reply_markup=buttons)

# --- 🎰 SLOTS (Visual) ---
@Client.on_message(filters.command(["slots", "luck"]))
async def slots_game(client: Client, message: Message):
    msg = await client.send_dice(message.chat.id, "🎰")
    score = msg.dice.value
    
    # Wait for animation
    await asyncio.sleep(3)
    
    # 64 = Triple Seven (Jackpot)
    # 1, 22, 43 = Mixed Fruits (Small Win)
    if score == 64:
        text = "**🎰 JACKPOT! TRIPLE 7s! 🎉**"
    elif score in [1, 22, 43]:
        text = "**🍒 Nice spin! You won!**"
    else:
        text = "**😢 Better luck next time!**"
        
    await message.reply_text(text, quote=True)
    
# --- 🔴 ROULETTE (Simple) ---
@Client.on_message(filters.command(["roulette"]))
async def roulette_game(client: Client, message: Message):
    args = message.text.split()
    if len(args) < 2:
        return await message.reply_text("**Usage:** `/roulette <red/black>`")
    
    user_choice = args[1].lower()
    if user_choice not in ["red", "black"]:
        return await message.reply_text("❌ Choose **Red** or **Black**.")
        
    outcome = random.choice(["red", "black", "red", "black", "green"]) # Small chance of green (0)
    
    msg = await message.reply_text("🎲 **Spinning the wheel...**")
    await asyncio.sleep(2)
    
    if outcome == "green":
        res = "💚 **0 (Green)! House wins everything!**"
    elif outcome == user_choice:
        res = f"🎉 **It was {outcome.upper()}! You Win!**"
    else:
        res = f"💀 **It was {outcome.upper()}. You Lose.**"
        
    await msg.edit_text(res)

# --- 🧮 MATH CHALLENGE ---
@Client.on_message(filters.command(["math"]))
async def math_game(client: Client, message: Message):
    num1 = random.randint(5, 50)
    num2 = random.randint(5, 50)
    op = random.choice(["+", "-", "*"])
    
    answer = eval(f"{num1} {op} {num2}")
    
    question_msg = await message.reply_text(
        f"**🧠 Quick Math!**\n\nSolve: `{num1} {op} {num2}`\n\n__Reply with the answer in 10s!__"
    )
    
    try:
        response = await client.wait_for_message(
            chat_id=message.chat.id,
            filters=filters.user(message.from_user.id) & filters.text,
            timeout=10
        )
        
        if str(response.text).strip() == str(answer):
            await response.reply_text("✅ **Correct! You are smart.**")
        else:
            await response.reply_text(f"❌ **Wrong! The answer was {answer}.**")
            
    except asyncio.TimeoutError:
        await question_msg.edit_text(f"⏰ **Time up! The answer was {answer}.**")

# --- 🔢 GUESS THE NUMBER ---
@Client.on_message(filters.command(["guess"]))
async def guess_game(client: Client, message: Message):
    secret = random.randint(1, 10)
    
    await message.reply_text(
        "**🔮 I am thinking of a number between 1 and 10...**\n"
        "__Reply with your guess! (10s timeout)__"
    )
    
    try:
        response = await client.wait_for_message(
            chat_id=message.chat.id,
            filters=filters.user(message.from_user.id) & filters.text,
            timeout=10
        )
        
        try:
            guess = int(response.text)
        except ValueError:
            return await response.reply_text("❌ That's not a number!")

        if guess == secret:
            await response.reply_text(f"🎉 **OMG! You got it! The number was {secret}.**")
        else:
            await response.reply_text(f"❌ **Nope! I was thinking of {secret}.**")
            
    except asyncio.TimeoutError:
        await message.reply_text(f"🤷‍♂️ **Too slow! The number was {secret}.**")

# --- 🆘 HELP MENU ---
@Client.on_message(filters.command("games"))
async def game_help(client: Client, message: Message):
    txt = (
        "**🎮 GAME COMMANDS**\n\n"
        "• `/rps` - Rock Paper Scissors\n"
        "• `/slots` - Spin the Slot Machine\n"
        "• `/roulette <red/black>` - Simple Roulette\n"
        "• `/math` - Quick Math Quiz\n"
        "• `/guess` - Guess the Number (1-10)"
    )
    await message.reply_text(txt)
    
# MyselfNeon
# Don't Remove Credit 🥺
# Telegram Channel @NeonFiles
