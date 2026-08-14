import math
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.stories_db import (
    search_story_db, 
    stories_col, 
    get_all_categories_db, 
    get_stories_by_category_paged_db
)

PAGE_SIZE = 5  # एक पेज पर कितनी स्टोरीज दिखेंगी

# --- Helper Function for Background Message Auto-Deletion ---
async def delete_messages_later(messages_to_delete: list, delay_seconds: int):
    """Executes message deletion in the background without blocking Pyrogram loop"""
    await asyncio.sleep(delay_seconds)
    for msg in messages_to_delete:
        if msg:
            try:
                await msg.delete()
            except Exception:
                pass


# --- Helper Function to Build Category Pagination Keyboard ---
def build_category_keyboard(stories: list, category_name: str, page: int, total_pages: int):
    buttons = []
    
    # Story Item Buttons
    for story in stories:
        btn_text = f"📖 {story['title'][:22]}"
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"catstory#{story['_id']}")])

    # Pagination Navigation Row (Prev | Page X/Y | Next)
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("◀️ Prev", callback_data=f"pgcat#{category_name}#{page - 1}"))
    
    nav_row.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="ignore_page_click"))
    
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("Next ▶️", callback_data=f"pgcat#{category_name}#{page + 1}"))

    buttons.append(nav_row)
    buttons.append([InlineKeyboardButton("❌ Close", callback_data="close_all_st")])
    
    return InlineKeyboardMarkup(buttons)


