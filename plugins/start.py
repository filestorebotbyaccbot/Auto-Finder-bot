import sys
import os
import asyncio
from bson.objectid import ObjectId
from pyrogram import Client, filters, enums 
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from script import Script
from config import Config
from database.stories_db import (
    add_user_db, 
    stories_col, 
    get_random_story_db,
    toggle_favorite_db,
    get_user_favorites_db,
    is_story_favorite_db
)
from plugins.search import build_aesthetic_caption, build_story_buttons, delete_messages_later

# PM Standard Start Buttons (Styled with Small Caps Text)
START_BUTTONS = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("📢 Sᴛᴏʀʏ Cʜᴀɴɴᴇʟ", url=Config.STORY_CHANNEL),
        InlineKeyboardButton("💬 Sᴜᴘᴘᴏʀᴛ Gʀᴏᴜᴘ", url=Config.SUPPORT_GROUP)
    ],
    [
        InlineKeyboardButton("ℹ️ Aʙᴏᴜᴛ", callback_data="about_cb"),
        InlineKeyboardButton("🛠️ Hᴇʟᴘ", callback_data="help_cb")
    ],
    [
        InlineKeyboardButton("⭐ Mʏ Fᴀᴠᴏʀɪᴛᴇs", callback_data="show_favs")
    ],
    [
        InlineKeyboardButton("🎲 Sᴜʀᴘʀɪsᴇ Mᴇ / Rᴀɴᴅᴏᴍ", callback_data="fetch_next_random")
    ],
    [
        InlineKeyboardButton("👤 Dᴇᴠᴇʟᴏᴘᴇʀ", url=Config.OWNER_LINK)
    ]
])

# Group Start Buttons (Styled with Small Caps Text)
GROUP_START_BUTTONS = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("💬 Sᴜᴘᴘᴏʀᴛ Gʀᴏᴜᴘ", url=Config.SUPPORT_GROUP),
        InlineKeyboardButton("👤 Oᴡɴᴇʀ", url=Config.OWNER_LINK)
    ],
    [
        InlineKeyboardButton("📢 Sᴛᴏʀʏ Cʜᴀɴɴᴇʟ", url=Config.STORY_CHANNEL)
    ]
])

BACK_BUTTON = InlineKeyboardMarkup([
    [InlineKeyboardButton("🔙 Bᴀᴄᴋ ᴛᴏ Hᴏᴍᴇ", callback_data="home_cb")]
])


# Helper function for non-blocking Auto-Delete
async def auto_delete_msg(message: Message, delay: int):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass


# Helper function to build Favorites List Keyboard
def build_favs_keyboard(fav_stories: list):
    buttons = []
    for story in fav_stories:
        btn_text = f"📖 {story['title'][:22]}"
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"catstory#{story['_id']}")])
    
    buttons.append([InlineKeyboardButton("🔙 Bᴀᴄᴋ ᴛᴏ Hᴏᴍᴇ", callback_data="home_cb")])
    return InlineKeyboardMarkup(buttons)


# 1. Private Chat /start Handler
@Client.on_message(filters.command("start") & filters.private)
async def private_start_cmd(bot: Client, message: Message):
    # ⚡ Instant Wait Response
    wait_msg = await message.reply_text("<b>Pʟᴇᴀsᴇ Wᴀɪᴛ...</b>", parse_mode=ParseMode.HTML)
    
    user = message.from_user

    # Returns True ONLY if user is NEW, False if user ALREADY EXISTS in DB
    is_new_user = await add_user_db(
        user_id=user.id,
        first_name=user.first_name,
        username=user.username
    )

    # 🗑️ Delete Wait Message
    try:
        await wait_msg.delete()
    except Exception:
        pass

    # 📩 Send Main Start Message
    start_msg = await message.reply_text(
        text=Script.START_TXT.format(
            mention=user.mention,
            user_id=user.id,
            bot_name=bot.me.first_name
        ),
        reply_markup=START_BUTTONS,
        disable_web_page_preview=True,
        parse_mode=ParseMode.HTML
    )

    # Log Channel Notification
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


# 2. Group /start Handler
@Client.on_message(filters.command("start") & ~filters.private)
async def group_start_cmd(bot: Client, message: Message):
    # ⚡ Instant Wait Response
    wait_msg = await message.reply_text("<b>Pʟᴇᴀsᴇ Wᴀɪᴛ...</b>", parse_mode=ParseMode.HTML)

    user = message.from_user
    chat = message.chat

    # 🗑️ Delete Wait Message
    try:
        await wait_msg.delete()
    except Exception:
        pass

    group_text = (
        f"👋 <b>ʜᴇʟʟᴏ {user.mention}! ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ {chat.title}!</b>\n\n"
        f"ɪ ᴀᴍ ᴀᴄᴛɪᴠᴇ ʜᴇʀᴇ ᴛᴏ ʜᴇʟᴘ ʏᴏᴜ ꜱᴇᴀʀᴄʜ ᴀɴᴅ ꜰɪɴᴅ ʏᴏᴜʀ ꜰᴀᴠᴏʀɪᴛᴇ ꜱᴛᴏʀɪᴇꜱ. "
        f"ᴊᴜꜱᴛ ᴛʏᴘᴇ ᴀɴʏ ꜱᴛᴏʀʏ ɴᴀᴍᴇ ᴅɪʀᴇᴄᴛʟʏ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ ᴛᴏ ꜱᴇᴀʀᴄʜ!\n\n"
        f"⏱️ <i>ᴛʜɪꜱ ᴍᴇꜱꜱᴀɢᴇ ᴡɪʟʟ ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ ɪɴ 2 ᴍɪɴᴜᴛᴇꜱ.</i>"
    )

    group_msg = await message.reply_text(
        text=group_text,
        reply_markup=GROUP_START_BUTTONS,
        disable_web_page_preview=True,
        parse_mode=ParseMode.HTML
    )

    asyncio.create_task(auto_delete_msg(group_msg, 120))
    asyncio.create_task(auto_delete_msg(message, 120))


