# ------------------------------------------------
# File Name: NeonCommands.py
# Author: https://t.me/myselfneon
# Description: Auto Add Commands via /neoncmd (Owner Only)
# ------------------------------------------------

import asyncio
from FileStream.config import Telegram
from pyrogram import Client, filters
from pyrogram.types import BotCommand, Message

# --- Edit This List (Text Format) ---
COMMAND_BLOCK = """
[
start - 𝘔𝘺𝘴𝘦𝘭𝘧𝘕𝘦𝘰𝘯 𝘉𝘰𝘵 𝘚𝘵𝘢𝘳𝘵
help - 𝘚𝘩𝘰𝘸 𝘏𝘦𝘭𝘱 𝘔𝘦𝘯𝘶
index - 𝘐𝘯𝘥𝘦𝘹 𝘍𝘪𝘭𝘦 𝘍𝘳𝘰𝘮 𝘊𝘩𝘢𝘯𝘯𝘦𝘭
setskip - 𝘚𝘬𝘪𝘱 𝘍𝘪𝘭𝘦𝘴 𝘞𝘩𝘦𝘯 𝘐𝘯𝘥𝘦𝘹𝘪𝘯𝘨
logs - 𝘛𝘰 𝘎𝘦𝘵 𝘙𝘦𝘤𝘦𝘯𝘵 𝘌𝘳𝘳𝘰𝘳𝘴
stats - 𝘍𝘪𝘭𝘦𝘴 𝘚𝘵𝘢𝘵𝘴 𝘐𝘯 𝘋𝘉
connections - 𝘚𝘦𝘦 𝘈𝘭𝘭 𝘊𝘰𝘯𝘯𝘦𝘤𝘵𝘦𝘥 𝘎𝘳𝘰𝘶𝘱𝘴
settings - 𝘎𝘳𝘰𝘶𝘱 𝘚𝘦𝘵𝘵𝘪𝘯𝘨𝘴 𝘔𝘦𝘯𝘶
connect - 𝘊𝘰𝘯𝘯𝘦𝘤𝘵 𝘛𝘰 𝘗𝘔
disconnect - 𝘋𝘪𝘴𝘤𝘰𝘯𝘯𝘦𝘤𝘵 𝘍𝘳𝘰𝘮 𝘗𝘔
delete - 𝘋𝘦𝘭𝘦𝘵𝘦 𝘚𝘱𝘦𝘤𝘪𝘧𝘪𝘤 𝘍𝘪𝘭𝘦 𝘍𝘳𝘰𝘮 𝘐𝘯𝘥𝘦𝘹
deleteall - 𝘋𝘦𝘭𝘦𝘵𝘦 𝘈𝘭𝘭 𝘐𝘯𝘥𝘦𝘹𝘦𝘥 𝘍𝘪𝘭𝘦𝘴
info - 𝘎𝘦𝘵 𝘜𝘴𝘦𝘳 𝘐𝘯𝘧𝘰
id - 𝘎𝘦𝘵 𝘛𝘦𝘭𝘦𝘨𝘳𝘢𝘮 𝘐𝘋𝘴
imdb - 𝘎𝘦𝘵 𝘐𝘯𝘧𝘰 𝘍𝘳𝘰𝘮 𝘐𝘔𝘋𝘉
search - 𝘚𝘦𝘢𝘳𝘤𝘩 𝘍𝘳𝘰𝘮 𝘝𝘢𝘳𝘪𝘰𝘶𝘴 𝘚𝘰𝘶𝘳𝘤𝘦𝘴
chats - 𝘓𝘪𝘴𝘵 𝘰𝘧 𝘔𝘺 𝘊𝘩𝘢𝘵𝘴 𝘢𝘯𝘥 𝘐𝘋𝘴
leave - 𝘓𝘦𝘢𝘷𝘦 𝘍𝘳𝘰𝘮 𝘢 𝘊𝘩𝘢𝘵
disable - 𝘋𝘪𝘴𝘢𝘣𝘭𝘦 𝘢 𝘊𝘩𝘢𝘵
enable - 𝘙𝘦-𝘌𝘯𝘢𝘣𝘭𝘦 𝘊𝘩𝘢𝘵
ban - 𝘉𝘢𝘯 𝘢 𝘜𝘴𝘦𝘳
unban - 𝘜𝘯𝘣𝘢𝘯 𝘜𝘴𝘦𝘳
channel - 𝘛𝘰𝘵𝘢𝘭 𝘊𝘰𝘯𝘯𝘦𝘤𝘵𝘦𝘥 𝘊𝘩𝘢𝘯𝘯𝘦𝘭𝘴 𝘓𝘪𝘴𝘵
broadcast - 𝘉𝘳𝘰𝘢𝘥𝘤𝘢𝘴𝘵 𝘢 𝘔𝘴𝘨 𝘛𝘰 𝘈𝘭𝘭 𝘜𝘴𝘦𝘳𝘴
grp_broadcast - 𝘉𝘳𝘰𝘢𝘥𝘤𝘢𝘴𝘵 𝘪𝘯 𝘊𝘰𝘯𝘯𝘦𝘤𝘵𝘦𝘥 𝘎𝘳𝘰𝘶𝘱𝘴
set_template - 𝘚𝘦𝘵 𝘢 𝘊𝘶𝘴𝘵𝘰𝘮 𝘐𝘔𝘋𝘉 𝘛𝘦𝘮𝘱𝘭𝘢𝘵𝘦 𝘍𝘰𝘳 𝘎𝘳𝘰𝘶𝘱𝘴
deletefiles - 𝘛𝘰 𝘋𝘦𝘭𝘦𝘵𝘦 𝘗𝘳𝘦𝘋𝘝𝘋 𝘢𝘯𝘥 𝘊𝘢𝘮𝘙𝘪𝘱 𝘍𝘪𝘭𝘦𝘴 𝘍𝘳𝘰𝘮 𝘉𝘰𝘵'𝘴 𝘋𝘢𝘵𝘢𝘣𝘢𝘴𝘦
plan - 𝘊𝘩𝘦𝘤𝘬 𝘗𝘭𝘢𝘯 𝘋𝘦𝘵𝘢𝘪𝘭𝘴
myplan - 𝘊𝘩𝘦𝘤𝘬 𝘠𝘰𝘶𝘳 𝘗𝘭𝘢𝘯 𝘚𝘵𝘢𝘵𝘴
add_premium - 𝘈𝘥𝘥 𝘜𝘴𝘦𝘳 𝘛𝘰 𝘗𝘳𝘦𝘮𝘪𝘶𝘮
remove_premium - 𝘙𝘦𝘮𝘰𝘷𝘦 𝘜𝘴𝘦𝘳 𝘍𝘳𝘰𝘮 𝘗𝘳𝘦𝘮𝘪𝘶𝘮
shortlink - 𝘚𝘦𝘵 𝘠𝘰𝘶𝘳 𝘜𝘙𝘓 𝘚𝘩𝘰𝘳𝘵𝘯𝘦𝘳
setshortlinkon - 𝘛𝘶𝘳𝘯 𝘚𝘩𝘰𝘳𝘵𝘓𝘪𝘯𝘬 𝘖𝘕
setshortlinkoff - 𝘛𝘶𝘳𝘯 𝘚𝘩𝘰𝘳𝘵𝘓𝘪𝘯𝘬 𝘖𝘍𝘍
shortlink_off - 𝘊𝘩𝘦𝘤𝘬 𝘚𝘩𝘰𝘳𝘵𝘓𝘪𝘯𝘬𝘴 𝘋𝘦𝘵𝘢𝘪𝘭𝘴
set_tutorial - 𝘚𝘦𝘵 𝘜𝘙𝘓 𝘚𝘩𝘰𝘳𝘵𝘯𝘦𝘳 𝘎𝘶𝘪𝘥𝘦
remove_tutorial - 𝘙𝘦𝘮𝘰𝘷𝘦 𝘛𝘶𝘵𝘰𝘳𝘪𝘢𝘭
rename - 𝘙𝘦𝘯𝘢𝘮𝘦 𝘈𝘯𝘺 𝘍𝘪𝘭𝘦 | 𝘝𝘪𝘥𝘦𝘰 | 𝘈𝘶𝘥𝘪𝘰
fsub - 𝘈𝘥𝘥 𝘍𝘰𝘳𝘤𝘦 𝘚𝘶𝘣𝘴𝘤𝘳𝘪𝘣𝘦
nofsub - 𝘋𝘦𝘭𝘦𝘵𝘦 𝘍𝘰𝘳𝘤𝘦 𝘚𝘶𝘣𝘴𝘤𝘳𝘪𝘣𝘦
font - 𝘊𝘳𝘦𝘢𝘵𝘦 𝘔𝘶𝘭𝘵𝘪𝘱𝘭𝘦 𝘍𝘰𝘯𝘵 𝘚𝘵𝘺𝘭𝘦𝘴
repo - 𝘍𝘪𝘯𝘥 𝘈𝘯𝘺 𝘎𝘪𝘵𝘏𝘶𝘣 𝘙𝘦𝘱𝘰
tts - 𝘛𝘦𝘹𝘵 𝘛𝘰 𝘈𝘶𝘥𝘪𝘰 𝘊𝘰𝘯𝘷𝘦𝘳𝘵𝘦𝘳
ping - 𝘊𝘩𝘦𝘤𝘬 𝘗𝘪𝘯𝘨
genpw - 𝘎𝘦𝘯𝘦𝘳𝘢𝘵𝘦 𝘗𝘢𝘴𝘴𝘸𝘰𝘳𝘥
purgerequests - 𝘋𝘦𝘭𝘦𝘵𝘦 𝘈𝘭𝘭 𝘑𝘰𝘪𝘯 𝘙𝘦𝘲𝘶𝘦𝘴𝘵𝘴
totalrequests - 𝘛𝘰𝘵𝘢𝘭 𝘑𝘰𝘪𝘯 𝘙𝘦𝘲𝘶𝘦𝘴𝘵
share - 𝘚𝘩𝘢𝘳𝘦 𝘠𝘰𝘶𝘳 𝘛𝘦𝘹𝘵𝘴
song - 𝘋𝘰𝘸𝘯𝘭𝘰𝘢𝘥 𝘚𝘰𝘯𝘨𝘴 𝘉𝘺 𝘕𝘢𝘮𝘦 𝘖𝘳 𝘓𝘪𝘯𝘬
sticker - 𝘎𝘦𝘵 𝘐𝘋 𝘰𝘧 𝘢 𝘚𝘵𝘪𝘤𝘬𝘦𝘳
json - 𝘎𝘦𝘵 𝘙𝘢𝘸 𝘑𝘚𝘖𝘕 𝘋𝘦𝘵𝘢𝘪𝘭𝘴 𝘰𝘧 𝘢 𝘔𝘦𝘴𝘴𝘢𝘨𝘦
telegraph - 𝘛𝘦𝘭𝘦𝘨𝘳𝘢𝘱𝘩 𝘔𝘰𝘥𝘶𝘭𝘦
plink - 𝘎𝘦𝘯𝘦𝘳𝘢𝘵𝘦 𝘗𝘦𝘳𝘮𝘢𝘯𝘦𝘯𝘵 𝘓𝘪𝘯𝘬 𝘧𝘰𝘳 𝘔𝘦𝘥𝘪𝘢
pbatch - 𝘎𝘦𝘯𝘦𝘳𝘢𝘵𝘦 𝘗𝘦𝘳𝘮𝘢𝘯𝘦𝘯𝘵 𝘉𝘢𝘵𝘤𝘩 𝘓𝘪𝘯𝘬 𝘧𝘰𝘳 𝘔𝘶𝘭𝘵𝘪𝘱𝘭𝘦 𝘍𝘪𝘭𝘦𝘴
batch - 𝘊𝘳𝘦𝘢𝘵𝘦 𝘉𝘢𝘵𝘤𝘩 𝘓𝘪𝘯𝘬𝘴 𝘧𝘰𝘳 𝘔𝘦𝘥𝘪𝘢
dl - 𝘋𝘰𝘸𝘯𝘭𝘰𝘢𝘥 𝘢𝘯𝘺 𝘜𝘙𝘓 𝘓𝘪𝘯𝘬𝘴 𝘢𝘴 𝘔𝘦𝘥𝘪𝘢 𝘰𝘳 𝘋𝘰𝘤𝘶𝘮𝘦𝘯𝘵 𝘍𝘪𝘭𝘦
stream - 𝘎𝘦𝘯𝘦𝘳𝘢𝘵𝘦 𝘢 𝘚𝘵𝘳𝘦𝘢𝘮𝘢𝘣𝘭𝘦 𝘓𝘪𝘯𝘬 𝘧𝘰𝘳 𝘔𝘦𝘥𝘪𝘢
set_caption - 𝘚𝘦𝘵 𝘋𝘦𝘧𝘢𝘶𝘭𝘵 𝘊𝘢𝘱𝘵𝘪𝘰𝘯 𝘧𝘰𝘳 𝘠𝘰𝘶𝘳 𝘜𝘱𝘭𝘰𝘢𝘥𝘴
see_caption - 𝘝𝘪𝘦𝘸 𝘠𝘰𝘶𝘳 𝘚𝘢𝘷𝘦𝘥 𝘊𝘢𝘱𝘵𝘪𝘰𝘯
del_caption - 𝘋𝘦𝘭𝘦𝘵𝘦 𝘠𝘰𝘶𝘳 𝘚𝘢𝘷𝘦𝘥 𝘊𝘢𝘱𝘵𝘪𝘰𝘯
set_thumb - 𝘚𝘦𝘵 𝘛𝘩𝘶𝘮𝘣𝘯𝘢𝘪𝘭 𝘧𝘰𝘳 𝘜𝘱𝘭𝘰𝘢𝘥𝘴
view_thumb - 𝘝𝘪𝘦𝘸 𝘠𝘰𝘶𝘳 𝘚𝘢𝘷𝘦𝘥 𝘛𝘩𝘶𝘮𝘣𝘯𝘢𝘪𝘭
del_thumb - 𝘋𝘦𝘭𝘦𝘵𝘦 𝘠𝘰𝘶𝘳 𝘚𝘢𝘷𝘦𝘥 𝘛𝘩𝘶𝘮𝘣𝘯𝘢𝘪𝘭
filter - 𝘈𝘥𝘥 𝘢 𝘍𝘪𝘭𝘵𝘦𝘳 𝘪𝘯 𝘊𝘩𝘢𝘵
filters - 𝘓𝘪𝘴𝘵 𝘈𝘭𝘭 𝘍𝘪𝘭𝘵𝘦𝘳𝘴 𝘪𝘯 𝘊𝘩𝘢𝘵
del - 𝘋𝘦𝘭𝘦𝘵𝘦 𝘢 𝘚𝘱𝘦𝘤𝘪𝘧𝘪𝘤 𝘍𝘪𝘭𝘵𝘦𝘳
delall - 𝘋𝘦𝘭𝘦𝘵𝘦 𝘈𝘭𝘭 𝘍𝘪𝘭𝘵𝘦𝘳𝘴 𝘪𝘯 𝘊𝘩𝘢𝘵
gfilter - 𝘈𝘥𝘥 𝘢 𝘎𝘭𝘰𝘣𝘢𝘭 𝘍𝘪𝘭𝘵𝘦𝘳
gfilters - 𝘓𝘪𝘴𝘵 𝘈𝘭𝘭 𝘎𝘭𝘰𝘣𝘢𝘭 𝘍𝘪𝘭𝘵𝘦𝘳𝘴
delg - 𝘋𝘦𝘭𝘦𝘵𝘦 𝘢 𝘎𝘭𝘰𝘣𝘢𝘭 𝘍𝘪𝘭𝘵𝘦𝘳
delallg - 𝘋𝘦𝘭𝘦𝘵𝘦 𝘈𝘭𝘭 𝘎𝘭𝘰𝘣𝘢𝘭 𝘍𝘪𝘭𝘵𝘦𝘳𝘴
passhelp - 𝘙𝘦𝘮𝘰𝘷𝘦/𝘈𝘥𝘥 𝘗𝘢𝘴𝘴𝘸𝘰𝘳𝘥 𝘵𝘰 𝘗𝘋𝘍 𝘰𝘳 𝘋𝘰𝘤𝘶𝘮𝘦𝘯𝘵 𝘍𝘪𝘭𝘦𝘴
taskhelp - 𝘛𝘰𝘋𝘰 𝘛𝘢𝘴𝘬𝘴 𝘓𝘪𝘴𝘵
users - 𝘎𝘦𝘵 𝘓𝘪𝘴𝘵 𝘰𝘧 𝘜𝘴𝘦𝘳𝘴 𝘢𝘯𝘥 𝘐𝘋𝘴
whois - 𝘎𝘦𝘵 𝘍𝘶𝘭𝘭 𝘋𝘦𝘵𝘢𝘪𝘭𝘴 𝘰𝘧 𝘈𝘯𝘺 𝘜𝘴𝘦𝘳
request - 𝘚𝘦𝘯𝘥 𝘢 𝘔𝘰𝘷𝘪𝘦/𝘚𝘦𝘳𝘪𝘦𝘴 𝘙𝘦𝘲𝘶𝘦𝘴𝘵 𝘵𝘰 𝘈𝘭𝘭 𝘈𝘥𝘮𝘪𝘯𝘴
restart - 𝘙𝘦𝘴𝘵𝘢𝘳𝘵 𝘉𝘰𝘵 𝘚𝘦𝘳𝘷𝘦𝘳
]
"""

