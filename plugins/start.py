import sys
import os
import asyncio
from bson.objectid import ObjectId
from pyrogram import Client, filters, enums 
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from script import Script
from config import Config
from database.stories_db import add_user_db, stories_col, get_random_story_db
from plugins.search import build_aesthetic_caption, delete_messages_later

# PM Standard Start Buttons (Updated with 🎲 Surprise Me Button)
START_BUTTONS = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("📢 Story Channel", url=Config.STORY_CHANNEL),
        InlineKeyboardButton("💬 Support Group", url=Config.SUPPORT_GROUP)
    ],
    [
        InlineKeyboardButton("ℹ️ About", callback_data="about_cb"),
        InlineKeyboardButton("🛠️ Help", callback_data="help_cb")
    ],
    [
        InlineKeyboardButton("🎲 Surprise Me / Random", callback_data="fetch_next_random", style=enums.ButtonStyle.SUCCESS)
    ],
    [
        InlineKeyboardButton("👤 Developer", url=Config.OWNER_LINK)
    ]
])

# Group Start Buttons
GROUP_START_BUTTONS = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("💬 Support Group", url=Config.SUPPORT_GROUP),
        InlineKeyboardButton("👤 Owner", url=Config.OWNER_LINK)
    ],
    [
        InlineKeyboardButton("📢 Story Channel", url=Config.STORY_CHANNEL)
    ]
])

BACK_BUTTON = InlineKeyboardMarkup([
    [InlineKeyboardButton("🔙 Back to Home", callback_data="home_cb")]
])


# Helper function for non-blocking Auto-Delete
async def auto_delete_msg(message: Message, delay: int):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass


