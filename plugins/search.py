import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.stories_db import search_story_db, stories_col, get_all_categories_db, get_stories_by_category_db

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
    # 🔍 1. CATEGORY SEARCH CHECK (-drama, #drama, /drama)
    # -------------------------------------------------------------
    clean_cat_query = user_query.lstrip("-/#").strip().capitalize()
    
    # DB से मौजूद सभी कैटेगरीज की लिस्ट निकालें
    all_categories = await get_all_categories_db()
    
    # अगर यूजर का इनपुट किसी कैटेगरी से मैच होता है (जैसे -drama या /drama)
    if clean_cat_query in [cat.capitalize() for cat in all_categories]:
        stories = await get_stories_by_category_db(clean_cat_query, limit=10)
        
        if not stories:
            msg = await message.reply_text(f"❌ `{clean_cat_query}` कैटेगरी में कोई स्टोरी नहीं मिली!")
            return asyncio.create_task(delete_messages_later([msg], 30))

        # 2x2 Buttons Layout Grid Creation
        buttons = []
        row = []
        for story in stories:
            btn_text = f"📖 {story['title'][:18]}"
            buttons.append([InlineKeyboardButton(btn_text, callback_data=f"catstory#{story['_id']}")])

        buttons.append([InlineKeyboardButton("❌ Close", callback_data="close_all_st")])
        markup = InlineKeyboardMarkup(buttons)

        cat_msg = await message.reply_text(
            f"📁 **Category Found:** `{clean_cat_query}`\n\nSelect a story below to read:\n\n⏱️ _This message will auto-delete in 2 minutes._",
            reply_markup=markup
        )

        to_delete = [cat_msg]
        if message.chat.type.value != "private":
            to_delete.append(message)  # Group me user text bhi delete karega

        return asyncio.create_task(delete_messages_later(to_delete, 120))


    # -------------------------------------------------------------
    # 🔎 2. REGULAR TITLE SEARCH & FUZZY MATCHING
    # -------------------------------------------------------------
    # Ignore slash commands for regular title searches
    if message.text.startswith("/"):
        return

    # Perform Word-by-Word & Fuzzy Search
    result = await search_story_db(user_query)
    
    # --- Case A: Exact / High Confidence Match ---
    if result["type"] == "exact":
        story = result["data"]
        category_name = story.get("category", "General")
        
        caption = (
            f"📖 **Story Found:** `{story['title']}`\n"
            f"🏷️ **Category:** `{category_name.capitalize()}`\n\n"
            f"✨ Tap the button below to play ▶️ the complete story:\n\n"
            f"⏱️ _This message will auto-delete in 5 minutes._"
        )
        
        # Direct Play Button
        button = InlineKeyboardMarkup([
            [InlineKeyboardButton("📖 Play Story", url=story["link"])]
        ])

        reply_msg = None
        try:
            reply_msg = await message.reply_photo(
                photo=story["photo"],
                caption=caption,
                reply_markup=button
            )
        except Exception:
            reply_msg = await message.reply_text(
                text=caption,
                reply_markup=button,
                disable_web_page_preview=True
            )

        # Non-blocking Auto-Delete Task (5 Minutes = 300s)
        to_delete = [reply_msg]
        if message.chat.type.value != "private":
            to_delete.append(message)

        asyncio.create_task(delete_messages_later(to_delete, 300))

    # --- Case B: Suggestions Found (Arranged in 2x2 Grid) ---
    elif result["type"] == "suggestions":
        suggestions = result["data"]
        
        # 2-2 Buttons Layout Grid Creation
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

    # --- Case C: Out of Database / No Matches ---
    else:
        # Silent Mode
        pass


# --- Callback Query Handler for Suggestion Buttons ---
@Client.on_callback_query(filters.regex(r"^sg#"))
async def suggestion_click_callback(bot: Client, query: CallbackQuery):
    selected_title = query.data.split("#", 1)[1]
    
    # Fetch from MongoDB by title
    story = await stories_col.find_one({"title": selected_title})
    
    if not story:
        return await query.answer("❌ Story no longer exists in database!", show_alert=True)

    # Delete suggestion box immediately on tap
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
    
    # Direct Play Button
    button = InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 Play Story", url=story["link"])]
    ])

    reply_msg = None
    try:
        reply_msg = await bot.send_photo(
            chat_id=query.message.chat.id,
            photo=story["photo"],
            caption=caption,
            reply_markup=button
        )
    except Exception:
        reply_msg = await bot.send_message(
            chat_id=query.message.chat.id,
            text=caption,
            reply_markup=button,
            disable_web_page_preview=True
        )

    # Background Auto-delete task (5 min = 300s)
    if reply_msg:
        asyncio.create_task(delete_messages_later([reply_msg], 300))


# Callback for Close Button
@Client.on_callback_query(filters.regex("^close_all_st$"))
async def close_callback(bot: Client, query: CallbackQuery):
    try:
        await query.message.delete()
    except Exception:
        pass
