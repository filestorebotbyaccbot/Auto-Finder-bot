from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from database.stories_db import add_story_db

@Client.on_message(filters.command("addstory") & filters.private)
async def add_story_handler(bot: Client, message: Message):
    if message.from_user.id not in Config.ADMIN_IDS:
        return await message.reply_text("⛔ **You are not authorized to use this command!**")

    # Step 1: Ask Title
    title_ask = await message.chat.ask("📖 **Step 1/3:** Enter the **Story Title**:")
    if not title_ask.text:
        return await message.reply_text("❌ Invalid Title. Operation Cancelled!")
    
    # Save strictly only the first line of title
    story_title = title_ask.text.strip().split("\n")[0]

    # Step 2: Ask Photo / Banner
    photo_ask = await message.chat.ask("🖼️ **Step 2/3:** Send the **Photo File ID** or **Telegraph URL**:")
    story_photo = photo_ask.photo.file_id if photo_ask.photo else photo_ask.text.strip()

    # Step 3: Ask Link
    link_ask = await message.chat.ask("🔗 **Step 3/3:** Send the **Story Post / Channel Link**:")
    story_link = link_ask.text.strip()

    # Database Entry
    await add_story_db(title=story_title, photo=story_photo, link=story_link)

    preview_btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 Read Story", url=story_link)]
    ])

    await message.reply_photo(
        photo=story_photo,
        caption=f"✅ **Story Added Successfully!**\n\n📌 **Title:** `{story_title}`\n🔗 **Link:** {story_link}",
        reply_markup=preview_btn
    )
