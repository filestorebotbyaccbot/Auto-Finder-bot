import math
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from database.stories_db import toggle_favorite_db, get_user_favorites_db, stories_col, users_col
from bson.objectid import ObjectId
from plugins.search import build_aesthetic_caption, build_story_buttons, delete_messages_later

ITEMS_PER_PAGE = 10


def build_fav_keyboard(fav_stories: list, page: int = 0):
    total_items = len(fav_stories)
    total_pages = math.ceil(total_items / ITEMS_PER_PAGE) if total_items > 0 else 1
    page = max(0, min(page, total_pages - 1))
    
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    current_stories = fav_stories[start:end]
    
    keyboard = []
    
    for story in current_stories:
        title = story.get("title", "Untitled")
        if len(title) > 22:
            title = f"{title[:19]}..."
        keyboard.append([InlineKeyboardButton(f"⭐ {title}", callback_data=f"catstory#{story['_id']}")])
    
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Bᴀᴄᴋ", callback_data=f"fav_page#{page - 1}"))
    
    nav_row.append(InlineKeyboardButton("❌ Cʟᴏsᴇ", callback_data="close_all_st"))
    
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Nᴇxᴛ ➡️", callback_data=f"fav_page#{page + 1}"))
    
    keyboard.append(nav_row)
    
    header_text = (
        f"⭐ <b>─── ⟨ ʏᴏᴜʀ Fᴀᴠᴏʀɪᴛᴇ sᴛᴏʀɪᴇs ⟩ ───</b> ⭐\n"
        f"📊 <b>Page ({page + 1}/{total_pages}) | Total: {total_items} Stories</b>\n\n"
        "👇 <b>Select any story below to open:</b>"
    )
    
    return InlineKeyboardMarkup(keyboard), header_text


# 1. /favorites Command Handler
@Client.on_message(filters.command(["favorites", "fav", "mybook"]) & (filters.private | filters.group))
async def user_favorites_cmd(bot: Client, message: Message):
    user_id = message.from_user.id
    fav_stories = await get_user_favorites_db(user_id)

    if not fav_stories:
        msg = await message.reply_text(
            "⭐ <b>आपने अभी तक कोई स्टोरी Favorites में ऐड नहीं की है!</b>\n"
            "<i>किसी भी स्टोरी के नीचे ⭐ Add Favorite बटन पर क्लिक करके सेव करें।</i>",
            parse_mode=ParseMode.HTML
        )
        return asyncio.create_task(delete_messages_later([msg, message], 20))

    markup, text_content = build_fav_keyboard(fav_stories, page=0)

    msg = await message.reply_text(
        text=text_content,
        reply_markup=markup,
        parse_mode=ParseMode.HTML
    )

    asyncio.create_task(delete_messages_later([msg, message], 180))


# 2. Favorite Toggle Callback Handler
@Client.on_callback_query(filters.regex(r"^fav#toggle#"))
async def toggle_favorite_cb(bot: Client, query: CallbackQuery):
    story_id = query.data.split("#")[2]
    user_id = query.from_user.id

    is_added, alert_msg = await toggle_favorite_db(user_id, story_id)
    await query.answer(alert_msg, show_alert=False)

    # Refresh card buttons live
    story = await stories_col.find_one({"_id": ObjectId(story_id)})
    if story:
        updated_markup = build_story_buttons(story, is_fav=is_added)
        try:
            await query.message.edit_reply_markup(reply_markup=updated_markup)
        except Exception:
            pass


# 3. Favorites Pagination Callback
@Client.on_callback_query(filters.regex(r"^fav_page#"))
async def fav_pagination_cb(bot: Client, query: CallbackQuery):
    target_page = int(query.data.split("#")[1])
    fav_stories = await get_user_favorites_db(query.from_user.id)

    if not fav_stories:
        return await query.answer("❌ No favorite stories found!", show_alert=True)

    markup, text_content = build_fav_keyboard(fav_stories, page=target_page)

    try:
        await query.message.edit_text(
            text=text_content,
            reply_markup=markup,
            parse_mode=ParseMode.HTML
        )
    except Exception:
        pass
    await query.answer()

