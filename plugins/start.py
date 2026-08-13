from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberUpdated
from pyrogram.enums import ChatMemberStatus
from script import Script
from config import Config
from database.stories_db import add_user_db, set_welcome_db, get_welcome_db

# --- Standard Buttons ---
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


# --- 1. /start Command (Private & Group Support) ---
@Client.on_message(filters.command("start"))
async def start_cmd(bot: Client, message: Message):
    user = message.from_user
    chat = message.chat
    
    # --- IF USED IN GROUP ---
    if chat.type != "private":
        welcome_text = (
            f"👋 **Welcome to {chat.title}!**\n\n"
            f"Hello {user.mention}, I am active here to help you search and play your favorite stories! "
            f"Just type any story name in this group to search."
        )
        return await message.reply_text(
            text=welcome_text,
            reply_markup=GROUP_START_BUTTONS,
            disable_web_page_preview=True
        )

    # --- IF USED IN PRIVATE CHAT ---
    await add_user_db(
        user_id=user.id,
        first_name=user.first_name,
        username=user.username
    )

    await message.reply_text(
        text=Script.START_TXT.format(
            mention=user.mention,
            user_id=user.id
        ),
        reply_markup=START_BUTTONS,
        disable_web_page_preview=True
    )

    # Log Channel Notification
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


# --- 2. Admin Command to Set Custom Welcome Message ---
@Client.on_message(filters.command("setwelcome") & ~filters.private)
async def set_custom_welcome(bot: Client, message: Message):
    # Check if user is Group Admin
    user_status = await message.chat.get_member(message.from_user.id)
    if user_status.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
        return await message.reply_text("⛔ **Only Group Admins can set welcome messages!**")

    # Extract Custom Text
    if len(message.command) < 2:
        return await message.reply_text(
            "⚠️ **उपयोग करने का तरीका:**\n\n"
            "`/setwelcome Welcome {mention} to {chat}! Enjoy reading stories here.`\n\n"
            "💡 **Shortcodes:**\n"
            "• `{mention}` - User mention\n"
            "• `{name}` - User First Name\n"
            "• `{chat}` - Group Name"
        )

    custom_text = message.text.split(None, 1)[1]
    await set_welcome_db(message.chat.id, custom_text)
    
    await message.reply_text("✅ **Custom Welcome Message successfully updated for this group!**")


# --- 3. New Member Auto-Welcome Handler ---
@Client.on_chat_member_updated()
async def auto_welcome_new_members(bot: Client, event: ChatMemberUpdated):
    # Trigger only when a new member joins/is added
    if event.old_chat_member is None and event.new_chat_member is not None:
        user = event.new_chat_member.user
        chat = event.chat
        
        # Don't welcome bots
        if user.is_bot:
            return

        custom_text = await get_welcome_db(chat.id)
        
        if custom_text:
            text = custom_text.format(
                mention=user.mention,
                name=user.first_name,
                chat=chat.title
            )
        else:
            text = (
                f"👋 Welcome {user.mention} to **{chat.title}**! ✨\n\n"
                f"Enjoy your stay and search for stories anytime!"
            )

        try:
            await bot.send_message(
                chat_id=chat.id,
                text=text,
                reply_markup=GROUP_START_BUTTONS
            )
        except Exception as e:
            print(f"⚠️ Welcome error: {e}")


# --- 4. Callback Query Handler ---
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
