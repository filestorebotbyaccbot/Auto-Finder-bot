import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from database.stories_db import *
from bson.objectid import ObjectId

# Auto Delete Helper
async def delete_msg_later(msg: Message, delay: int = 120):
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


# /categories or /filter Command
@Client.on_message(filters.command(["categories", "filters"]) & (filters.group | filters.private))
async def show_categories_cmd(bot: Client, message: Message):
    categories = await get_all_categories_db()

    if not categories:
        msg = await message.reply_text("❌ **अभी डेटाबेस में कोई कैटेगरी उपलब्ध नहीं है!**")
        return asyncio.create_task(delete_msg_later(msg, 30))

    # 2x2 Grid Buttons Layout
    buttons = []
    row = []
    for cat in categories:
        row.append(InlineKeyboardButton(f"📁 {cat}", callback_data=f"cat#{cat}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton("❌ Close", callback_data="close_all_st")])

    cat_msg = await message.reply_text(
        "📂 <b><u>Select a Category to Browse Stories:</u></b>\n\n⏱️ <i>This message will auto-delete in 2 minutes.</i>",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.HTML
    )

    asyncio.create_task(delete_msg_later(cat_msg, 120))


# Callback for Category Selection
@Client.on_callback_query(filters.regex(r"^cat#"))
async def category_select_cb(bot: Client, query: CallbackQuery):
    selected_cat = query.data.split("#", 1)[1]
    stories = await get_stories_by_category_db(selected_cat, limit=10)

    if not stories:
        return await query.answer(f"❌ '{selected_cat}' में कोई स्टोरी नहीं मिली!", show_alert=True)

    await query.answer()

    # Create Buttons for Stories in Selected Category
    buttons = []
    for story in stories:
        btn_text = f"📖 {story['title'][:22]}"
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"catstory#{story['_id']}")])

    buttons.append([InlineKeyboardButton("🔙 Back to Categories", callback_data="back_to_cats")])
    buttons.append([InlineKeyboardButton("❌ Close", callback_data="close_all_st")])

    await query.message.edit_text(
        f"📁 <b>Category:</b> <code>{selected_cat}</code>\n\nSelect a story below to play:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.HTML
    )


# Callback for Opening Story from Category List
@Client.on_callback_query(filters.regex(r"^catstory#"))
async def open_category_story_cb(bot: Client, query: CallbackQuery):
    story_id = query.data.split("#", 1)[1]
    
    try:
        story = await stories_col.find_one({"_id": ObjectId(story_id)})
    except Exception:
        story = None

    if not story:
        return await query.answer("❌ Story no longer exists!", show_alert=True)

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
        asyncio.create_task(delete_msg_later(reply_msg, 300))


# Callback to Go Back to Main Category List
@Client.on_callback_query(filters.regex("^back_to_cats$"))
async def back_to_categories_cb(bot: Client, query: CallbackQuery):
    categories = await get_all_categories_db()
    
    buttons = []
    row = []
    for cat in categories:
        row.append(InlineKeyboardButton(f"📁 {cat}", callback_data=f"cat#{cat}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton("❌ Close", callback_data="close_all_st")])

    await query.message.edit_text(
        "📂 <b><u>Select a Category to Browse Stories:</u></b>\n\n⏱️ <i>This message will auto-delete in 2 minutes.</i>",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.HTML
    )
