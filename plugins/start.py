from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from script import Script
from config import Config

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
        InlineKeyboardButton("👤 Developer", url=Config.OWNER_LINK)
    ]
])

BACK_BUTTON = InlineKeyboardMarkup([
    [InlineKeyboardButton("🔙 Back to Home", callback_data="home_cb")]
])

@Client.on_message(filters.command("start") & filters.private)
async def start_cmd(bot: Client, message: Message):
    user = message.from_user
    
    # 1. Reply to User
    await message.reply_text(
        text=Script.START_TXT.format(
            mention=user.mention,
            user_id=user.id
        ),
        reply_markup=START_BUTTONS,
        disable_web_page_preview=True
    )

    # 2. Send User Log Notification to LOG_CHANNEL
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
