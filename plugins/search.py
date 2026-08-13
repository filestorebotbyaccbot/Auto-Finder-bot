from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database.stories_db import search_story_db

# Group and Private text search handler
@Client.on_message(
    (filters.group | filters.private) & 
    filters.text & 
    ~filters.command(["start", "addstory", "request", "allstories", "filter"])
)
async def search_handler(bot: Client, message: Message):
    user_query = message.text.strip()
    
    # Perform Search
    story, score = await search_story_db(user_query)
    
    if story and score >= 60:
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
            # Fallback if photo link fails
            await message.reply_text(
                text=caption,
                reply_markup=button,
                disable_web_page_preview=True
            )
    else:
        # Silent Mode: Remain completely silent if no database match found
        pass
