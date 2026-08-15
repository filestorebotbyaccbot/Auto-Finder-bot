import math
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode
from database.stories_db import*

ITEMS_PER_PAGE = 10  # 10 Buttons per page limit


# --- Helper Function for Background Message Auto-Deletion ---
async def delete_msg_later(msg: Message, delay: int = 300):
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except Exception:
        pass


# --- Helper Function to Build Aesthetic HTML Caption ---
def build_aesthetic_caption(story: dict) -> str:
    """
    Constructs screenshot-style UI layout with Expandable Blockquote description
    (Unified design for ALL preview popups/messages)
    """
    title = story.get("title", "Unknown Story")
    status = story.get("status", "Ongoing")
    platform = story.get("platform", "Pocket FM")
    genre = story.get("category", story.get("genre", "General")).capitalize()
    episodes = story.get("episodes", "1 / ∞")
    description = story.get("description", "No description available for this story.")

    # Status Emoji Logic
    status_emoji = "🟢" if str(status).lower() in ["completed", "complete"] else "♨️"

    caption = (
        f"<b>{status_emoji}Story : {title}</b>\n"
        f"<b>🔰Status : {str(status).capitalize()}</b>\n"
        f"<b>🖥️Platform : {platform}</b>\n"
        f"<b>🧩Genre : {genre}</b>\n"
        f"<b>🎬Episodes : {episodes}</b>\n"
        f"═══════════════════\n"
        f"📝 <b>Story Description :-</b>\n"
        f"<blockquote expandable>{description}</blockquote>\n\n"
        f"⏱️ <i>This message will auto-delete in 5 minutes.</i>"
    )
    return caption


def get_stories_keyboard(titles_list, page=0):
    total_items = len(titles_list)
    total_pages = math.ceil(total_items / ITEMS_PER_PAGE) if total_items > 0 else 1
    
    # Keep page within boundaries
    page = max(0, min(page, total_pages - 1))
    
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    current_page_titles = titles_list[start:end]
    
    keyboard = []
    
    # 1. Add 10 Story Buttons
    for title in current_page_titles:
        # Callback data embeds title snippet
        keyboard.append([InlineKeyboardButton(f"📖 {title}", callback_data=f"all_st#{title[:25]}")])
    
    # 2. Add Navigation Row (Back | Close | Next)
    nav_row = []
    
    # Back Button (Hide on 1st page)
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Back", callback_data=f"all_page#{page - 1}"))
    
    # Close Button (Always visible)
    nav_row.append(InlineKeyboardButton("❌ Close", callback_data="close_all_st"))
    
    # Next Button (Hide on last page)
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"all_page#{page + 1}"))
    
    keyboard.append(nav_row)
    
    return InlineKeyboardMarkup(keyboard), page + 1, total_pages


# 1. Main Command Handler (/allstories & /filter)
@Client.on_message(filters.command(["allstories", "filter"]))
async def list_stories_handler(bot: Client, message: Message):
    titles = await get_all_titles()
    
    if not titles:
        return await message.reply_text("📚 **No stories found in database!**")
    
    markup, current_page, total_pages = get_stories_keyboard(titles, page=0)
    
    await message.reply_text(
        text=f"📚 <b>Available Stories List (Page {current_page}/{total_pages}):</b>\n\nTap any story button below to play ▶️:",
        reply_markup=markup,
        parse_mode=ParseMode.HTML
    )


# 2. Callback Handler for Pagination Buttons (Next / Back)
@Client.on_callback_query(filters.regex(r"^all_page#"))
async def stories_pagination_callback(bot: Client, query: CallbackQuery):
    target_page = int(query.data.split("#")[1])
    titles = await get_all_titles()
    
    if not titles:
        return await query.answer("❌ No stories found!", show_alert=True)
    
    markup, current_page, total_pages = get_stories_keyboard(titles, page=target_page)
    
    await query.message.edit_text(
        text=f"📚 <b>Available Stories List (Page {current_page}/{total_pages}):</b>\n\nTap any story button below to play ▶️:",
        reply_markup=markup,
        parse_mode=ParseMode.HTML
    )
    await query.answer()


# 3. Callback Handler for Story Button Selection
@Client.on_callback_query(filters.regex(r"^all_st#"))
async def story_item_click_callback(bot: Client, query: CallbackQuery):
    selected_title = query.data.split("#", 1)[1]
    
    # Fetch story details from MongoDB
    story = await stories_col.find_one({"title": selected_title})
    
    if not story:
        return await query.answer("❌ Story no longer exists!", show_alert=True)
    
    caption = build_aesthetic_caption(story)
    
    button = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎧 Listen / Play Story", url=story["link"])],
        [InlineKeyboardButton("❌ Close", callback_data="close_all_st")]
    ])
    
    reply_msg = None
    try:
        reply_msg = await bot.send_photo(
            chat_id=query.message.chat.id,
            photo=story["photo"],
            caption=caption,
            reply_markup=button,
            parse_mode=ParseMode.HTML
        )
    except Exception:
        reply_msg = await bot.send_message(
            chat_id=query.message.chat.id,
            text=caption,
            reply_markup=button,
            disable_web_page_preview=True,
            parse_mode=ParseMode.HTML
        )

    if reply_msg:
        asyncio.create_task(delete_msg_later(reply_msg, 300))

    await query.answer()


# 4. Callback Handler for Close Button
@Client.on_callback_query(filters.regex(r"^close_all_st$"))
async def close_menu_callback(bot: Client, query: CallbackQuery):
    try:
        await query.message.delete()
    except Exception:
        pass
