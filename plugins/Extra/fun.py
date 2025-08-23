from __future__ import annotations

import random
from typing import Dict

from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

def _reply_target(message: Message) -> int:
    return message.reply_to_message.message_id if message.reply_to_message else message.id

HELP_TEXT = (
    "**Fun & Games Plugin**\n\n"
    "Commands:\n"
    "• `/ae <text>` → full-width aesthetic text\n"
    "• `/dart`, `/dice`, `/luck`, `/goal`, `/bowl`, `/basket` → Telegram mini dice games\n"
    "• `/runs` → random funny line\n"
    "• `/rps` → Rock-Paper-Scissors vs bot (buttons)\n"
    "• `/guessstart [max]` → start number guessing (default 100)\n"
    "• `/guess <n>` → guess the number\n"
    "• `/guessstop` → stop guessing game\n"
    "• `/tod [truth|dare]` → random truth or dare\n"
)

@Client.on_message(filters.command(["funhelp"]))
async def fun_help(_: Client, message: Message):
    await message.reply_text(HELP_TEXT)


# ASTHETIC TEXTS

def aesthetify(string: str):
    PRINTABLE_ASCII = range(0x21, 0x7F)
    for ch in string:
        code = ord(ch)
        if code == 0x20:
            yield chr(0x3000)  # full-width space
        elif code in PRINTABLE_ASCII:
            yield chr(code + 0xFF00 - 0x20)
        else:
            yield ch

@Client.on_message(filters.command(["ae"]))
async def aesthetic(_: Client, message: Message):
    text = " ".join(message.command[1:]).strip()
    if not text:
        await message.reply_text("Usage: `/ae your text`", quote=True)
        return
    pretty = "".join(aesthetify(text))
    await message.reply_text(pretty, quote=True)


# TELEGRAM BUILT-IN DICE MINI GAMES

EMOJI_DART = "🎯"
EMOJI_DICE = "🎲"
EMOJI_SLOT = "🎰"
EMOJI_GOAL = "⚽"
EMOJI_BOWL = "🎳"
EMOJI_BASKET = "🏀"

async def _send_dice(_: Client, message: Message, emoji: str):
    await _.send_dice(
        chat_id=message.chat.id,
        emoji=emoji,
        disable_notification=True,
        reply_to_message_id=_reply_target(message),
    )

@Client.on_message(filters.command(["dart", "throw"]))
async def cmd_dart(c: Client, m: Message):
    await _send_dice(c, m, EMOJI_DART)

@Client.on_message(filters.command(["dice", "roll"]))
async def cmd_dice(c: Client, m: Message):
    await _send_dice(c, m, EMOJI_DICE)

@Client.on_message(filters.command(["luck", "slot", "cownd"]))
async def cmd_slot(c: Client, m: Message):
    await _send_dice(c, m, EMOJI_SLOT)

@Client.on_message(filters.command(["goal", "shoot"]))
async def cmd_goal(c: Client, m: Message):
    await _send_dice(c, m, EMOJI_GOAL)

@Client.on_message(filters.command(["bowl", "bowling"]))
async def cmd_bowl(c: Client, m: Message):
    await _send_dice(c, m, EMOJI_BOWL)

@Client.on_message(filters.command(["basket", "basketball"]))
async def cmd_basket(c: Client, m: Message):
    await _send_dice(c, m, EMOJI_BASKET)


# /runs – FUNNY STRINGS

RUN_STRINGS = (
    "Why have you come to remind the darkness inside me…",
    "We are sea creatures pretending to be land adults.",
    "You wanted a bad call, but you needed good thunder.",
    "Oh bloody grandma virtues!",
    "Sea MUGGie, I’m going to pay the bill.",
    "Walk with me or watch me run 😎",
    "You are not a male chaff!!",
    "I locked it. The good beach was done by the good beach.",
    "Kindi… Kindi…!",
    "Give the stems and then show the ISI mark.",
    "Davayeeese, Kingfisher… chilled…!",
    "You made your father for half of the midnight?",
    "This is the king of our work.",
    "I’m fett’s to feed….",
    "Mumak is every Bearby Kachyo…",
    "Oh it moves it… when we moves it…",
    "The saw of a carpenter is the virtue of a carpenter.",
    "Why not to feel this intelligence in Da Vijaya…!",
    "Where was this time…",
    "Save me only…",
    "I know his father’s name is Bhavaniami…",
    "Da Dasa…",
    "Uppukam’s English Salt Mango Tree…",
    "Children… behave or beware!",
    "Car engine out completely…",
    "Is this the eye or magnet?!",
    "Before the 4th pegging falls, I’ll already be there.",
    "The drunk rains and waste…",
    "To tell me I love yo…",
    "No, the Meenaka of Verbapur is not…",
)

