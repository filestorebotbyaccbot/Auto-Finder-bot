from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberUpdated
from pyrogram.enums import ChatMemberStatus
from config import Config
from database.stories_db import set_welcome_db, get_welcome_db

GROUP_START_BUTTONS = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("💬 Support Group", url=Config.SUPPORT_GROUP),
        InlineKeyboardButton("👤 Owner", url=Config.OWNER_LINK)
    ],
    [
        InlineKeyboardButton("📢 Story Channel", url=Config.STORY_CHANNEL)
    ]
])

# Fix: Admin status verification with fallback
async def is_admin(chat_id: int, user_id: int, bot: Client) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]
    except Exception:
        return False

@Client.on_message(filters.command(["setwelcome", "setwelcome@InfinityStorysFinderBot"]) & ~filters.private)
async def set_custom_welcome(bot: Client, message: Message):
    # Check User Admin Rights
    if not await is_admin(message.chat.id, message.from_user.id, bot):
        return await message.reply_text("⛔ **Only Group Admins can set welcome messages!**")

    if len(message.command) < 2:
        return await message.reply_text(
            "⚠️ **उपयोग करने का सही तरीका:**\n\n"
            "`/setwelcome Welcome {mention} to {chat}! Enjoy reading stories here.`\n\n"
            "💡 **Available Shortcodes:**\n"
            "• `{mention}` - User Link\n"
            "• `{name}` - First Name\n"
            "• `{chat}` - Group Title"
        )

    custom_text = message.text.split(None, 1)[1]
    
    # DB Save
    await set_welcome_db(message.chat.id, custom_text)
    await message.reply_text("✅ **Custom Welcome Message successfully updated for this group!**")

# Auto-Welcome Handler for New Members
@Client.on_chat_member_updated()
async def auto_welcome_new_members(bot: Client, event: ChatMemberUpdated):
    try:
        # Check if new user joined or was added
        if (
            (event.old_chat_member is None or event.old_chat_member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]) 
            and event.new_chat_member is not None 
            and event.new_chat_member.status == ChatMemberStatus.MEMBER
        ):
            user = event.new_chat_member.user
            chat = event.chat
            
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

            await bot.send_message(
                chat_id=chat.id,
                text=text,
                reply_markup=GROUP_START_BUTTONS,
                disable_web_page_preview=True
            )
    except Exception as e:
        print(f"⚠️ Auto-Welcome Error: {e}")
