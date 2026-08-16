import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from pyrogram.enums import ParseMode
from database.stories_db import get_random_story_db, is_story_favorite_db
from plugins.search import build_aesthetic_caption, build_story_buttons, delete_messages_later

# --- 🎲 RANDOM STORY COMMAND HANDLER ---
@Client.on_message(filters.command(["random", "surpriseme"]) & (filters.group | filters.private))
async def random_story_handler(bot: Client, message: Message):
    """
    Fetches and displays a random story with Like/Dislike rating and 'Another Random' buttons.
    """
    story = await get_random_story_db()
    
    if not story:
        return await message.reply_text("❌ <b>डेटाबेस में कोई स्टोरी उपलब्ध नहीं है!</b>")

    user_id = message.from_user.id
    is_fav = await is_story_favorite_db(user_id, str(story["_id"]))

    # Dynamic Bot Username Fetch
    bot_username = bot.me.username if bot.me else (await bot.get_me()).username

    # Photo/Caption & Rating UI Build करें (bot_username pass kiya)
    caption = build_aesthetic_caption(story, bot_username=bot_username)
    buttons = build_story_buttons(story, is_fav=is_fav)

    # "Next Random" बटन को रेटिंग बटन्स के साथ शामिल करें
    button_list = buttons.inline_keyboard
    button_list.insert(1, [InlineKeyboardButton("🎲 Nᴇxᴛ Rᴀɴᴅᴏᴍ", callback_data="fetch_next_random")])
    final_markup = InlineKeyboardMarkup(button_list)

    reply_msg = None
    try:
        reply_msg = await message.reply_photo(
            photo=story["photo"],
            caption=caption,
            reply_markup=final_markup,
            parse_mode=ParseMode.HTML
        )
    except Exception:
        reply_msg = await message.reply_text(
            text=caption,
            reply_markup=final_markup,
            disable_web_page_preview=True,
            parse_mode=ParseMode.HTML
        )

    # 5 मिनट में ऑटो-डिलीट
    to_delete = [reply_msg]
    if message.chat.type.value != "private":
        to_delete.append(message)

    asyncio.create_task(delete_messages_later(to_delete, 300))


# --- 🎲 CALLBACK QUERY FOR "NEXT RANDOM" BUTTON ---
@Client.on_callback_query(filters.regex("^fetch_next_random$"))
async def next_random_callback(bot: Client, query: CallbackQuery):
    story = await get_random_story_db()
    
    if not story:
        return await query.answer("❌ कोई अन्य स्टोरी नहीं मिली!", show_alert=True)

    user_id = query.from_user.id
    is_fav = await is_story_favorite_db(user_id, str(story["_id"]))

    # Dynamic Bot Username Fetch
    bot_username = bot.me.username if bot.me else (await bot.get_me()).username

    caption = build_aesthetic_caption(story, bot_username=bot_username)
    buttons = build_story_buttons(story, is_fav=is_fav)

    # "Next Random" बटन को रेटिंग बटन्स के साथ जोड़ें
    button_list = buttons.inline_keyboard
    button_list.insert(1, [InlineKeyboardButton("🎲 Nᴇxᴛ Rᴀɴᴅᴏᴍ", callback_data="fetch_next_random")])
    final_markup = InlineKeyboardMarkup(button_list)

    try:
        # फोटो और कैप्शन अपडेट करें
        if query.message.photo:
            await query.message.edit_media(
                media=InputMediaPhoto(media=story["photo"], caption=caption, parse_mode=ParseMode.HTML),
                reply_markup=final_markup
            )
        else:
            await query.message.edit_text(
                text=caption,
                reply_markup=final_markup,
                disable_web_page_preview=True,
                parse_mode=ParseMode.HTML
            )
        await query.answer("🎲 New Random Story Loaded!")
    except Exception:
        # अगर मीडिया एडिट में दिक्कत आए तो पुराना डिलीट करके नया भेजें
        try:
            await query.message.delete()
        except Exception:
            pass
            
        await bot.send_photo(
            chat_id=query.message.chat.id,
            photo=story["photo"],
            caption=caption,
            reply_markup=final_markup,
            parse_mode=ParseMode.HTML
        )