# 1. Private Chat /start Handler (With Immediate 'Please Wait' Response)
@Client.on_message(filters.command("start") & filters.private)
async def private_start_cmd(bot: Client, message: Message):
    # ⚡ Instant Wait Response
    wait_msg = await message.reply_text("<b>Pʟᴇᴀsᴇ Wᴀɪᴛ</b>", parse_mode=ParseMode.HTML)
    
    user = message.from_user

    # Returns True ONLY if user is NEW, False if user ALREADY EXISTS in DB
    is_new_user = await add_user_db(
        user_id=user.id,
        first_name=user.first_name,
        username=user.username
    )

    # Edit 'Please Wait' message to Main Start Text
    start_msg = await wait_msg.edit_text(
        text=Script.START_TXT.format(
            mention=user.mention,
            user_id=user.id,
            bot_name=bot.me.first_name
        ),
        reply_markup=START_BUTTONS,
        disable_web_page_preview=True,
        parse_mode=ParseMode.HTML
    )

    # Log Channel me notification SIRF NAYE User par jayegi
    if is_new_user and Config.LOG_CHANNEL:
        try:
            log_text = (
                f"👤 <b>ɴᴇᴡ ᴜꜱᴇʀ ꜱᴛᴀʀᴛᴇᴅ ʙᴏᴛ!</b>\n\n"
                f"✨ <b>ɴᴀᴍᴇ:</b> {user.mention}\n"
                f"🆔 <b>ᴜꜱᴇʀ ɪᴅ:</b> <code>{user.id}</code>\n"
                f"👤 <b>ᴜꜱᴇʀɴᴀᴍᴇ:</b> @{user.username if user.username else 'None'}"
            )
            await bot.send_message(
                chat_id=Config.LOG_CHANNEL, 
                text=log_text, 
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            print(f"⚠️ Log Channel error: {e}")


# 2. Group /start Handler (With Immediate 'Please Wait' Response)
@Client.on_message(filters.command("start") & ~filters.private)
async def group_start_cmd(bot: Client, message: Message):
    # ⚡ Instant Wait Response
    wait_msg = await message.reply_text("⏳ <b>PLEASE WAIT...</b>", parse_mode=ParseMode.HTML)

    user = message.from_user
    chat = message.chat

    group_text = (
        f"👋 <b>ʜᴇʟʟᴏ {user.mention}! ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ {chat.title}!</b>\n\n"
        f"ɪ ᴀᴍ ᴀᴄᴛɪᴠᴇ ʜᴇʀᴇ ᴛᴏ ʜᴇʟᴘ ʏᴏᴜ ꜱᴇᴀʀᴄʜ ᴀɴᴅ ꜰɪɴᴅ ʏᴏᴜʀ ꜰᴀᴠᴏʀɪᴛᴇ ꜱᴛᴏʀɪᴇꜱ. "
        f"ᴊᴜꜱᴛ ᴛʏᴘᴇ ᴀɴʏ ꜱᴛᴏʀʏ ɴᴀᴍᴇ ᴅɪʀᴇᴄᴛʟʏ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ ᴛᴏ ꜱᴇᴀʀᴄʜ!\n\n"
        f"⏱️ <i>ᴛʜɪꜱ ᴍᴇꜱꜱᴀɢᴇ ᴡɪʟʟ ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ ɪɴ 2 ᴍɪɴᴜᴛᴇꜱ.</i>"
    )

    group_msg = await wait_msg.edit_text(
        text=group_text,
        reply_markup=GROUP_START_BUTTONS,
        disable_web_page_preview=True,
        parse_mode=ParseMode.HTML
    )

    # Auto-delete group start message & user command after 2 minutes (120s)
    asyncio.create_task(auto_delete_msg(group_msg, 120))
    asyncio.create_task(auto_delete_msg(message, 120))


# 3. System Restart Command (Render Supported)
@Client.on_message(filters.command("restart") & filters.private)
async def restart_bot_handler(bot: Client, message: Message):
    if message.from_user.id not in Config.ADMIN_IDS:
        return await message.reply_text("⛔ <b>ᴀᴄᴄᴇꜱꜱ ᴅᴇɴɪᴇᴅ! ᴏɴʟʏ ᴀᴅᴍɪɴꜱ ᴄᴀɴ ʀᴇꜱᴛᴀʀᴛ.</b>")

    restart_msg = await message.reply_text(
        "🔄 <b>ʙᴏᴛ ɪꜱ ʀᴇꜱᴛᴀʀᴛɪɴɢ... ᴘʟᴇᴀꜱᴇ ᴡᴀɪᴛ 3-5 ꜱᴇᴄᴏɴᴅꜱ!</b>",
        parse_mode=ParseMode.HTML
    )

    # Save details to edit command response on bootup
    try:
        with open("restart_info.txt", "w") as f:
            f.write(f"{restart_msg.chat.id}\n{restart_msg.id}")
    except Exception:
        pass

    # Stop Client & Exit Process Safely
    try:
        await bot.stop()
    except Exception:
        pass

    # Instant exit signal for Render auto-restart container
    os._exit(0)

# 4. Callbacks for About, Help, Home, and Random
@Client.on_callback_query()
async def cb_handler(bot: Client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id

    if data == "home_cb":
        await query.message.edit_text(
            text=Script.START_TXT.format(
                mention=query.from_user.mention,
                user_id=user_id,
                bot_name=bot.me.first_name
            ),
            reply_markup=START_BUTTONS,
            disable_web_page_preview=True,
            parse_mode=ParseMode.HTML
        )

    elif data == "about_cb":
        await query.message.edit_text(
            text=Script.ABOUT_TXT.format(
                owner_link=Config.OWNER_LINK,
                user_id=user_id,
                bot_name=bot.me.first_name
            ),
            reply_markup=BACK_BUTTON,
            disable_web_page_preview=True,
            parse_mode=ParseMode.HTML
        )

    elif data == "help_cb":
        await query.message.edit_text(
            text=Script.HELP_TXT.format(
                bot_name=bot.me.first_name
            ),
            reply_markup=BACK_BUTTON,
            disable_web_page_preview=True,
            parse_mode=ParseMode.HTML
        )

    elif data == "fetch_next_random":
        story = await get_random_story_db()
        
        if not story:
            return await query.answer("❌ डेटाबेस में कोई स्टोरी उपलब्ध नहीं है!", show_alert=True)

        caption = build_aesthetic_caption(story)

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎧 Listen / Play Story", url=story["link"])],
            [
                InlineKeyboardButton("🎲 Next Random", callback_data="fetch_next_random"),
                InlineKeyboardButton("❌ Close", callback_data="close_all_st")
            ]
        ])

        try:
            await query.message.delete()
        except Exception:
            pass

        reply_msg = None
        try:
            reply_msg = await bot.send_photo(
                chat_id=query.message.chat.id,
                photo=story["photo"],
                caption=caption,
                reply_markup=buttons,
                parse_mode=ParseMode.HTML
            )
        except Exception:
            reply_msg = await bot.send_message(
                chat_id=query.message.chat.id,
                text=caption,
                reply_markup=buttons,
                disable_web_page_preview=True,
                parse_mode=ParseMode.HTML
            )

        if reply_msg and query.message.chat.type.value != "private":
            asyncio.create_task(delete_messages_later([reply_msg], 300))

        await query.answer("🎲 Random Story Loaded!")

    elif data == "close_all_st":
        try:
            await query.message.delete()
        except Exception:
            pass
