from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from config import Config
from database.stories_db import save_full_story_db

# Predefined Suggestions for quick typing
DEFAULT_CATEGORIES = ["Romance", "Horror", "Drama", "Action", "Sci-Fi", "Thriller", "General"]
DEFAULT_PLATFORMS = ["Pocket FM", "Kuku FM", "YouTube", "Telegram", "Spotify"]


@Client.on_message(filters.command(["addstory", "editstory"]) & filters.private)
async def interactive_add_or_edit_story_handler(bot: Client, message: Message):
    if message.from_user.id not in Config.ADMIN_IDS:
        return await message.reply_text("⛔ **You are not authorized to use this command!**")

    chat_id = message.chat.id

    # 📌 Step 1: Story Title
    title_ask = await message.chat.ask(
        "📝 <b>Step 1/8:</b> स्टोरी का <b>Title</b> भेजिए:\n\n<i>(नोट: केवल पहली लाइन सेव होगी)</i>",
        parse_mode=ParseMode.HTML
    )
    if not title_ask.text:
        return await message.reply_text("❌ Invalid Title. Process Cancelled!")
    
    # Save strictly only the first line of title
    story_title = title_ask.text.strip().split("\n")[0].strip()

    # 🖼️ Step 2: Photo / Banner
    photo_ask = await message.chat.ask(
        "🖼️ <b>Step 2/8:</b> स्टोरी का <b>Photo / Banner</b> भेजें (या Photo File ID / URL भी भेज सकते हैं):",
        parse_mode=ParseMode.HTML
    )
    story_photo = photo_ask.photo.file_id if photo_ask.photo else (photo_ask.text.strip() if photo_ask.text else "https://telegra.ph/file/default_banner.jpg")

    # 🔗 Step 3: Story Link
    link_ask = await message.chat.ask(
        "🔗 <b>Step 3/8:</b> स्टोरी का <b>Play / Read Link</b> भेजें:",
        parse_mode=ParseMode.HTML
    )
    if not link_ask.text:
        return await message.reply_text("❌ Invalid Link. Process Cancelled!")
    story_link = link_ask.text.strip()

    # 🔰 Step 4: Status (Ongoing / Completed)
    status_ask = await message.chat.ask(
        "🔰 <b>Step 4/8:</b> स्टोरी का <b>Status</b> लिखें:\n\n💡 <i>उदाहरण: <code>Ongoing</code> या <code>Completed</code></i>",
        parse_mode=ParseMode.HTML
    )
    raw_status = status_ask.text.strip() if status_ask.text else "Ongoing"
    story_status = "Completed" if "complete" in raw_status.lower() else "Ongoing"

    # 🖥️ Step 5: Platform
    plat_ask = await message.chat.ask(
        f"🖥️ <b>Step 5/8:</b> स्टोरी का <b>Platform Name</b> लिखें:\n\n💡 <i>Suggested: {', '.join(DEFAULT_PLATFORMS)}</i>",
        parse_mode=ParseMode.HTML
    )
    story_platform = plat_ask.text.strip() if plat_ask.text else "Pocket FM"

    # 🧩 Step 6: Category / Genre
    cat_ask = await message.chat.ask(
        f"🧩 <b>Step 6/8:</b> स्टोरी की <b>Category / Genre</b> लिखें:\n\n💡 <i>Suggested: {', '.join(DEFAULT_CATEGORIES)}</i>",
        parse_mode=ParseMode.HTML
    )
    story_genre = cat_ask.text.strip().capitalize() if cat_ask.text else "General"

    # 🎬 Step 7: Episodes Count
    ep_ask = await message.chat.ask(
        "🎬 <b>Step 7/8:</b> स्टोरी के <b>Episodes</b> की संख्या लिखें:\n\n💡 <i>उदाहरण: <code>415 / ∞</code> या <code>100 Complete</code></i>",
        parse_mode=ParseMode.HTML
    )
    story_episodes = ep_ask.text.strip() if ep_ask.text else "1 / ∞"

    # 📝 Step 8: Description
    desc_ask = await message.chat.ask(
        "📝 <b>Step 8/8:</b> स्टोरी का <b>Story Description</b> भेजें:",
        parse_mode=ParseMode.HTML
    )
    story_description = desc_ask.text.strip() if desc_ask.text else "No description provided."

    # 💾 Save Complete Metadata to MongoDB
    await save_full_story_db(
        title=story_title,
        photo=story_photo,
        link=story_link,
        status=story_status,
        platform=story_platform,
        genre=story_genre,
        episodes=story_episodes,
        description=story_description
    )

    # Preview Layout Setup
    status_emoji = "🟢" if story_status == "Completed" else "♨️"
    
    caption_preview = (
        f"✅ <b>Story Saved / Updated Successfully!</b>\n\n"
        f"<b>{status_emoji} Story : {story_title}</b>\n"
        f"<b>🔰 Status : {story_status}</b>\n"
        f"<b>🖥️ Platform : {story_platform}</b>\n"
        f"<b>🧩 Genre : {story_genre}</b>\n"
        f"<b>🎬 Episodes : {story_episodes}</b>\n"
        f"═══════════════════\n"
        f"📝 <b>Story Description :-</b>\n"
        f"<blockquote expandable>{story_description}</blockquote>"
    )

    preview_btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎧 Listen / Play Story", url=story_link)],
        [InlineKeyboardButton("❌ Close", callback_data="close_all_st")]
    ])

    try:
        await message.reply_photo(
            photo=story_photo,
            caption=caption_preview,
            reply_markup=preview_btn,
            parse_mode=ParseMode.HTML
        )
    except Exception:
        await message.reply_text(
            text=caption_preview,
            reply_markup=preview_btn,
            parse_mode=ParseMode.HTML
        )
