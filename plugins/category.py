import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.stories_db import get_all_categories_db, get_stories_by_category_db, stories_col
from bson.objectid import ObjectId

# Auto Delete Helper
async def delete_msg_later(msg: Message, delay: int = 120):
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except Exception:
        pass


# /categories or /filter Command
@Client.on_message(filters.command(["categories", "filter"]) & (filters.group | filters.private))
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
        "📂 **<u>Select a Category to Browse Stories:</u>**\n\n⏱️ _This message will auto-delete in 2 minutes._",
        reply_markup=InlineKeyboardMarkup(buttons)
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
        f"📁 **Category:** `{selected_cat}`\n\nSelect a story below to play:",
        reply_markup=InlineKeyboardMarkup(buttons)
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

    caption = (
        f"📖 **Story Found:** `{story['title']}`\n"
        f"🏷️ **Category:** `{story.get('category', 'General')}`\n\n"
        f"✨ Tap below to play ▶️ the complete story:\n\n"
        f"⏱️ _This message will auto-delete in 5 minutes._"
    )
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
        "📂 **<u>Select a Category to Browse Stories:</u>**\n\n⏱️ _This message will auto-delete in 2 minutes._",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