# 3. /favorites Command Handler
@Client.on_message(filters.command(["favorites", "fav", "mybook"]) & filters.private)
async def user_favorites_command(bot: Client, message: Message):
    user_id = message.from_user.id
    fav_stories = await get_user_favorites_db(user_id)

    if not fav_stories:
        return await message.reply_text(
            "⭐ <b>आपकी फेवरेट लिस्ट अभी खाली है!</b>\n\n"
            "किसी भी स्टोरी कार्ड पर मौजूद <b>'⭐ Aᴅᴅ Fᴀᴠᴏʀɪᴛᴇ'</b> बटन पर क्लिक करके उसे यहाँ सेव करें।",
            parse_mode=ParseMode.HTML
        )

    markup = build_favs_keyboard(fav_stories)
    await message.reply_text(
        f"⭐ <b><u>YOUR FAVORITE STORIES</u></b>\n\n"
        f"Total Saved Stories: <b>{len(fav_stories)}</b>\n"
        f"नीचे दी गई लिस्ट में से अपनी पसंद की स्टोरी चुनें:",
        reply_markup=markup,
        parse_mode=ParseMode.HTML
    )


# 4. System Restart Command
@Client.on_message(filters.command("restart") & filters.private)
async def restart_bot_handler(bot: Client, message: Message):
    if message.from_user.id not in Config.ADMIN_IDS:
        return await message.reply_text("⛔ <b>ᴀᴄᴄᴇꜱꜱ ᴅᴇɴɪᴇᴅ! ᴏɴʟʏ ᴀᴅᴍɪɴꜱ ᴄᴀɴ ʀᴇꜱᴛᴀʀᴛ.</b>")

    restart_msg = await message.reply_text(
        "🔄 <b>ʙᴏᴛ ɪꜱ ʀᴇꜱᴛᴀʀᴛɪɴɢ... ᴘʟᴇᴀꜱᴇ ᴡᴀɪᴛ 3-5 ꜱᴇᴄᴏɴᴅꜱ!</b>",
        parse_mode=ParseMode.HTML
    )

    try:
        with open("restart_info.txt", "w") as f:
            f.write(f"{restart_msg.chat.id}\n{restart_msg.id}")
    except Exception:
        pass

    try:
        await bot.stop()
    except Exception:
        pass

    os._exit(0)


# 5. Callback Query Handlers
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

    elif data == "show_favs":
        fav_stories = await get_user_favorites_db(user_id)
        
        if not fav_stories:
            return await query.answer("⭐ आपकी फेवरेट लिस्ट अभी खाली है!", show_alert=True)

        markup = build_favs_keyboard(fav_stories)
        await query.message.edit_text(
            f"⭐ <b><u>YOUR FAVORITE STORIES</u></b>\n\n"
            f"Total Saved Stories: <b>{len(fav_stories)}</b>\n"
            f"नीचे दी गई लिस्ट में से अपनी पसंद की स्टोरी चुनें:",
            reply_markup=markup,
            parse_mode=ParseMode.HTML
        )
        await query.answer()

    elif data.startswith("fav#toggle#"):
        story_id = data.split("#")[2]
        is_now_fav, alert_msg = await toggle_favorite_db(user_id, story_id)
        
        # Refetch story to update inline UI buttons
        try:
            story = await stories_col.find_one({"_id": ObjectId(story_id)})
        except Exception:
            story = None

        if story:
            updated_markup = build_story_buttons(story, is_fav=is_now_fav)
            try:
                await query.message.edit_reply_markup(reply_markup=updated_markup)
            except Exception:
                pass

        await query.answer(alert_msg, show_alert=False)

    elif data == "fetch_next_random":
        story = await get_random_story_db()
        
        if not story:
            return await query.answer("❌ डेटाबेस में कोई स्टोरी उपलब्ध नहीं है!", show_alert=True)

        user_id = query.from_user.id
        is_fav = await is_story_favorite_db(user_id, str(story["_id"]))

        # Dynamic Bot Username Fetch for Hyperlinked Caption
        bot_username = bot.me.username if bot.me else (await bot.get_me()).username

        caption = build_aesthetic_caption(story, bot_username=bot_username)
        buttons = build_story_buttons(story, is_fav=is_fav)

        button_list = buttons.inline_keyboard
        button_list.insert(1, [InlineKeyboardButton("🎲 Nᴇxᴛ Rᴀɴᴅᴏᴍ", callback_data="fetch_next_random")])
        final_markup = InlineKeyboardMarkup(button_list)

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
                reply_markup=final_markup,
                parse_mode=ParseMode.HTML
            )
        except Exception:
            reply_msg = await bot.send_message(
                chat_id=query.message.chat.id,
                text=caption,
                reply_markup=final_markup,
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
