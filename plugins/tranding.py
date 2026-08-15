import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from database.stories_db import rate_story_db, get_trending_stories_db, stories_col
from bson.objectid import ObjectId

# Helper function to truncate title
def format_clean_button_title(title: str, likes: int, max_len: int = 22) -> str:
    title = str(title).strip()
    if len(title) > max_len:
        return f"🔥 {title[:max_len-3]}... ({likes} 👍)"
    return f"🔥 {title} ({likes} 👍)"


# 1. /trending Command Handler
@Client.on_message(filters.command(["trending", "popular"]) & (filters.group | filters.private))
async def trending_cmd_handler(bot: Client, message: Message):
    wait_msg = await message.reply_text("<b>Pʟᴇᴀsᴇ Wᴀɪᴛ...</b>", parse_mode=ParseMode.HTML)
    
    trending_stories = await get_trending_stories_db(limit=8)

    try:
        await wait_msg.delete()
    except Exception:
        pass

    if not trending_stories:
        return await message.reply_text("❌ <b>अभी कोई ट्रेंडिंग स्टोरी उपलब्ध नहीं है!</b>")

    buttons = []
    text_content = "🔥 <b><u>TOP TRENDING & MOST LIKED STORIES</u></b>\n\n"

    for idx, story in enumerate(trending_stories, 1):
        title = story.get("title", "Untitled")
        likes_count = len(story.get("likes", []))
        text_content += f"<b>{idx}.</b> <code>{title}</code> — <b>{likes_count} 👍</b>\n"
        
        btn_text = format_clean_button_title(title, likes_count, max_len=20)
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"catstory#{story['_id']}")])

    buttons.append([InlineKeyboardButton("❌ Cʟᴏsᴇ", callback_data="close_all_st")])

    msg = await message.reply_text(
        text=text_content,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.HTML
    )

    if message.chat.type.value != "private":
        await asyncio.sleep(120)
        try:
            await msg.delete()
            await message.delete()
        except Exception:
            pass


# 2. Rating Callback Handler (👍 / 👎 Buttons Click Event)
@Client.on_callback_query(filters.regex(r"^rate#"))
async def rate_story_cb(bot: Client, query: CallbackQuery):
    _, rating_type, story_id = query.data.split("#")
    user_id = query.from_user.id

    success, total_likes = await rate_story_db(story_id, user_id, rating_type)

    if not success:
        return await query.answer("❌ Failed to update rating!", show_alert=True)

    # Fetch updated story to refresh buttons
    story = await stories_col.find_one({"_id": ObjectId(story_id)})
    likes_count = len(story.get("likes", []))
    dislikes_count = len(story.get("dislikes", []))

    # Updated Rating Buttons Logic
    updated_buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎧 Lɪsᴛᴇɴ / Pʟᴀʏ Sᴛᴏʀʏ", url=story["link"])],
        [
            InlineKeyboardButton(f"👍 {likes_count}", callback_data=f"rate#like#{story_id}"),
            InlineKeyboardButton(f"👎 {dislikes_count}", callback_data=f"rate#dislike#{story_id}")
        ],
        [InlineKeyboardButton("❌ Cʟᴏsᴇ", callback_data="close_all_st")]
    ])

    try:
        await query.message.edit_reply_markup(reply_markup=updated_buttons)
    except Exception:
        pass

    action_text = "Liked! 👍" if rating_type == "like" else "Disliked! 👎"
    await query.answer(f"Thanks! Story {action_text}")