# --- Internal Command Handler ---
@Client.on_message(filters.command("neoncmd") & filters.user(Telegram.OWNER_ID))
async def sync_bot_commands(client: Client, message: Message):

    msg = await message.reply_text("**⏱️ __Wait 3 Seconds while I load your Commands through plugin System.__**")
    
    # Countdown
    for i in range(2, 0, -1):
        await asyncio.sleep(1)
        try:
            await msg.edit_text(f"**⏱️ __Wait {i} Seconds while I load your Commands through plugin System.__**")
        except:
            pass
            
    await asyncio.sleep(1)

    print("Checking Command Sync...")

    try:
        # --- Parse The Text Block ---
        commands = []
        for line in COMMAND_BLOCK.strip().split("\n"):
            # Clean Up Line
            line = line.strip()
            
            if line in ["[", "]"] or not line:
                continue
                
            if "-" in line:
                cmd, desc = line.split("-", 1)
                commands.append(BotCommand(cmd.strip(), desc.strip()))

        # --- Push to Telegram ---
        await client.set_bot_commands(commands)
        
        print(f"✅ Commands Synced with Telegram: {len(commands)} commands set.")
        
        # --- Confirm Success ---
        await msg.edit_text("**✅ __Success !!\n🎉 Commands Updated Successfully.__**\n👀 **__Close Telegram and Return back to see Changes. - by @MyselfNeon 🆘__**")
        
    except Exception as e:
        print(f"✗ Failed to Sync Commands: {e}")
        await msg.edit_text(f"**🚫 __Error Updating Commands:__**\n`{e}`")
      
