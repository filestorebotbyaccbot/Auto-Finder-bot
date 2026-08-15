import math
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from database.stories_db import rate_story_db, get_trending_stories_db, stories_col
from bson.objectid import ObjectId
from plugins.search import build_aesthetic_caption, build_story_buttons, delete_messages_later

ITEMS_PER_PAGE = 10
RANK_EMOJIS = ["🥇", "🥈", "🥉", "🏅", "🏅", "🏅", "🏅", "🏅", "🏅", "🏅"]


# Clean Title Button Helper
def clean_trending_button_text(rank: int, title: str, likes: int, max_len: int = 18) -> str:
    badge = RANK_EMOJIS[rank - 1] if rank <= len(RANK_EMOJIS) else "🏅"
    clean_title = str(title).strip()
    if len(clean_title) > max_len:
        clean_title = f"{clean_title[:max_len-3]}..."
    return f"{badge} #{rank} {clean_title} ({likes} 👍)"


# Dynamic Keyboard Generator with Pagination
def build_trending_keyboard(stories_list: list, page: int = 0):
    total_items = len(stories_list)
    total_pages = math.ceil(total_items / ITEMS_PER_PAGE) if total_items > 0 else 1
    page = max(0, min(page, total_pages - 1))
    
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    current_stories = stories_list[start:end]
    
    keyboard = []
    
    # 1. Top Stories Rank Buttons (10 Per Page)
    for idx, story in enumerate(current_stories, start=start + 1):
        title = story.get("title", "Untitled")
        likes = len(story.get("likes", [])) if isinstance(story.get("likes"), list) else story.get("likes", 0)
        btn_label = clean_trending_button_text(idx, title, likes)
        keyboard.append([InlineKeyboardButton(btn_label, callback_data=f"catstory#{story['_id']}")])
    
    # 2. Navigation Row (Back | Close | Next)
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Bᴀᴄᴋ", callback_data=f"tr_page#{page - 1}"))
    
    nav_row.append(InlineKeyboardButton("❌ Cʟᴏsᴇ", callback_data="close_all_st"))
    
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Nᴇxᴛ ➡️", callback_data=f"tr_page#{page + 1}"))
    
    keyboard.append(nav_row)
    
    # Clean Text Header
    header_text = (
        f"🏆 <b>─── ⟨ ᴛᴏᴘ ᴛʀᴇɴᴅɪɴɢ sᴛᴏʀɪᴇs ⟩ ───</b> 🏆\n"
        f"📊 <b>Page ({page + 1}/{total_pages})</b>\n\n"
        "╭───────────────────────────\n"
    )
    for idx, story in enumerate(current_stories, start=start + 1):
        rank_icon = RANK_EMOJIS[idx - 1] if idx <= len(RANK_EMOJIS) else "🏅"
        header_text += f"│ <b>{rank_icon} #{idx}.</b> <code>{story.get('title', 'Untitled')}</code>\n"
    
    header_text += (
        "╰───────────────────────────\n\n"
        "👇 <b>Select a story button below to listen:</b>"
    )
    
    return InlineKeyboardMarkup(keyboard), header_text


# 1. Trending Command Handler
@Client.on_message(filters.command(["trending", "popular", "tranding"]) & (filters.group | filters.private))
async def trending_cmd_handler(bot: Client, message: Message):
    wait_msg = await message.reply_text("<b>Pʟᴇᴀsᴇ Wᴀɪᴛ...</b>", parse_mode=ParseMode.HTML)
    
    # DB से टॉप स्टोरीज निकालें
    trending_stories = await get_trending_stories_db(limit=50)

    try:
        await wait_msg.delete()
    except Exception:
        pass

    if not trending_stories:
        msg = await message.reply_text("❌ <b>अभी कोई ट्रेंडिंग स्टोरी उपलब्ध नहीं है!</b>", parse_mode=ParseMode.HTML)
        return asyncio.create_task(delete_messages_later([msg, message], 15))

    markup, text_content = build_trending_keyboard(trending_stories, page=0)

    msg = await message.reply_text(
        text=text_content,
        reply_markup=markup,
        parse_mode=ParseMode.HTML
    )

    # Auto Delete After 3 Minutes
    asyncio.create_task(delete_messages_later([msg, message], 180))


# 2. Pagination Callback Handler
@Client.on_callback_query(filters.regex(r"^tr_page#"))
async def trending_pagination_cb(bot: Client, query: CallbackQuery):
    target_page = int(query.data.split("#")[1])
    trending_stories = await get_trending_stories_db(limit=50)

    if not trending_stories:
        return await query.answer("❌ No stories found!", show_alert=True)

    markup, text_content = build_trending_keyboard(trending_stories, page=target_page)

    try:
        await query.message.edit_text(
            text=text_content,
            reply_markup=markup,
            parse_mode=ParseMode.HTML
        )
    except Exception:
        pass
    await query.answer()


# 3. Rating Callback Handler (👍 / 👎 Buttons Click Event)
@Client.on_callback_query(filters.regex(r"^rate#"))
async def rate_story_cb(bot: Client, query: CallbackQuery):
    _, rating_type, story_id = query.data.split("#")
    user_id = query.from_user.id

    success, total_likes = await rate_story_db(story_id, user_id, rating_type)

    if not success:
        return await query.answer("❌ Failed to update rating!", show_alert=True)

    story = await stories_col.find_one({"_id": ObjectId(story_id)})
    if not story:
        return await query.answer("❌ Story no longer exists!", show_alert=True)

    updated_buttons = build_story_buttons(story)

    try:
        await query.message.edit_reply_markup(reply_markup=updated_buttons)
    except Exception:
        pass

    action_text = "Liked! 👍" if rating_type == "like" else "Disliked! 👎"
    await query.answer(f"Thanks! Story {action_text}")
