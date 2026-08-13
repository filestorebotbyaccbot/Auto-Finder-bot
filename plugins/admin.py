from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from database.stories_db import delete_single_story_db, delete_all_stories_db, get_all_titles

# --- 1. Delete Single Story Command (/deletestory <Story Name>) ---
@Client.on_message(filters.command("deletestory") & filters.private)
async def delete_single_story_handler(bot: Client, message: Message):
    if message.from_user.id not in Config.ADMIN_IDS:
        return await message.reply_text("⛔ **You are not authorized to use this command!**")

    if len(message.command) < 2:
        return await message.reply_text(
            "⚠️ **Usage:** `/deletestory <Story Name>`\n\n**Example:** `/deletestory Veer Gatha`"
        )

    story_name = message.text.split(None, 1)[1].strip()
    success = await delete_single_story_db(story_name)

    if success:
        await message.reply_text(f"✅ **Story `{story_name}` deleted successfully from Database!**")
    else:
        await message.reply_text(f"❌ **Story `{story_name}` not found in Database!**")


# --- 2. Clear All Stories Command (/clearallstories) ---
@Client.on_message(filters.command("clearallstories") & filters.private)
async def clear_all_stories_handler(bot: Client, message: Message):
    if message.from_user.id not in Config.ADMIN_IDS:
        return await message.reply_text("⛔ **You are not authorized to use this command!**")

    titles = await get_all_titles()
    total_count = len(titles)

    if total_count == 0:
        return await message.reply_text("📚 **Database is already empty!**")

    confirm_buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🚨 Yes, Delete All", callback_data="confirm_clear_all"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_clear_all")
        ]
    ])

    await message.reply_text(
        f"⚠️ **WARNING!**\n\n"
        f"Are you sure you want to delete **ALL {total_count} stories** from the database?\n"
        f"This action **cannot** be undone!",
        reply_markup=confirm_buttons
    )


# --- 3. Callback Handler for Clear All Confirmation ---
@Client.on_callback_query(filters.regex(r"^(confirm_clear_all|cancel_clear_all)$"))
async def clear_all_callback_handler(bot: Client, query: CallbackQuery):
    if query.from_user.id not in Config.ADMIN_IDS:
        return await query.answer("⛔ Admin access required!", show_alert=True)

    data = query.data

    if data == "confirm_clear_all":
        deleted_count = await delete_all_stories_db()
        await query.message.edit_text(
            f"🗑️ **Database Cleared!**\n\nSuccessfully deleted **{deleted_count} stories** from MongoDB."
        )
        await query.answer("Database Cleared Successfully!", show_alert=True)

    elif data == "cancel_clear_all":
        await query.message.edit_text("❌ **Operation Cancelled.** No stories were deleted.")
        await query.answer("Cancelled!")
