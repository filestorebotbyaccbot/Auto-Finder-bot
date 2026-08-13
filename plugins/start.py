from bson.objectid import ObjectId
from pyrogram import Client, filters
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
        InlineKeyboardButton("🛠️ Help", callback_data="help_cb")
    ],
    [
        InlineKeyboardButton("👤 Developer", url=Config.OWNER_LINK)
    ]
])

BACK_BUTTON = InlineKeyboardMarkup([
    [InlineKeyboardButton("🔙 Back to Home", callback_data="home_cb")]
])


# Private Chat /start Handler (Deep Linking Integrated)
@Client.on_message(filters.command("start") & filters.private)
async def private_start_cmd(bot: Client, message: Message):
    user = message.from_user

    # 1. Save User for Broadcasting
    await add_user_db(
        user_id=user.id,
        first_name=user.first_name,
        username=user.username
    )

    # 2. Check Redirect Payload (/start st_<story_id>)
    if len(message.command) > 1:
        payload = message.command[1]

        # Handle Story Payload
        if payload.startswith("st_"):
            story_id = payload.split("st_", 1)[1]
            story = None

            # Fetch Story by ObjectId or Title
            try:
                story = await stories_col.find_one({"_id": ObjectId(story_id)})
            except Exception:
                story = await stories_col.find_one({"title": story_id})

            if story:
                caption = (
                    f"📖 **Story Found:** `{story['title']}`\n\n"
                    f"✨ Tap the button below to play ▶️ the complete story:"
                )
                button = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📖 Play Story", url=story["link"])],
                    [InlineKeyboardButton("🔙 Home", callback_data="home_cb")]
                ])

                try:
                    return await message.reply_photo(
                        photo=story["photo"],
                        caption=caption,
                        reply_markup=button
                    )
                except Exception:
                    return await message.reply_text(
                        text=caption,
                        reply_markup=button,
                        disable_web_page_preview=True
                    )
            else:
                await message.reply_text("❌ **यह स्टोरी डेटाबेस में नहीं मिली या हटा दी गई है!**")

    # 3. Standard /start Flow (If no payload present)
    await message.reply_text(
        text=Script.START_TXT.format(
            mention=user.mention,
            user_id=user.id
        ),
        reply_markup=START_BUTTONS,
        disable_web_page_preview=True
    )

    # Log Channel Alert
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


# Callbacks for About, Help, Home, and Close
@Client.on_callback_query()
async def cb_handler(bot: Client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id

    if data == "home_cb":
        # Check if message has a photo (from redirected story view)
        if query.message.photo:
            await query.message.delete()
            await bot.send_message(
                chat_id=query.message.chat.id,
                text=Script.START_TXT.format(
                    mention=query.from_user.mention,
                    user_id=user_id
                ),
                reply_markup=START_BUTTONS,
                disable_web_page_preview=True
            )
        else:
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