@Client.on_message(filters.command("runs"))
async def runs(_: Client, message: Message):
    await message.reply_text(random.choice(RUN_STRINGS), quote=True)


#rROCK-PAPER-SCISSORS /rps

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
    user_choice = cq.data.split(":")[1]
    bot_choice = random.choice(["rock", "paper", "scissors"])
    outcome = _rps_result(user_choice, bot_choice)

    txt = (
        f"**Rock-Paper-Scissors**\n"
        f"You: {RPS_EMOJI[user_choice]}  vs  Bot: {RPS_EMOJI[bot_choice]}\n\n"
        f"Result: **{'You Win 🎉' if outcome=='win' else 'Draw 😐' if outcome=='draw' else 'You Lose 💀'}**"
    )
    await cq.message.edit_text(txt, reply_markup=rps_keyboard())
    await cq.answer()


# NUMBER GUESSING– /guessstart, /guess, /guessstop

class GuessState:
    __slots__ = ("target", "attempts", "max")
    def __init__(self, target: int, max_value: int):
        self.target = target
        self.attempts = 0
        self.max = max_value

GUESS_STATE: Dict[int, GuessState] = {}

@Client.on_message(filters.command(["guessstart"]))
async def guess_start(_: Client, message: Message):
    max_value = 100
    if len(message.command) > 1:
        try:
            max_value = max(10, min(10_000, int(message.command[1])))
        except ValueError:
            pass

    target = random.randint(1, max_value)
    GUESS_STATE[message.chat.id] = GuessState(target, max_value)
    await message.reply_text(
        f"🎯 Guessing game started! Number is **1..{max_value}**.\n"
        f"Use `/guess <number>` to guess. Use `/guessstop` to end.",
        quote=True,
    )

@Client.on_message(filters.command(["guess"]))
async def guess_try(_: Client, message: Message):
    state = GUESS_STATE.get(message.chat.id)
    if not state:
        await message.reply_text("No game running. Start with `/guessstart`.", quote=True)
        return

    if len(message.command) < 2:
        await message.reply_text("Usage: `/guess <number>`", quote=True)
        return

    try:
        n = int(message.command[1])
    except ValueError:
        await message.reply_text("Please provide a valid integer.", quote=True)
        return

    state.attempts += 1
    if n == state.target:
        await message.reply_text(
            f"🎉 Correct! The number was **{state.target}**. Attempts: **{state.attempts}**",
            quote=True,
        )
        GUESS_STATE.pop(message.chat.id, None)
    elif n < state.target:
        await message.reply_text("🔼 Too low. Try higher!", quote=True)
    else:
        await message.reply_text("🔽 Too high. Try lower!", quote=True)

@Client.on_message(filters.command(["guessstop"]))
async def guess_stop(_: Client, message: Message):
    state = GUESS_STATE.pop(message.chat.id, None)
    if state:
        await message.reply_text(f"Game stopped. Number was **{state.target}**.", quote=True)
    else:
        await message.reply_text("There was no active guessing game.", quote=True)


#tTRUTH OR DARE –/tod [truth|dare]

TRUTHS = [
    "What’s a secret hobby you’ve never told anyone about?",
    "What’s the most cringey DM you’ve ever sent?",
    "Which app do you spend way too much time on?",
    "Have you ever pretended to be busy to avoid a call?",
    "What’s a hill you’re willing to die on?",
]

DARES = [
    "Send your most used emoji in this chat—no context.",
    "Type the alphabet backward as fast as you can.",
    "Change your profile name to something funny for 5 minutes.",
    "Reply to the last message with only GIFs for the next 2 minutes.",
    "Say ‘I, for one, welcome our robot overlords.’",
]

@Client.on_message(filters.command(["tod"]))
async def truth_or_dare(_: Client, message: Message):
    choice = (message.command[1].lower() if len(message.command) > 1 else "").strip()
    if choice.startswith("t"):
        await message.reply_text(f"**Truth:** {random.choice(TRUTHS)}", quote=True)
    elif choice.startswith("d"):
        await message.reply_text(f"**Dare:** {random.choice(DARES)}", quote=True)
    else:
        await message.reply_text(
            f"Type `/tod truth` or `/tod dare`.\n"
            f"Or let fate decide: {random.choice(['Truth!', 'Dare!'])}",
            quote=True,
        )