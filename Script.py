class script(object):
    START_TXT = """<b><blockquote><i>‣ Hᴇʟʟᴏ {}</blockquote>\n<blockquote>I ᴀᴍ Lᴀᴛᴇsᴛ Aᴅᴠᴀɴᴄᴇᴅ Fɪʟᴛᴇʀ Bᴏᴛ.\nCᴏᴅᴇᴅ & Dᴇᴠᴇʟᴏᴘᴇᴅ ʙʏ <a href='https://t.me/MyselfNeon'>NᴇᴏɴAɴᴜʀᴀɢ</a>.\nI ᴄᴀɴ Fɪʟᴛᴇʀ & Sᴇɴᴅ Mᴏᴠɪᴇs / Aɴɪᴍᴇs Fɪʟᴇs Aᴅᴅᴇᴅ ᴛᴏ ᴍʏ Dᴀᴛᴀʙᴀsᴇ !!</blockquote></i></b>"""

    CLONE_START_TXT = """<b><blockquote><i>‣ Hᴇʟʟᴏ {}</blockquote>\n<blockquote>I am Latest Advanced Filter Bot.\nCoded & Developed by <a href='https://t.me/MyselfNeon'>NeonAnurag</a>.\nYou can create you own Clone Bot and use it in your own channel. It will Filter and Send Movies/Animes files added to its Database !!</blockquote></i></b>"""
    
    HELP_TXT = """<b><i>Hello {} \nHere are all my useful features.</i></b>"""

    ABOUT_TXT = """<b><i><blockquote>‣ 📝 My Details</blockquote>
    
⪼ My Name : <a href=https://t.me/{}>{}</a>
⪼ My Best Friend : <a href='tg://settings'>This Sweetie 🤌❤️</a> 
⪼ Developer : <a href={}>Owner</a> 
⪼ Library : <a href='https://docs.pyrogram.org/'>Pyrogram</a> 
⪼ Language : <a href='https://www.python.org/download/releases/3.0/'>Python 3</a> 
⪼ Data Base : <a href='https://www.mongodb.com/'>Mongo DB</a> 
⪼ Bot Server : <a href='https://heroku.com'>Heroku</a> 
⪼ Build Status : ᴠ2.7.1 [Stable]</i></b>"""

    CLONE_ABOUT_TXT = """<b><i><blockquote>‣ 📝 My Details</blockquote>
    
⪼ My Name : {}
⪼ My Best Friend : <a href='tg://settings'>This Sweetie 🤌❤️</a> 
⪼ Cloned From : <a href=https://t.me/{}>{}</a>
⪼ Library : <a href='https://docs.pyrogram.org/'>Pyrogram</a> 
⪼ Language : <a href='https://www.python.org/download/releases/3.0/'>Python 3</a> 
⪼ Data Base : <a href='https://www.mongodb.com/'>Mongo DB</a> 
⪼ Build Status : ᴠ2.7.1 [Stable]></i></b>"""

    CLONE_TXT = """<blockquote><b><i>‣ 👥 CLONE MODE</blockquote>

- You can create your own clone Bot by /clone Command
- You can Broadcast in your clone Bots
- Already added thousands of Files Index

👨‍💻 Command : /clone</i></b>"""

    SUBSCRIPTION_TXT = """<blockquote><b>‣ Referal Plans ⚡</blockquote>
<blockquote><i>Refer your link to your Friends, Family, Channel and Groups to get free Premium for {}

Referal Link - \nhttps://telegram.me/{}?start=Neon-{}  ✨

If {} unique user start the Bot with your referal link then you will Automatically added in Premium List.\n\nBuy paid plan by - /plan\n\n@NeonFiles</b></i></blockquote>"""

    MANUELFILTER_TXT = """<blockquote><b><i>‣ Filters</blockquote>\nFilter is a feature where users can set Automated replies for a perticular keyword and i will respond whenever a keyword is found in Message.
\n<blockquote>‣ Note</blockquote>
1. Bot should have Admin privilege
2. Only Admins can add filters in a chat
3. Alert buttons have a limit of 64 characters
\n<blockquote>‣ Commands And Usage</blockquote>
• /filter - Add a Filter in a chat
• /filters - List of all filters
• /del - Delete a specific filter
• /delall - Delete all available filters (Admin Only)</b></i>"""

    BUTTON_TXT = """<blockquote><b><i>‣ Buttons</blockquote>
This Bot support both URL and alert inline buttons.
\n<blockquote>‣ Note</blockquote>
1. Telegram will not allows you to send Buttons without any content so content is mandatory.
2. This Bot supports buttons with any telegram media type
3. Buttons should be properly parsed as Markdown format
\n<blockquote>‣ URL Buttons
[Button Text](buttonurl:https://t.me/NeonFiles)
‣ Alert Buttons
[Button Text](buttonalert:This is an Alert Message)</blockquote></b></i>"""

    AUTOFILTER_TXT = """<b><i><blockquote>‣ File Index</blockquote>
1. Make me Admin of your Channel if it's Private
2. Make sure that your channel does not contains crimps, p@rns and fake Files
3. Forward the last message to me with Quotes. I'll add all the files in that channel to my database

<blockquote>‣ Auto Filter</blockquote>
1. Add Bot as Admin on your Group
2. Use /connect and connect your Group to the Bot
3. Use /settings on Bot's PM and turn AutoFilter on the settings menu</b></i>"""

    CONNECTION_TXT = """<b><i><blockquote>Connections</blockquote>
• Connect Bot to PM
• It helps to avoid spamming in Groups
\n<blockquote>Note</blockquote>
1. Only Admins can add connections
2. Send <code>/connect</code> for connecting me to PM
\n<blockquote>Commands and Usage</blockquote>
• /connect  - Connect any chat to PM
• /disconnect  - Disconnect from chat
• /connections - List of all connections</b></i>"""

    EXTRAMOD_TXT = """<blockquote><i><b>‣ Extra Modules</b></i></blockquote>
<blockquote> <b>⪼ Maintained by : <a href={}>Owner</a></b> 
 <b>⪼ Join here : <a href={}>Update Channel</a></b> </blockquote>
  
<b><i>/id - Get ID of specified User 
/info  - Get information about a user
/song - Download any song
/telegraph - Telegraph generator under 5MB video or photo and I will give you telegraph link
/tts - Text to Voice converter
/video - YouTube video downloader
/font - Stylish and cool Font generator</i></b>"""


    ADMIN_TXT = """<b><blockquote>‣ 𝐀𝐃𝐌𝐈𝐍 𝐌𝐎𝐃𝐬 🛐</blockquote>
<i><blockquote>Tʜᴇsᴇ Cᴏᴍᴍᴀɴᴅs ᴀʀᴇ Mᴀᴅᴇ Jᴜsᴛ Fᴏʀ Aᴅᴍɪɴs Aɴᴅ Wɪʟʟ Wᴏʀᴋ Oɴʟʏ Fᴏʀ Aᴅᴍɪɴs 🥰</i></blockquote>
\n<blockquote>‣ 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒 & 𝐔𝐒𝐀𝐆𝐄</blockquote>
<i>• /logs - Tᴏ Gᴇᴛ Rᴇᴄᴇɴᴛ Eʀʀᴏʀs
• /stats - Gᴇᴛ Sᴛᴀᴛᴜs ᴏғ Fɪʟᴇs ɪɴ DB
• /delete - Dᴇʟᴇᴛᴇ ᴀ Fɪʟᴇ Fʀᴏᴍ DB
• /users - Gᴇᴛ Lɪsᴛ ᴏғ Usᴇʀs Aɴᴅ IDs
• /chats - Gᴇᴛ Lɪsᴛ ᴏғ Cʜᴀᴛs Aɴᴅ IDs
• /leave  - Tᴏ Lᴇᴀᴠᴇ Fʀᴏᴍ ᴀ Cʜᴀᴛ
• /disable  - Tᴏ Dɪsᴀʙʟᴇ ᴀ Cʜᴀᴛ
• /ban  - Bᴀɴ ᴀ Usᴇʀ
• /unban  - Uɴʙᴀɴ ᴀ Usᴇʀ
• /channel - Tᴏᴛᴀʟ Cᴏɴɴᴇᴄᴛᴇᴅ Cʜɴʟs
• /broadcast - Bʀᴏᴀᴅᴄᴀsᴛ ᴀ Msɢ Tᴏ Aʟʟ Usᴇʀs ᴏғ Bᴏᴛ
• /grp_broadcast - Bʀᴏᴀᴅᴄᴀsᴛ ᴀ Msɢ Tᴏ Aʟʟ Cᴏɴɴᴇᴄᴛᴇᴅ Gʀᴏᴜᴘs
• /gfilter - Aᴅᴅ ᴀ Gʟᴏʙᴀʟ Fɪʟᴛᴇʀs
• /gfilters - Lɪsᴛ ᴏғ Aʟʟ Gʟᴏʙᴀʟ Fɪʟᴛᴇʀs
• /delg - Dʟᴛ ᴀ Sᴘᴇᴄɪғɪᴄ Gʟᴏʙᴀʟ Fɪʟᴛᴇʀ
• /request - Tᴏ Sᴇɴᴅ ᴀ Mᴏᴠɪᴇ/Sᴇʀɪᴇs Rᴇǫᴜᴇsᴛ Tᴏ Aʟʟ Bᴏᴛ Aᴅᴍɪɴs Oɴʟʏ Wᴏʀᴋ Oɴ Sᴜᴘᴘᴏʀᴛ Gʀᴏᴜᴘ
• /delallg - Tᴏ Dᴇʟᴇᴛᴇ Aʟʟ Gғɪʟᴛᴇʀs Fʀᴏᴍ Tʜᴇ Bᴏᴛ's Dᴀᴛᴀʙᴀsᴇ
• /deletefiles - Tᴏ Dᴇʟᴇᴛᴇ CᴀᴍRɪᴘ Aɴᴅ PʀᴇDVD Fɪʟᴇs Fʀᴏᴍ Bᴏᴛ's Dᴀᴛᴀʙᴀsᴇ</i></b>"""

    SEC_STATUS_TXT = """<b><i>★ Tᴏᴛᴀʟ Usᴇʀs: <code>{}</code>
★ Tᴏᴛᴀʟ Cʜᴀᴛs: <code>{}</code>
★ Tᴏᴛᴀʟ Fɪʟᴇs: <code>{}</code>
★ Usᴇᴅ Sᴛᴏʀᴀɢᴇ: <code>{} MB</code>
★ Fʀᴇᴇ Sᴛᴏʀᴀɢᴇ: <code>{} MB</code></i></b>"""
    
    STATUS_TXT = """<b><i>Total Files From All DBs: <code>{}</code>

USERS DB :-
★ Tᴏᴛᴀʟ Usᴇʀs: <code>{}</code>
★ Tᴏᴛᴀʟ Cʜᴀᴛs: <code>{}</code>

FILE FIRST DB :-
★ Tᴏᴛᴀʟ Fɪʟᴇs: <code>{}</code>
★ Usᴇᴅ Sᴛᴏʀᴀɢᴇ: <code>{} MB</code>
★ Fʀᴇᴇ Sᴛᴏʀᴀɢᴇ: <code>{} MB</code>

FILE SECOND DB :-
★ Tᴏᴛᴀʟ Fɪʟᴇs: <code>{}</code>
★ Usᴇᴅ Sᴛᴏʀᴀɢᴇ: <code>{} MB</code>
★ Fʀᴇᴇ Sᴛᴏʀᴀɢᴇ: <code>{} MB</code>

OTHER DB :-
★ Usᴇᴅ Sᴛᴏʀᴀɢᴇ: <code>{} MB</code>
★ Fʀᴇᴇ Sᴛᴏʀᴀɢᴇ: <code>{} MB</code></i></b>"""
    
    LOG_TEXT_G = """#NewGroup
Gʀᴏᴜᴘ = {}(<code>{}</code>)
Tᴏᴛᴀʟ Mᴇᴍʙᴇʀs = <code>{}</code>
Aᴅᴅᴇᴅ Bʏ - {}"""

    LOG_TEXT_P = """#NewUser
ID - <code>{}</code>
Nᴀᴍᴇ - {}"""

    ALRT_TXT = """<b><i>Hello {}\n\nThis is not your Movie/Series request.\nRequest yours...😏</i></b>"""

    OLD_ALRT_TXT = """<i><b>Hey {}\n\nYou are using one of my old messages.\nPlease send the request again...</i></b>"""

    CUDNT_FND = """<i><b>I couldn't find anything related to {}\nDid you mean any of these?</i></b>"""

    I_CUDNT = """<b><i>Sorry no files were found for your request {} 😕

Check your spelling in Google and try again 😃

<blockquote>Movie request format 👇

Example : Uncharted or Uncharted 2022 or Uncharted En

Series request format 👇

Example : Loki S01 or Loki S01E04 or Lucifer S03E24</blockquote>

🚯 Dont use ➠ ':(!,./)</i></b>"""

    I_CUD_NT = """<b><i>I couldn't find any movie related to {}.\nPlease check the Spelling on Google or IMBD...</b></i>"""

    MVE_NT_FND = """<b><i>Movie not found in Database...</b></i>"""

    TOP_ALRT_MSG = """Checking for Movie in Database..."""

    MELCOW_ENG = """<b><i>Hello {} 😍 \nWelcome to {} Group ❤️</b></i>"""

    SHORTLINK_INFO = """<b><i><blockquote>Select Your Language 🌐</blockquote></b></i>"""

    REQINFO = """<b><i><blockquote>‣ 🍿 Information 🍿</blockquote>\n\nAfter 5 minutes this message will be Automatically deleted

If you do not see the Requested Movie/Series file, look at the next page...</b></i>"""

    SELECT = """<b><i>Select your preferred Language, Quality, Season and Episode</b></i>"""

    SINFO = """<b><i>For Movie Join First Then Click On Try Again Button</b></i>"""

    NORSLTS = """ 
★ #𝗡𝗼𝗥𝗲𝘀𝘂𝗹𝘁𝘀 ★

𝗜𝗗 <b>: {}</b>

𝗡𝗮𝗺𝗲 <b>: {}</b>

𝗠𝗲𝘀𝘀𝗮𝗴𝗲 <b>: {}</b>"""

    CAPTION = """""" 

    IMDB_TEMPLATE_TXT = """
<b><i>Query: {qurey}

<blockquote>‣ IMDb Data</blockquote>

🏷 Title: <a href={url}>{title}</a>
🎭 Genres: {genres}
📆 Year: <a href={url}/releaseinfo>{year}</a>
🌟 Rating: <a href={url}/ratings>{rating}</a> / 10 (based on {votes} user ratings.)
☀️ Languages : <code>{languages}</code>
📀 RunTime: {runtime} Minutes
📆 Release Info : {release_date}
🎛 Countries : <code>{countries}</code>


⏰Result Shown in: {remaining_seconds} <i>seconds</i> 🔥

Requested by : {message.from_user.mention}</b></i>"""
    
    ALL_FILTERS = """
<blockquote><b><i>Hey {} \nHere are my three types of Filters.</i></b></blockquote>"""
    
    GFILTER_TXT = """
<b><i><blockquote>‣ Global Filters 🌐</blockquote>\nGlobal filters are set by Bot Admins which will work on all Groups.
    
<blockquote>‣ Available Commands</blockquote>
• /gfilter - Create a global filter
• /gfilters - View all global filters
• /delg - Delete a global filter
• /delallg - Delete all global filters</b></i>"""
    
    FILE_STORE_TXT = """
<b><i><blockquote>‣ File Store 📚</blockquote>\nFile Store is a feature which will create a Shareable link of a Single or Multiple Files.

<blockquote>‣ Available Commands</blockquote>
• /batch - Link for multiple files
• /link - Link for single file
• /plink - Just like <code>/link </code>but the files will be send with forward restrictions
• /pbatch - Just like <code>/batch </code>but the files will be send with forward restrictions</b></i>"""

    SONG_TXT = """<b><i><blockquote>‣ Song Download Module 🥁</blockquote>
      
<blockquote>For those who love music.\nYou can use this feature to download any song with super fast speed. Works Bot and Groups only...</blockquote>
  
 Commands : /song Song name.</i></b>""" 
  
    YTDL_TXT = """<b><i><blockquote>‣ Youtube Video Downloader 📽️</blockquote>\n\nUsage : You can download any video from Youtube
  
 How to use : Type - /video or /mp4 
 <blockquote>Example :<code>/mp4 https://youtu.be/example...</code></i></b></blockquote>""" 
  
    TTS_TXT = """<b><i>TTS module 🎤 : Translate text to Speech 
  
 Commands and Usage : /tts</b></i>""" 
  
    GTRANS_TXT = """<b>ʜᴇʟᴩ:ɢᴏᴏɢʟᴇ ᴛʀᴀɴꜱʟᴀᴛᴇʀ 
  
 ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ʜᴇʟᴩꜱ yᴏᴜ ᴛᴏ ᴛʀᴀɴꜱʟᴀᴛᴇ ᴀ ᴛᴇxᴛ ᴛᴏ ᴀɴy ʟᴀɴɢᴜᴀɢᴇꜱ yᴏᴜ ᴡᴀɴᴛ. ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ᴡᴏʀᴋꜱ ᴏɴ ʙᴏᴛʜ ᴩᴍ ᴀɴᴅ ɢʀᴏᴜᴏ  
  
 ᴄᴏᴍᴍᴀɴᴅꜱ ᴀɴᴅ ᴜꜱᴀɢᴇ : /tr - ᴛᴏ ᴛʀᴀɴꜱʟᴀᴛᴇʀ ᴛᴇxᴛꜱ ᴛᴏ ᴀ ꜱᴩᴇᴄɪꜰᴄ ʟᴀɴɢᴜᴀɢᴇ 
  
 ɴᴏᴛᴇ: ᴡʜɪʟᴇ ᴜꜱɪɴɢ /tr yᴏᴜ ꜱʜᴏᴜʟᴅ ꜱᴩᴇᴄɪꜰy ᴛʜᴇ ʟᴀɴɢᴜᴀɢᴇ ᴄᴏᴅᴇ 
  
 ᴇxᴀᴍᴩʟᴇ: /𝗍𝗋 ᴍʟ 
 • ᴇɴ = ᴇɴɢʟɪꜱʜ 
 • ᴍʟ = ᴍᴀʟᴀyᴀʟᴀᴍ 
 • ʜɪ = ʜɪɴᴅɪ</b>""" 
  
    TELE_TXT = """<b><i><blockquote>‣ Telegraph Module 🌁</blockquote>\nTwo Upload site options are Available in this Module. Select the one that Best suits your needs -\n\n01 - Envs.sh\nCatbox.moe
  
<blockquote>‣ Usage 📄</blockquote>Use /telegraph and send any image or video under 5MB (for envs.sh) and 200MB (for catbox.moe)⏳
  
<blockquote>‣ Note 👀</blockquote>
• Available in Groups and PM
• Can be used by everyone</i></b>""" 
  
    CORONA_TXT = """<b>ʜᴇʟᴩ: ᴄᴏᴠɪᴅ 
  
 ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ʜᴇʟᴩꜱ yᴏᴜ ᴛᴏ ᴋɴᴏᴡ ᴅᴀɪʟy ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ ᴀʙᴏᴜᴛ ᴄᴏᴠɪᴅ 
  
 ᴄᴏᴍᴍᴀɴᴅꜱ ᴀɴᴅ ᴜꜱᴀɢᴇ: 
  
 /covid - ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ᴡɪᴛʜ yᴏᴜʀ ᴄᴏᴜɴᴛʀy ɴᴀᴍᴇ ᴛᴏ ɢᴇᴛ ᴄᴏᴠɪᴅᴇ ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ 
 ᴇxᴀᴍᴩʟᴇ:<code>/covid 𝖨𝗇𝖽𝗂𝖺</code> 
  
 ⚠️ ᴛʜɪꜱ ꜱᴇʀᴠɪᴄᴇ ʜᴀꜱ ʙᴇᴇɴ ꜱᴛᴏᴩᴩᴇᴅ 
  
 </b>""" 

    PROGRESS_BAR = """\n
╭━━━━❰ File Is Renaming... ❱━➣
┣⪼ 🗂️ : {1} | {2}
┣⪼ ⏳️ : {0}%
┣⪼ 🚀 : {3}/s
┣⪼ ⏱️ : {4}
╰━━━━━━━━━━━━━━━➣ """
  
    ABOOK_TXT = """<b>ʜᴇʟᴩ : ᴀᴜᴅɪᴏʙᴏᴏᴋ 
  
 yᴏᴜ ᴄᴀɴ ᴄᴏɴᴠᴇʀᴛ ᴀ ᴩᴅꜰ ꜰɪʟᴇ ᴛᴏ ᴀ ᴀᴜᴅɪᴏ ꜰɪʟᴇ ᴡɪᴛʜ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ✯ 
  
 ᴄᴏᴍᴍᴀɴᴅꜱ ᴀɴᴅ ᴜꜱᴀɢᴇ: 
 /audiobook: ʀᴇᴩʟy ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ᴛᴏ ᴀɴy ᴩᴅꜰ ᴛᴏ ɢᴇɴᴇʀᴀᴛᴇ ᴛʜᴇ ᴀᴜᴅɪᴏ 
</b>""" 
  
 
    PINGS_TXT = """<b>ᴘɪɴɢ ᴛᴇꜱᴛɪɴɢ:ʜᴇʟᴘꜱ ʏᴏᴜ ᴛᴏ ᴋɴᴏᴡ ʏᴏᴜʀ ᴘɪɴɢ🪄 
  
 ᴄᴏᴍᴍᴀɴᴅꜱ: 
 • /alive - ᴛᴏ ᴄʜᴇᴄᴋ ʏᴏᴜ ᴀʀᴇ ᴀʟɪᴠᴇ. 
 • /help - To get help. 
 • /ping - <b>ᴛᴏ ɢᴇᴛ ʏᴏᴜʀ ᴘɪɴɢ. 
  
 ᴜꜱᴀɢᴇ : 
 • ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅꜱ ᴄᴀɴ ʙᴇ ᴜꜱᴇᴅ ɪɴ ᴘᴍ ᴀɴᴅ ɢʀᴏᴜᴘꜱ 
 • ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅꜱ ᴄᴀɴ ʙᴇ ᴜꜱᴇᴅ ʙᴜʏ ᴇᴠᴇʀʏᴏɴᴇ ɪɴ ᴛʜᴇ ɢʀᴏᴜᴘꜱ ᴀɴᴅ ʙᴏᴛꜱ ᴘᴍ 
 • ꜱʜᴀʀᴇ ᴜꜱ ꜰᴏʀ ᴍᴏʀᴇ ꜰᴇᴀᴛᴜʀᴇꜱ 
  </b>""" 
  
    STICKER_TXT = """<b><i><blockquote>‣ Sticker ID Module</blockquote>\nYou can use this module to find and stickerid. \nTap /stickerid to know how to use me.</i></b>""" 
  
    FONT_TXT= """<b>ᴜꜱᴀɢᴇ 
  
 yᴏᴜ ᴄᴀɴ ᴜꜱᴇ ᴛʜɪꜱ ᴍᴏᴅᴜʟᴇ ᴛᴏ ᴄʜᴀɴɢᴇ ꜰᴏɴᴛ ꜱᴛyʟᴇ   
  
 ᴄᴏᴍᴍᴀɴᴅ : /font yᴏᴜʀ ᴛᴇxᴛ (ᴏᴩᴛɪᴏɴᴀʟ) 
 ᴇɢ:- /font ʜᴇʟʟᴏ 
  
 </b>""" 
  
    PURGE_TXT = """<b>ᴘᴜʀɢᴇ 
      
 ᴅᴇʟᴇᴛᴇ ᴀ ʟᴏᴛ ᴏꜰ ᴍᴇssᴀɢᴇs ꜰʀᴏᴍ ɢʀᴏᴜᴘs!  
      
  ᴀᴅᴍɪɴ  
  
 ◉ /purge :- ᴅᴇʟᴇᴛᴇ ᴀʟʟ ᴍᴇssᴀɢᴇs ꜰʀᴏᴍ ᴛʜᴇ ʀᴇᴘʟɪᴇᴅ ᴛᴏ ᴍᴇssᴀɢᴇ, ᴛᴏ ᴛʜᴇ ᴄᴜʀʀᴇɴᴛ ᴍᴇssᴀɢᴇ</b>""" 
  
    WHOIS_TXT = """<b>ᴡʜᴏɪꜱ ᴍᴏᴅᴜʟᴇ 
  
 ɴᴏᴛᴇ:- ɢɪᴠᴇ ᴀ ᴜꜱᴇʀ ᴅᴇᴛᴀɪʟꜱ 
 /whois :- ɢɪᴠᴇ ᴀ ᴜꜱᴇʀ ꜰᴜʟʟ ᴅᴇᴛᴀɪʟꜱ 📑 
 </b>""" 
  
    JSON_TXT = """<b><i><blockquote>‣ Json 📝</blockquote>\nBot returns json file for all replied messages with /json
  
<blockquote>‣ Features</blockquote>\n• Message editing json\n• PM support\n• Group support 
  
<blockquote>‣ Note</blockquote>\nAnyone can use this command, if spamming happens Bot will automatically Ban you from the Group</i></b>""" 
  
    URLSHORT_TXT = """<b>ʜᴇʟᴩ: ᴜʀʟ ꜱʜᴏʀᴛɴᴇʀ 
  
 <i><b>𝚃𝚑𝚒𝚜ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ʜᴇʟᴩꜱ yᴏᴜ ᴛᴏ ꜱʜᴏʀᴛ ᴛᴏ ᴜʀʟ </i></b> 
  
 ᴄᴏᴍᴍᴀɴᴅꜱ ᴀɴᴅ ᴜꜱᴀɢᴇ: 
  
 /short: <b>ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ᴡɪᴛʜ yᴏᴜʀ ʟɪɴᴋ ᴛᴏ ɢᴇᴛ ꜱʜᴏʀᴛ ʟɪɴᴋꜱ</b> 
 ᴇxᴀᴍᴩʟᴇ:<code>/short https://youtu.be/example...</code> 
</b>""" 
  
    CARB_TXT = """<b>ʜᴇʟᴩ ꜰᴏʀ ᴄᴀʀʙᴏɴ 
  
 ᴄᴀʀʙᴏɴ ɪꜱ ᴀ ꜰᴇᴜᴛᴜʀᴇ ᴛᴏ ᴍᴀᴋᴇ ᴛʜᴇ ɪᴍᴀɢᴇ ᴀꜱ ꜱʜᴏᴡɴ ɪɴ ᴛʜᴇ ᴛᴏᴩ ᴡɪᴛʜ ʏᴏᴜʀ ᴛᴇxᴛꜱ. 
 ꜰᴏʀ ᴜꜱɪɴɢ ᴛʜᴇ ᴍᴏᴅᴜʟᴇ ᴊᴜꜱᴛ ꜱᴇɴᴅ ᴛʜᴇ ᴛᴇxᴛ ᴀɴᴅ ᴏᴇᴩʟᴀʏ ᴛɪ ɪᴛ ᴡɪᴛʜ  /carbon ᴄᴏᴍᴍᴀɴᴅ ᴛʜᴇ ʙᴏᴛ ᴡɪʟʟ ᴩᴇᴩᴀʏ ᴡɪᴛʜ ᴛʜᴇ ᴄᴀʀʙᴏɴ ɪᴍᴀɢᴇ 
</b>""" 
    GEN_PASS = """<b>Hᴇʟᴘ: Pᴀꜱꜱᴡᴏʀᴅ Gᴇɴᴇʀᴀᴛᴏʀ 
  
 Tʜᴇʀᴇ Iꜱ Nᴏᴛʜɪɴɢ Tᴏ Kɴᴏᴡ Mᴏʀᴇ. Sᴇɴᴅ Mᴇ Tʜᴇ Lɪᴍɪᴛ Oғ Yᴏᴜʀ Pᴀꜱꜱᴡᴏʀᴅ. 
 - I Wɪʟʟ Gɪᴠᴇ Tʜᴇ Pᴀꜱꜱᴡᴏʀᴅ Oғ Tʜᴀᴛ Lɪᴍɪᴛ. 
  
 Cᴏᴍᴍᴀɴᴅꜱ ᴀɴᴅ Uꜱᴀɢᴇ: 
 • /genpassword ᴏʀ /genpw 𝟸𝟶 
  
 NOTE: 
 • Oɴʟʏ Dɪɢɪᴛꜱ Aʀᴇ Aʟʟᴏᴡᴇᴅ 
 • Mᴀxɪᴍᴜᴍ Aʟʟᴏᴡᴇᴅ Dɪɢɪᴛꜱ Tɪʟʟ 𝟾𝟺  
 (I Cᴀɴ'ᴛ Gᴇɴᴇʀᴀᴛᴇ Pᴀꜱꜱᴡᴏʀᴅꜱ Aʙᴏᴠᴇ Tʜᴇ Lᴇɴɢᴛʜ 𝟾𝟺) 
 • IMDʙ ꜱʜᴏᴜʟᴅ ʜᴀᴠᴇ ᴀᴅᴍɪɴ ᴘʀɪᴠɪʟʟᴀɢᴇ. 
 • Tʜᴇꜱᴇ ᴄᴏᴍᴍᴀɴᴅꜱ ᴡᴏʀᴋꜱ ᴏɴ ʙᴏᴛʜ ᴘᴍ ᴀɴᴅ ɢʀᴏᴜᴘ. 
 • Tʜᴇꜱᴇ ᴄᴏᴍᴍᴀɴᴅꜱ ᴄᴀɴ ʙᴇ ᴜꜱᴇᴅ ʙʏ ᴀɴʏ ɢʀᴏᴜᴘ ᴍᴇᴍʙᴇʀ.</b>""" 
  
    SHARE_TXT = """<b><i><blockquote>‣ Text Share URL</blockquote>\nGet your text share url. 
  
 - Example :- /share
  
 </i></b>""" 
  
    PIN_TXT = """<b>ᴩɪɴ ᴍᴏᴅᴜʟᴇ 
 ᴩɪɴ ᴀ ᴍᴇꜱꜱᴀɢᴇ... 
  
 ᴀʟʟ ᴛʜᴇ ᴩɪɴ ʀᴇᴩʟᴀᴛᴇᴅ ᴄᴏᴍᴍᴀɴᴅꜱ ᴄᴀɴ ʙᴇ ꜰᴏᴜɴᴅ ʜᴇʀᴇ: 
  
 📌ᴄᴏᴍᴍᴀɴᴅꜱ ᴀɴᴅ ᴜꜱᴀɢᴇ📌 
  
 /pin :- ᴛᴏ ᴩɪɴ ᴛʜᴇ ᴍᴇꜱꜱᴀɢᴇ ᴏɴ ʏᴏᴜʀ ᴄʜᴀᴛꜱ 
 /unpin :- ᴛᴏ ᴜɴᴩɪɴ ᴛʜᴇ ᴄᴜʀʀᴇᴇɴᴛ ᴩɪɴɴᴇᴅ ᴍᴇꜱꜱᴀɢᴇ</b>"""

 
    RESTART_TXT = """
**🛜 __<a href="t.me/ZeroFilterBot">Auto Filter</a> Bot Restarted !!__**

**📅 __Dᴀᴛᴇ : {}__**
**⏰ __Tɪᴍᴇ : {}__**
**🌐 __Tɪᴍᴇᴢᴏɴᴇ : Asia/Kolkata__**
**🛠️ __Bᴜɪʟᴅ Sᴛᴀᴛᴜs : v2.7.1 [ Sᴛᴀʙʟᴇ ]__**"""

    LOGO = """
███╗   ██╗ ███████╗ ██████╗  ███╗   ██╗
████╗  ██║ ██╔════╝ ██╔══██╗ ████╗  ██║
██╔██╗ ██║ █████╗   ██║   ██║ ██╔██╗ ██║
██║╚██╗██║ ██╔══╝   ██║   ██║ ██║╚██╗██║
██║ ╚████║ ███████╗ ╚██████╔ ██║ ╚████║
╚═╝  ╚═══╝ ╚══════╝  ╚═════╝ ╚═╝  ╚═══╝"""
 
    TAMIL_INFO = """
<b><i><blockquote>ஏய் <a href='tg://settings'>Dear User 🤌❤️</a></blockquote> 

<blockquote expandable> இப்போது டெலிகிராமிலும் பணம் சம்பாதிக்கலாம்.

 தந்தி மூலம் பணம் சம்பாதிக்க உங்களிடம் 1 குழு இருக்க வேண்டும்.
 உங்களிடம் குழு இருந்தால், எங்கள் bot ஐ உங்கள் குழுவில் சேர்ப்பதன் மூலம் நீங்கள் பணம் சம்பாதிக்கலாம்.

 உங்கள் குழுவில் அதிக உறுப்பினர்கள் இருந்தால், உங்கள் வருமானம் அதிகரிக்கும்.

 எப்படி மற்றும் என்ன செய்ய வேண்டும்

 படி 1: இந்த FILTER-BOT போட் உங்கள் குழுவை நிர்வாகியாக்குங்கள்

 படி 2: உங்கள் இணையதளம் மற்றும் API ஐச் சேர்க்கவும்

 Exp: /shortlink xtz.in 4b392f8eb6ad711fbe58

 வீடியோவைச் சேர்க்கவும்

 �D எப்படி சேர்ப்பது 👇

 Exp: /set_tutorial video link

மேலும் உங்கள் குழுவில் பயிற்சி வீடியோ தொகுப்பு ஆகிடும்...</b></i></blockquote>"""

    ENGLISH_INFO = """
<b><i><blockquote>‣ Hey <a href='tg://settings'>Dear User 🤌❤️</a></blockquote>

<blockquote expandable>Now you can earn money on Telegram too.\n\nYou must have 1 group to earn money by telegram.If you have a group, you can earn money by adding our bot to your group.

The more members you have in your group, the higher your income will be.</blockquote>

<blockquote>‣ How and what to do ⁉️</blockquote>

Step 1: Add your website and API
Step 2: Make sure this Bot is Admin in your given Group

Exp: /shortlink <code>xtz.in</code> 4b39dfbe58

<blockquote>‣ Add a video 📷</blockquote>

Exp: /set_tutorial video link

Also your given tutorial will be Added inside Your specified Group...</b></i>"""

    TELUGU_INFO = """
<b><i><blockquote>‣ హే <a href='tg://settings'>Dear User 🤌❤️</a></blockquote>

<blockquote expandable> ఇప్పుడు మీరు టెలిగ్రామ్‌లో కూడా డబ్బు సంపాదించవచ్చు.

 టెలిగ్రామ్ ద్వారా డబ్బు సంపాదించడానికి మీరు తప్పనిసరిగా 1 గ్రూప్‌ని కలిగి ఉండాలి.
 మీకు గ్రూప్ ఉన్నట్లయితే, మా బాట్‌ను మీ గ్రూప్‌కి జోడించడం ద్వారా మీరు డబ్బు సంపాదించవచ్చు.

 మీ గ్రూప్‌లో ఎంత ఎక్కువ మంది సభ్యులు ఉంటే మీ ఆదాయం అంత ఎక్కువగా ఉంటుంది.

 ఎలా మరియు ఏమి చేయాలి

 దశ 1: ఈ ZERO-FILTER-BOT బాట్‌ని మీ సమూహానికి నిర్వహించండి

 దశ 2: మీ వెబ్‌సైట్ మరియు APIని జోడించండి

 గడువు: /shortlink xtz.in 4b392f8eb6ad711fbe58

 వీడియోను జోడించండి

 👇 ఎలా జోడించాలి 👇

 గడువు: /set_tutorial వీడియో లింక్

అలాగే మీ బృందం వీడియో సేకరణకు శిక్షణ ఇస్తుంది...</b></i></blockquote>"""

    HINDI_INFO = """
<b><i><blockquote>‣ प्रिय <a href='tg://settings'>प्यारे उपयोगकर्ता</a></blockquote> 

<blockquote expandable> अब आप टेलीग्राम पर भी पैसे कमा सकते हैं।

 टेलीग्राम से पैसे कमाने के लिए आपके पास 1 ग्रुप होना चाहिए।
 यदि आपके पास एक समूह है, तो आप हमारे बॉट को अपने समूह में जोड़कर पैसा कमा सकते हैं।

 आपके समूह में जितने अधिक सदस्य होंगे, आपकी आय उतनी ही अधिक होगी।

 कैसे और क्या करना है

 चरण 1: इस फ़िल्टर-बॉट बॉट को अपने समूह में प्रशासित करें

 चरण 2: अपनी वेबसाइट और एपीआई जोड़ें

 एक्सप: /shortlink xtz.in 4b392f8eb6ad711fbe58

 एक वीडियो जोड़ें

 👇कैसे जोड़ें 👇

 ऍक्स्प: /set_tutorial वीडियो लिंक

साथ ही आपकी टीम वीडियो संग्रह का प्रशिक्षण भी देगी...</blockquote></b></i>"""

    MALAYALAM_INFO = """
<b><i><blockquote>ഹേയ് <a href='tg://settings'>Dear User 🤌❤️</a></blockquote>

<blockquote expandable> ഇപ്പോൾ നിങ്ങൾക്ക് ടെലിഗ്രാമിലും പണം സമ്പാദിക്കാം.

 ടെലിഗ്രാം വഴി പണം സമ്പാദിക്കാൻ നിങ്ങൾക്ക് ഒരു ഗ്രൂപ്പ് ഉണ്ടായിരിക്കണം.
 നിങ്ങൾക്ക് ഒരു ഗ്രൂപ്പ് ഉണ്ടെങ്കിൽ, നിങ്ങളുടെ ഗ്രൂപ്പിലേക്ക് ഞങ്ങളുടെ ബോട്ട് ചേർത്തുകൊണ്ട് നിങ്ങൾക്ക് പണം സമ്പാദിക്കാം.

 നിങ്ങളുടെ ഗ്രൂപ്പിൽ കൂടുതൽ അംഗങ്ങൾ ഉണ്ടെങ്കിൽ, നിങ്ങളുടെ വരുമാനം ഉയർന്നതായിരിക്കും.

 എങ്ങനെ, എന്ത് ചെയ്യണം

 ഘട്ടം 1: ഈ തലപതി-ഫിൽട്ടർ-ബോട്ട് ബോട്ട് നിങ്ങളുടെ ഗ്രൂപ്പിലേക്ക് നൽകുക

 ഘട്ടം 2: നിങ്ങളുടെ വെബ്‌സൈറ്റും API-യും ചേർക്കുക

 കാലഹരണപ്പെടൽ: /shortlink xtz.in 4b392f8eb6ad711fbe58

 ഒരു വീഡിയോ ചേർക്കുക

 👇 എങ്ങനെ ചേർക്കാം 👇

 കാലഹരണപ്പെടൽ: /set_tutorial വീഡിയോ ലിങ്ക്

നിങ്ങളുടെ ടീം വീഡിയോ ശേഖരണവും പരിശീലിപ്പിക്കും...</b></i></blockquote>"""

    URTU_INFO = """
<b><i><blockquote>Hii <a href='tg://settings'>Dear User 🤌❤️</a></blockquote> 

<blockquote expandable> اب آپ ٹیلی گرام پر بھی پیسے کما سکتے ہیں۔

 ٹیلی گرام کے ذریعے پیسے کمانے کے لیے آپ کے پاس 1 گروپ ہونا ضروری ہے۔
 اگر آپ کا کوئی گروپ ہے، تو آپ ہمارے بوٹ کو اپنے گروپ میں شامل کر کے پیسے کما سکتے ہیں۔

 آپ کے گروپ میں جتنے زیادہ ممبر ہوں گے آپ کی آمدنی اتنی ہی زیادہ ہوگی۔

 کیسے اور کیا کرنا ہے۔

 مرحلہ 1: اپنے گروپ میں اس FILTER-BOT بوٹ کا انتظام کریں۔

 مرحلہ 2: اپنی ویب سائٹ اور API شامل کریں۔

 Exp: /shortlink xtz.in 4b392f8eb6ad711fbe58

 ایک ویڈیو شامل کریں۔

 👇 کیسے شامل کریں 👇

 Exp: /set_tutorial ویڈیو لنک

نیز آپ کی ٹیم ویڈیو جمع کرنے کی تربیت دے گی...</b></i></blockquote>"""

    GUJARATI_INFO = """
<b><i><blockquote>અરે <a href='tg://settings'>Dear User 🤌❤️</a></blockquote>

<blockquote expandable> હવે તમે ટેલિગ્રામ પર પણ પૈસા કમાઈ શકો છો.

 ટેલિગ્રામ દ્વારા પૈસા કમાવવા માટે તમારી પાસે 1 જૂથ હોવું આવશ્યક છે.
 જો તમારી પાસે જૂથ છે, તો તમે અમારા બોટને તમારા જૂથમાં ઉમેરીને પૈસા કમાઈ શકો છો.

 તમારા જૂથમાં તમારા જેટલા વધુ સભ્યો હશે તેટલી તમારી આવક વધુ હશે.

 કેવી રીતે અને શું કરવું

 પગલું 1: તમારા જૂથમાં આ FILTER-BOT બોટનું સંચાલન કરો

 પગલું 2: તમારી વેબસાઇટ અને API ઉમેરો

 સમાપ્તિ: /shortlink xtz.in 4b392f8eb6ad711fbe58

 વિડિઓ ઉમેરો

 👇 કેવી રીતે ઉમેરવું 👇

 સમાપ્તિ: /set_tutorial વિડિઓ લિંક

તેમજ તમારી ટીમ વિડિયો કલેક્શનની તાલીમ આપશે...</b></i></blockquote>"""

    KANNADA_INFO = """
<b><i><blockquote> ಹೇ <a href='tg://settings'> Dear User 🤌❤️</a></blockquote>

<blockquote expandable> ಈಗ ನೀವು ಟೆಲಿಗ್ರಾಮ್‌ನಲ್ಲಿಯೂ ಹಣ ಗಳಿಸಬಹುದು.

 ಟೆಲಿಗ್ರಾಮ್ ಮೂಲಕ ಹಣ ಗಳಿಸಲು ನೀವು 1 ಗುಂಪನ್ನು ಹೊಂದಿರಬೇಕು.
 ನೀವು ಗುಂಪನ್ನು ಹೊಂದಿದ್ದರೆ, ನಮ್ಮ ಬೋಟ್ ಅನ್ನು ನಿಮ್ಮ ಗುಂಪಿಗೆ ಸೇರಿಸುವ ಮೂಲಕ ನೀವು ಹಣವನ್ನು ಗಳಿಸಬಹುದು.

 ನಿಮ್ಮ ಗುಂಪಿನಲ್ಲಿ ನೀವು ಹೆಚ್ಚು ಸದಸ್ಯರನ್ನು ಹೊಂದಿದ್ದರೆ, ನಿಮ್ಮ ಆದಾಯವು ಹೆಚ್ಚಾಗುತ್ತದೆ.

 ಹೇಗೆ ಮತ್ತು ಏನು ಮಾಡಬೇಕು

 ಹಂತ 1: ಈ ಫಿಲ್ಟರ್-ಬಾಟ್ ಬೋಟ್ ಅನ್ನು ನಿಮ್ಮ ಗುಂಪಿಗೆ ನಿರ್ವಹಿಸಿ

 ಹಂತ 2: ನಿಮ್ಮ ವೆಬ್‌ಸೈಟ್ ಮತ್ತು API ಸೇರಿಸಿ

 ಅವಧಿ: /shortlink xtz.in 4b392f8eb6ad711fbe58

 ವೀಡಿಯೊ ಸೇರಿಸಿ

 👇 ಸೇರಿಸುವುದು ಹೇಗೆ 👇

 ಅವಧಿ: /set_tutorial ವೀಡಿಯೊ ಲಿಂಕ್

ನಿಮ್ಮ ತಂಡವು ವೀಡಿಯೋ ಸಂಗ್ರಹಣೆಗೆ ತರಬೇತಿ ನೀಡಲಿದೆ...</b></i></blockquote>"""

    BANGLADESH_INFO = """
<b><i><blockquote>আরে <a href='tg://settings'>Dear User 🤌❤️</a></blockquote>

<blockquote expandable> এখন আপনি টেলিগ্রামেও অর্থ উপার্জন করতে পারেন।

 টেলিগ্রামের মাধ্যমে অর্থ উপার্জন করতে আপনার অবশ্যই 1টি গ্রুপ থাকতে হবে।
 আপনার যদি একটি গ্রুপ থাকে, আপনি আপনার গ্রুপে আমাদের বট যোগ করে অর্থ উপার্জন করতে পারেন।

 আপনার গ্রুপে যত বেশি সদস্য থাকবেন আপনার আয় তত বেশি হবে।

 কিভাবে এবং কি করতে হবে

 ধাপ 1: আপনার গ্রুপে এই ZERO-FILTER-BOT বট পরিচালনা করুন

 ধাপ 2: আপনার ওয়েবসাইট এবং API যোগ করুন

 মেয়াদ: /shortlink xtz.in 4b392f8eb6ad711fbe58

 একটি ভিডিও যোগ করুন

 👇 কিভাবে যোগ করবেন 👇

 মেয়াদ: /set_tutorial ভিডিও লিঙ্ক

এছাড়াও আপনার দল ভিডিও সংগ্রহের প্রশিক্ষণ দেবে...</blockquote></i></b>"""

    RENAME_TXT = """<b><i><blockquote>‣ HOW TO RENAME A FILE 📝</blockquote>\n• /rename - send any file and click rename option and type new file name and then select \n[ document, video, audio ]
\n<blockquote>‣ SET THUMBNAIL 🌄</blockquote>\n• /set_thumb - Send any picture to automatically set Thumbnail\n• /del_thumb Use this command and delete your old Thumbnail\n• /view_thumb Use this command view your current Thumbnail

<blockquote>‣ SET CUSTOM CAPTION ✏️</blockquote>\n• /set_caption - Set a custom caption\n• /see_caption - See custom caption\n• /del_caption - Delete custom caption

<blockquote>Example:- <code>/set_caption</code> \n📕 File Name: {filename}
💾 Size: {filesize}
⏰ Duration: {duration}</blockquote></b></i>
"""

    STREAM_TXT = """<b><i><blockquote>‣ Get Stream And Download Link 📥</blockquote>

Get Streamable and Downloadable link of any file by using /stream</b></i>"""



# Dont remove Credits
# Developer Telegram @MyselfNeon
# Update channel - @NeonFiles