@Client.on_message(
    (filters.group | filters.private) & 
    filters.text & 
    ~filters.command(["start", "addstory", "request", "allstories", "filter", "categories", "deletestory", "clearallstories"])
)
async def search_handler(bot: Client, message: Message):
    user_query = message.text.strip()
    if len(user_query) < 2:
        return

    # -------------------------------------------------------------
    # 🔍 1. CATEGORY SEARCH WITH PAGINATION (-drama, #drama, /drama)
    # -------------------------------------------------------------
    clean_cat_query = user_query.lstrip("-/#").strip().capitalize()
    all_categories = await get_all_categories_db()
    
    if clean_cat_query in [cat.capitalize() for cat in all_categories]:
        page = 1
        stories, total_count = await get_stories_by_category_paged_db(clean_cat_query, page=page, page_size=PAGE_SIZE)
        
        if not stories:
            msg = await message.reply_text(f"❌ `{clean_cat_query}` कैटेगरी में कोई स्टोरी नहीं मिली!")
            return asyncio.create_task(delete_messages_later([msg], 30))

        total_pages = math.ceil(total_count / PAGE_SIZE)
        markup = build_category_keyboard(stories, clean_cat_query, page, total_pages)

        cat_msg = await message.reply_text(
            f"📁 **Category Found:** `{clean_cat_query}`\n"
            f"📊 **Total Stories:** `{total_count}`\n\n"
            f"Select a story below to read:\n\n"
            f"⏱️ _This message will auto-delete in 2 minutes._",
            reply_markup=markup
        )

        to_delete = [cat_msg]
        if message.chat.type.value != "private":
            to_delete.append(message)

        return asyncio.create_task(delete_messages_later(to_delete, 120))


    # -------------------------------------------------------------
    # 🔎 2. REGULAR TITLE SEARCH & FUZZY MATCHING
    # -------------------------------------------------------------
    if message.text.startswith("/"):
        return

    result = await search_story_db(user_query)
    
    # Exact Match
    if result["type"] == "exact":
        story = result["data"]
        category_name = story.get("category", "General")
        
        caption = (
            f"📖 **Story Found:** `{story['title']}`\n"
            f"🏷️ **Category:** `{category_name.capitalize()}`\n\n"
            f"✨ Tap the button below to play ▶️ the complete story:\n\n"
            f"⏱️ _This message will auto-delete in 5 minutes._"
        )
        
        button = InlineKeyboardMarkup([
            [InlineKeyboardButton("📖 Play Story", url=story["link"])]
        ])

        reply_msg = None
        try:
            reply_msg = await message.reply_photo(photo=story["photo"], caption=caption, reply_markup=button)
        except Exception:
            reply_msg = await message.reply_text(text=caption, reply_markup=button, disable_web_page_preview=True)

        to_delete = [reply_msg]
        if message.chat.type.value != "private":
            to_delete.append(message)

        asyncio.create_task(delete_messages_later(to_delete, 300))

    # Suggestions
    elif result["type"] == "suggestions":
        suggestions = result["data"]
        buttons = []
        row = []
        for title in suggestions:
            btn_text = f"📖 {title[:18]}"
            row.append(InlineKeyboardButton(btn_text, callback_data=f"sg#{title[:25]}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)

        buttons.append([InlineKeyboardButton("❌ Close", callback_data="close_all_st")])
        markup = InlineKeyboardMarkup(buttons)
        
        suggestion_msg = await message.reply_text(
            f"❓ **Did you mean one of these stories?**\n\nSelect a story from below to read:\n\n⏱️ _This message will auto-delete in 2 minutes._",
            reply_markup=markup
        )

        asyncio.create_task(delete_messages_later([suggestion_msg], 120))


# --- Callback Query Handler for Category Pagination (Prev/Next) ---
@Client.on_callback_query(filters.regex(r"^pgcat#"))
async def category_pagination_callback(bot: Client, query: CallbackQuery):
    _, category_name, page_str = query.data.split("#")
    page = int(page_str)
    
    stories, total_count = await get_stories_by_category_paged_db(category_name, page=page, page_size=PAGE_SIZE)
    
    if not stories:
        return await query.answer("❌ No stories found on this page!", show_alert=True)

    total_pages = math.ceil(total_count / PAGE_SIZE)
    markup = build_category_keyboard(stories, category_name, page, total_pages)

    await query.message.edit_text(
        f"📁 **Category Found:** `{category_name}`\n"
        f"📊 **Total Stories:** `{total_count}`\n\n"
        f"Select a story below to read:\n\n"
        f"⏱️ _This message will auto-delete in 2 minutes._",
        reply_markup=markup
    )
    await query.answer()


# Ignore page counter click
@Client.on_callback_query(filters.regex("^ignore_page_click$"))
async def ignore_page_click_cb(bot: Client, query: CallbackQuery):
    await query.answer()


# --- Callback Query Handler for Suggestion Buttons ---
@Client.on_callback_query(filters.regex(r"^sg#"))
async def suggestion_click_callback(bot: Client, query: CallbackQuery):
    selected_title = query.data.split("#", 1)[1]
    story = await stories_col.find_one({"title": selected_title})
    
    if not story:
        return await query.answer("❌ Story no longer exists in database!", show_alert=True)

    try:
        await query.message.delete()
    except Exception:
        pass

    category_name = story.get("category", "General")
    caption = (
        f"📖 **Story Found:** `{story['title']}`\n"
        f"🏷️ **Category:** `{category_name.capitalize()}`\n\n"
        f"✨ Tap below to play ▶️ the complete story:\n\n"
        f"⏱️ _This message will auto-delete in 5 minutes._"
    )
    
    button = InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 Play Story", url=story["link"])]
    ])

    reply_msg = None
    try:
        reply_msg = await bot.send_photo(chat_id=query.message.chat.id, photo=story["photo"], caption=caption, reply_markup=button)
    except Exception:
        reply_msg = await bot.send_message(chat_id=query.message.chat.id, text=caption, reply_markup=button, disable_web_page_preview=True)

    if reply_msg:
        asyncio.create_task(delete_messages_later([reply_msg], 300))


# Callback for Close Button
@Client.on_callback_query(filters.regex("^close_all_st$"))
async def close_callback(bot: Client, query: CallbackQuery):
    try:
        await query.message.delete()
    except Exception:
        pass
