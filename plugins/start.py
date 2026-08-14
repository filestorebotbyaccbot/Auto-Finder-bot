import asyncio
from bson.objectid import ObjectId
from pyrogram import Client, filters, enums 
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from script import Script
from config import Config
from database.stories_db import add_user_db, stories_col

# PM Standard Start Buttons
START_BUTTONS = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("📢 Story Channel", url=Config.STORY_CHANNEL),
        InlineKeyboardButton("💬 Support Group", url=Config.SUPPORT_GROUP)
    ],
    [
        InlineKeyboardButton("ℹ️ About", callback_data="about_cb"),
        InlineKeyboardButton("🛠️ Help", callback_data="help_cb", enums.ButtonStyle.SUCCESS))
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


# 1. Private Chat /start Handler
@Client.on_message(filters.command("start") & filters.private)
async def private_start_cmd(bot: Client, message: Message):
    user = message.from_user

    # Save User for Broadcasting
    await add_user_db(
        user_id=user.id,
        first_name=user.first_name,
        username=user.username
    )

    start_msg = await message.reply_text(
        text=Script.START_TXT.format(
            mention=user.mention,
            user_id=user.id
        ),
        reply_markup=START_BUTTONS,
        disable_web_page_preview=True
    )

    if Config.LOG_CHANNEL:
        try:
            log_text = (
                f"👤 **New User Started Bot!**\n\n"
                f"✨ **Name:** {user.mention}\n"
                f"🆔 **User ID:** `{user.id}`\n"
                f"👤 **Username:** @{user.username if user.username else 'None'}"
            )
            await bot.send_message(chat_id=Config.LOG_CHANNEL, text=log_text)
        except Exception as e:
            print(f"⚠️ Log Channel error: {e}")


# 2. Group /start Handler (Separate Handler)
@Client.on_message(filters.command("start") & ~filters.private)
async def group_start_cmd(bot: Client, message: Message):
    user = message.from_user
    chat = message.chat

    group_text = (
        f"👋 **Hello {user.mention}! Welcome to {chat.title}!**\n\n"
        f"I am active here to help you search and find your favorite stories. "
        f"Just type any story name directly in this group to search!\n\n"
        f"⏱️ _This message will auto-delete in 2 minutes._"
    )

    group_msg = await message.reply_text(
        text=group_text,
        reply_markup=GROUP_START_BUTTONS,
        disable_web_page_preview=True
    )

    # Auto-delete group start message & user command after 2 minutes (120s)
    asyncio.create_task(auto_delete_msg(group_msg, 120))
    asyncio.create_task(auto_delete_msg(message, 120))


# 3. Callbacks for About and Help
@Client.on_callback_query()
async def cb_handler(bot: Client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id

    if data == "home_cb":
        await query.message.edit_text(
            text=Script.START_TXT.format(
                mention=query.from_user.mention,
                user_id=user_id
            ),
            reply_markup=START_BUTTONS,
            disable_web_page_preview=True
        )

    elif data == "about_cb":
        await query.message.edit_text(
            text=Script.ABOUT_TXT.format(
                owner_link=Config.OWNER_LINK,
                user_id=user_id
            ),
            reply_markup=BACK_BUTTON,
            disable_web_page_preview=True
        )

    elif data == "help_cb":
        await query.message.edit_text(
            text=Script.HELP_TXT,
            reply_markup=BACK_BUTTON,
            disable_web_page_preview=True
        )

    elif data == "close_all_st":
        try:
            await query.message.delete()
        except Exception:
            pass
