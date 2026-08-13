from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberUpdated
from pyrogram.enums import ChatMemberStatus
from config import Config
from database.stories_db import set_welcome_db, get_welcome_db

# Group Buttons
GROUP_START_BUTTONS = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("💬 Support Group", url=Config.SUPPORT_GROUP),
        InlineKeyboardButton("👤 Owner", url=Config.OWNER_LINK)
    ],
    [
        InlineKeyboardButton("📢 Story Channel", url=Config.STORY_CHANNEL)
    ]
])


# 1. /setwelcome Command (Group Admin Only)
@Client.on_message(filters.command("setwelcome") & ~filters.private)
async def set_custom_welcome(bot: Client, message: Message):
    try:
        # Check Admin Rights
        user_member = await message.chat.get_member(message.from_user.id)
        if user_member.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
            return await message.reply_text("⛔ **Only Group Admins can set welcome messages!**")

        # Extract Text
        if len(message.command) < 2:
            return await message.reply_text(
                "⚠️ **उपयोग करने का तरीका:**\n\n"
                "`/setwelcome Welcome {mention} to {chat}! Enjoy reading stories here.`\n\n"
                "💡 **Variables:**\n"
                "• `{mention}` - User link\n"
                "• `{name}` - First name\n"
                "• `{chat}` - Group Name"
            )

        custom_text = message.text.split(None, 1)[1]
        await set_welcome_db(message.chat.id, custom_text)
        
        await message.reply_text("✅ **Custom Welcome Message successfully set for this group!**")

    except Exception as e:
        print(f"⚠️ Set Welcome Error: {e}")
        await message.reply_text(f"❌ **Error:** `{e}`\n\n*(Make sure I am Admin in this group)*")


# 2. Group /start Command
@Client.on_message(filters.command("start") & ~filters.private)
async def group_start_cmd(bot: Client, message: Message):
    user = message.from_user
    chat = message.chat

    group_text = (
        f"👋 **Welcome to {chat.title}!**\n\n"
        f"Hello {user.mention}, I am active here to help you search and play your favorite stories! "
        f"Just type any story name in this group to search."
    )
    
    await message.reply_text(
        text=group_text,
        reply_markup=GROUP_START_BUTTONS,
        disable_web_page_preview=True
    )


# 3. Auto Welcome New Members Handler
@Client.on_chat_member_updated()
async def auto_welcome_new_members(bot: Client, event: ChatMemberUpdated):
    try:
        if (
            (event.old_chat_member is None or event.old_chat_member.status == ChatMemberStatus.BANNED) 
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
        print(f"⚠️ Welcome Handler Error: {e}")
