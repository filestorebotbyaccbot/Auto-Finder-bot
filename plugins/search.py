import math
import asyncio
from bson.objectid import ObjectId
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode
from database.stories_db import (
    search_story_db, 
    stories_col, 
    get_all_categories_db, 
    get_stories_by_category_paged_db,
    get_top_categories_db
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


# --- Helper Function to Build Aesthetic HTML Caption ---
def build_aesthetic_caption(story: dict) -> str:
    """
    Constructs screenshot-style UI layout with Expandable Blockquote description
    """
    title = story.get("title", "Unknown Story")
    status = story.get("status", "Ongoing")
    platform = story.get("platform", "Pocket FM")
    genre = story.get("category", story.get("genre", "General")).capitalize()
    episodes = story.get("episodes", "1 / ∞")
    description = story.get("description", "No description available for this story.")

    # Status Emoji
    status_emoji = "🟢" if status.lower() in ["completed", "complete"] else "♨️"

    caption = (
        f"<b>{status_emoji}Story : {title}</b>\n"
        f"<b>🔰Status : {status.capitalize()}</b>\n"
        f"<b>🖥️Platform : {platform}</b>\n"
        f"<b>🧩Genre : {genre}</b>\n"
        f"<b>🎬Episodes : {episodes}</b>\n"
        f"═══════════════════\n"
        f"📝 <b>Story Description :-</b>\n"
        f"<blockquote expandable>{description}</blockquote>\n\n"
        f"⏱️ <i>This message will auto-delete in 5 minutes.</i>"
    )
    return caption


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


# --- 🔍 MAIN SEARCH & CATEGORY HANDLER ---
@Client.on_message(
    (filters.group | filters.private) & 
    filters.text & 
    ~filters.command(["start", "addstory", "request", "allstories", "filter", "categories", "top", "topcategories", "deletestory", "clearallstories", "stats"])
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
            f"📁 <b>Category Found:</b> <code>{clean_cat_query}</code>\n"
            f"📊 <b>Total Stories:</b> <code>{total_count}</code>\n\n"
            f"Select a story below to read:\n\n"
            f"⏱️ <i>This message will auto-delete in 2 minutes.</i>",
            reply_markup=markup,
            parse_mode=ParseMode.HTML
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
        caption = build_aesthetic_caption(story)
        
        button = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎧 Listen / Play Story", url=story["link"])],
            [InlineKeyboardButton("❌ Close", callback_data="close_all_st")]
        ])

        reply_msg = None
        try:
            reply_msg = await message.reply_photo(
                photo=story["photo"], 
                caption=caption, 
                reply_markup=button,
                parse_mode=ParseMode.HTML
            )
        except Exception:
            reply_msg = await message.reply_text(
                text=caption, 
                reply_markup=button, 
                disable_web_page_preview=True,
                parse_mode=ParseMode.HTML
            )

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
            f"❓ <b>Did you mean one of these stories?</b>\n\nSelect a story from below to read:\n\n⏱️ <i>This message will auto-delete in 2 minutes.</i>",
            reply_markup=markup,
            parse_mode=ParseMode.HTML
        )

        asyncio.create_task(delete_messages_later([suggestion_msg], 120))


# --- 🔥 TOP CATEGORIES COMMAND HANDLER ---
@Client.on_message(filters.command(["top", "topcategories"]) & (filters.group | filters.private))
async def show_top_categories_cmd(bot: Client, message: Message):
    status_msg = await message.reply_text("🔄 **Fetching top categories...**")

    try:
        top_cats = await get_top_categories_db(limit=6)

        if not top_cats:
            return await status_msg.edit_text("❌ **अभी डेटाबेस में कोई कैटेगरी उपलब्ध नहीं है या स्टोरीज में कैटेगरी नहीं जुड़ी है!**")

        buttons = []
        text_content = "🔥 <b><u>TOP & MOST POPULAR CATEGORIES</u></b>\n\n"

        row = []
        for idx, item in enumerate(top_cats, 1):
            cat_name = str(item["category"]).strip().capitalize()
            count = item["count"]
            
            text_content += f"<b>{idx}.</b> <code>{cat_name}</code> — <b>{count} Stories</b>\n"
            row.append(InlineKeyboardButton(f"🔥 {cat_name} ({count})", callback_data=f"pgcat#{cat_name}#1"))
            
            if len(row) == 2:
                buttons.append(row)
                row = []

        if row:
            buttons.append(row)

        buttons.append([InlineKeyboardButton("❌ Close", callback_data="close_all_st")])
        markup = InlineKeyboardMarkup(buttons)

        text_content += "\n👇 <b>Tap any category below to browse stories:</b>"

        await status_msg.edit_text(text_content, reply_markup=markup, parse_mode=ParseMode.HTML)

    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:**\n`{e}`")


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
        f"📁 <b>Category Found:</b> <code>{category_name}</code>\n"
        f"📊 <b>Total Stories:</b> <code>{total_count}</code>\n\n"
        f"Select a story below to read:\n\n"
        f"⏱️ <i>This message will auto-delete in 2 minutes.</i>",
        reply_markup=markup,
        parse_mode=ParseMode.HTML
    )
    await query.answer()


# --- Callback Query Handler for Opening Category Story ---
@Client.on_callback_query(filters.regex(r"^catstory#"))
async def open_category_story_cb(bot: Client, query: CallbackQuery):
    story_id = query.data.split("#", 1)[1]
    
    try:
        story = await stories_col.find_one({"_id": ObjectId(story_id)})
    except Exception:
        story = None

    if not story:
        return await query.answer("❌ Story no longer exists in database!", show_alert=True)

    try:
        await query.message.delete()
    except Exception:
        pass

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
        asyncio.create_task(delete_messages_later([reply_msg], 300))


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
        asyncio.create_task(delete_messages_later([reply_msg], 300))


# Callback for Close Button
@Client.on_callback_query(filters.regex("^close_all_st$"))
async def close_callback(bot: Client, query: CallbackQuery):
    try:
        await query.message.delete()
    except Exception:
        pass
