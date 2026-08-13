import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.stories_db import search_story_db, stories_col

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
    ~filters.command(["start", "addstory", "request", "allstories", "filter", "deletestory", "clearallstories"])
)
async def search_handler(bot: Client, message: Message):
    # Ignore slash commands completely
    if message.text.startswith("/"):
        return

    user_query = message.text.strip()
    if len(user_query) < 2:
        return

    # Perform Word-by-Word & Fuzzy Search
    result = await search_story_db(user_query)
    
    # --- Case 1: Exact / High Confidence Match ---
    if result["type"] == "exact":
        story = result["data"]
        
        caption = (
            f"📖 **Story Found:** `{story['title']}`\n\n"
            f"✨ Tap the button below to play ▶️ the complete story:\n\n"
            f"⏱️ _This message will auto-delete in 5 minutes._"
        )
        
        # Direct Play Button (No PM Redirect)
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
            to_delete.append(message)  # Delete user's search message in group too

        asyncio.create_task(delete_messages_later(to_delete, 300))

    # --- Case 2: Suggestions Found (Arranged in 2x2 Grid) ---
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

        # Non-blocking Auto-Delete Task (2 Minutes = 120s)
        asyncio.create_task(delete_messages_later([suggestion_msg], 120))

    # --- Case 3: Out of Database / No Matches ---
    else:
        # Silent Mode: Remain completely silent if no match or suggestions found in DB
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

    caption = (
        f"📖 **Story Found:** `{story['title']}`\n\n"
        f"✨ Tap below to play ▶️ the complete story:\n\n"
        f"⏱️ _This message will auto-delete in 5 minutes._"
    )
    
    # Direct Play Button (No PM Redirect)
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
