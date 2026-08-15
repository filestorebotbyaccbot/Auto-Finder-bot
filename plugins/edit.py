import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from database.stories_db import stories_col, clean_text_for_search, update_story_field_db

# Store temporary edit state: {user_id: {"title": story_title}}
EDIT_CACHE = {}

# 1. Main Edit Command (/edit Story Name)
@Client.on_message(filters.command("edit") & filters.private)
async def edit_story_start(bot: Client, message: Message):
    if message.from_user.id not in Config.ADMIN_IDS:
        return await message.reply_text("⛔ <b>ᴀᴄᴄᴇꜱꜱ ᴅᴇɴɪᴇᴅ! ᴏɴʟʏ ᴀᴅᴍɪɴꜱ ᴄᴀɴ ᴜꜱᴇ ᴛʜɪꜱ.</b>")

    text = message.text.split(maxsplit=1)
    if len(text) < 2:
        return await message.reply_text(
            "⚠️ <b>ɪɴᴠᴀʟɪᴅ ꜰᴏʀᴍᴀᴛ!</b>\n\n"
            "<b>Usage:</b> <code>/edit Story Title</code>\n"
            "<b>Example:</b> <code>/edit Celebrity Se Pyaar</code>"
        )

    story_title = text[1].strip()
    clean_query = clean_text_for_search(story_title)

    # Check if story exists in Database
    story = await stories_col.find_one({"$or": [{"search_title": clean_query}, {"title": story_title}]})
    if not story:
        return await message.reply_text(f"❌ <b>Story '{story_title}' not found in Database!</b>")

    # Save title in Cache for Callback query
    EDIT_CACHE[message.from_user.id] = story["title"]

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🟢 Status", callback_data="ed_field_status"),
            InlineKeyboardButton("📺 Platform", callback_data="ed_field_platform")
        ],
        [
            InlineKeyboardButton("🧩 Genre", callback_data="ed_field_genre"),
            InlineKeyboardButton("🎬 Episodes", callback_data="ed_field_episodes")
        ],
        [
            InlineKeyboardButton("📝 Description", callback_data="ed_field_description")
        ],
        [
            InlineKeyboardButton("🔗 Link", callback_data="ed_field_link"),
            InlineKeyboardButton("🖼️ Cover Photo", callback_data="ed_field_photo")
        ],
        [
            InlineKeyboardButton("❌ Cancel", callback_data="ed_cancel")
        ]
    ])

    await message.reply_text(
        f"🛠️ <b>ᴇᴅɪᴛ ᴍᴇɴᴜ ꜰᴏʀ:</b> <code>{story['title']}</code>\n\n"
        f"👇 Select which detail you want to change:",
        reply_markup=buttons
    )


# 2. Callback Query Handler for Buttons
@Client.on_callback_query(filters.regex(r"^ed_"))
async def edit_callback_handler(bot: Client, query: CallbackQuery):
    user_id = query.from_user.id

    if user_id not in Config.ADMIN_IDS:
        return await query.answer("⛔ Access Denied!", show_alert=True)

    if query.data == "ed_cancel":
        EDIT_CACHE.pop(user_id, None)
        await query.message.delete()
        return await query.answer("Cancelled!")

    story_title = EDIT_CACHE.get(user_id)
    if not story_title:
        return await query.answer("⚠️ Session Expired! Please type /edit again.", show_alert=True)

    field = query.data.replace("ed_field_", "")
    field_labels = {
        "status": "Status (e.g. Completed / Ongoing)",
        "platform": "Platform (e.g. Pocket FM / Pratilipi FM)",
        "genre": "Genre / Category (e.g. Romantic / Action)",
        "episodes": "Episodes Count (e.g. 43 / 43)",
        "description": "Story Description",
        "link": "Listen / Play Link",
        "photo": "Cover Photo URL"
    }

    label = field_labels.get(field, field)
    await query.message.delete()

    # Ask user for input
    ask_msg = await bot.send_message(
        chat_id=query.message.chat.id,
        text=f"✏️ <b>Now send the new value for [{label}] for '{story_title}':</b>\n\n"
             f"⏱️ <i>Reply within 60 seconds...</i>"
    )

    try:
        # Listen for user reply
        response: Message = await bot.listen(chat_id=query.message.chat.id, user_id=user_id, timeout=60)
        new_val = response.text.strip() if response.text else ""

        if not new_val:
            return await ask_msg.edit_text("❌ <b>Invalid input! Text message required.</b>")

        # Update Database
        success = await update_story_field_db(story_title, field, new_val)
        if success:
            await ask_msg.edit_text(
                f"✅ <b>Successfully Updated!</b>\n\n"
                f"📖 <b>Story:</b> <code>{story_title}</code>\n"
                f"📌 <b>{field.capitalize()}:</b> <code>{new_val}</code>"
            )
        else:
            await ask_msg.edit_text("❌ <b>Failed to update database!</b>")

    except asyncio.TimeoutError:
        await ask_msg.edit_text("⏱️ <b>Timeout! You didn't send any message in 60 seconds.</b>")
