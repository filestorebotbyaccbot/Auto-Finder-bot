from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.stories_db import search_story_db, stories_col

@Client.on_message(
    (filters.group | filters.private) & 
    filters.text & 
    ~filters.command(["start", "addstory", "request", "allstories", "filter", "deletestory", "clearallstories"])
)
async def search_handler(bot: Client, message: Message):
    user_query = message.text.strip()
    
    # Perform Search
    result = await search_story_db(user_query)
    
    # --- Case 1: Exact / High Confidence Match ---
    if result["type"] == "exact":
        story = result["data"]
        caption = f"📖 **Story Found:** `{story['title']}`\n\n✨ Tap the button below to play ▶️ the complete story:"
        button = InlineKeyboardMarkup([
            [InlineKeyboardButton("📖 Play Story", url=story["link"])]
        ])
        
        try:
            await message.reply_photo(
                photo=story["photo"],
                caption=caption,
                reply_markup=button
            )
        except Exception:
            await message.reply_text(
                text=caption,
                reply_markup=button,
                disable_web_page_preview=True
            )

    # --- Case 2: Suggestions Found (Up to 4 Buttons) ---
    elif result["type"] == "suggestions":
        suggestions = result["data"]
        
        buttons = []
        for title in suggestions:
            # Prefix 'sg#' for suggestion callback handling
            buttons.append([InlineKeyboardButton(f"📖 {title}", callback_data=f"sg#{title[:25]}")])
            
        markup = InlineKeyboardMarkup(buttons)
        
        await message.reply_text(
            f"❓ **Did you mean one of these stories?**\n\nSelect a story from below to read:",
            reply_markup=markup
        )

    # --- Case 3: Out of Database / No Matches ---
    else:
        # Silent Mode: Remain completely silent if no match or suggestions found
        pass


# --- Callback Query Handler for Suggestion Buttons ---
@Client.on_callback_query(filters.regex(r"^sg#"))
async def suggestion_click_callback(bot: Client, query: CallbackQuery):
    selected_title = query.data.split("#", 1)[1]
    
    # Fetch from MongoDB by title
    story = await stories_col.find_one({"title": selected_title})
    
    if not story:
        return await query.answer("❌ Story no longer exists in database!", show_alert=True)
    
    caption = f"📖 **Story Found:** `{story['title']}`\n\n✨ Tap the button below to play ▶️ the complete story:"
    button = InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 Play Story", url=story["link"])]
    ])
    
    try:
        await query.message.reply_photo(
            photo=story["photo"],
            caption=caption,
            reply_markup=button
        )
        await query.message.delete()  # Remove the suggestion menu after click
    except Exception:
        await query.message.edit_text(
            text=caption,
            reply_markup=button,
            disable_web_page_preview=True
        )
