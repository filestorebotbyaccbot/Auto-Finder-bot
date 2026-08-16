import asyncio
import re
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from pyrogram.enums import ParseMode
from config import Config
from database.stories_db import save_full_story_db, save_channel_msg_id

# Predefined Suggestions for quick typing
DEFAULT_CATEGORIES = ["Romance", "Horror", "Drama", "Action", "Sci-Fi", "Thriller", "General"]
DEFAULT_PLATFORMS = ["Pocket FM", "Kuku FM", "YouTube", "Telegram", "Spotify"]


# --- Cancel Inline Keyboard Helper ---
def get_cancel_btn():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel Process", callback_data="cancel_wizard")]
    ])


# --- 📢 UPDATE CHANNEL HELPERS ---

def build_channel_caption(story: dict, bot_username: str = None) -> str:
    """चैनल पोस्ट के लिए एस्थेटिक कैप्श्न तैयार करता है (Powered By Clickable Link के साथ)"""
    title = story.get("title", "Unknown Story")
    status = story.get("status", "Ongoing")
    platform = story.get("platform", "Pocket FM")
    genre = story.get("category", story.get("genre", "General")).capitalize()
    episodes = story.get("episodes", "1 / ∞")
    description = story.get("description", "No description available.")

    status_emoji = "🟢" if str(status).lower() in ["completed", "complete"] else "♨️"
    powered_by_text = f"⚡ <b>Powered By <a href='https://t.me/{bot_username}'>@{bot_username}</a></b>" if bot_username else ""

    caption = (
        f"<b>📢 NEW STORY / UPDATE!</b>\n\n"
        f"<b>{status_emoji}Story : {title}</b>\n"
        f"<b>🔰Status : {str(status).capitalize()}</b>\n"
        f"<b>🖥️Platform : {platform}</b>\n"
        f"<b>🧩Genre : {genre}</b>\n"
        f"<b>🎬Episodes : {episodes}</b>\n"
        f"═══════════════════\n"
        f"📝 <b>Story Description :-</b>\n"
        f"<blockquote expandable>{description}</blockquote>\n\n"
        f"{powered_by_text}"
    )
    return caption


def build_channel_buttons(story: dict, bot_username: str = None) -> InlineKeyboardMarkup:
    """चैनल/ग्रुप पोस्ट के लिए बटन्स (Likes, Dislikes, Fav & Powered By Bot)"""
    likes_count = len(story.get("likes", [])) if isinstance(story.get("likes"), list) else story.get("likes", 0)
    dislikes_count = len(story.get("dislikes", [])) if isinstance(story.get("dislikes"), list) else story.get("dislikes", 0)
    story_id = str(story["_id"])

    keyboard = [
        [InlineKeyboardButton("🎧 Lɪsᴛᴇɴ / Pʟᴀʏ Sᴛᴏʀʏ", url=story["link"])],
        [
            InlineKeyboardButton(f"👍 {likes_count}", callback_data=f"rate#like#{story_id}"),
            InlineKeyboardButton(f"👎 {dislikes_count}", callback_data=f"rate#dislike#{story_id}")
        ],
        [InlineKeyboardButton("⭐ Aᴅᴅ Fᴀᴠᴏʀɪᴛᴇ", callback_data=f"fav#toggle#{story_id}")]
    ]

    # 🚀 Dynamic Powered By Button
    if bot_username:
        keyboard.append([
            InlineKeyboardButton(
                f"⚡ Pᴏᴡᴇʀᴇᴅ Bʏ @{bot_username}", 
                url=f"https://t.me/{bot_username}"
            )
        ])

    return InlineKeyboardMarkup(keyboard)


async def broadcast_or_sync_to_channel(bot: Client, story: dict):
    """अपडेट चैनल में नयी स्टोरी पोस्ट करता है या पुरानी को ऑटो-अपडेट करता है"""
    channel_id = getattr(Config, "UPDATE_CHANNEL", None)
    if not channel_id:
        return

    # बॉट का यूज़रनेम डायनामिकली प्राप्त करें
    bot_username = bot.me.username if bot.me else (await bot.get_me()).username

    caption = build_channel_caption(story, bot_username=bot_username)
    buttons = build_channel_buttons(story, bot_username=bot_username)
    msg_id = story.get("channel_message_id")

    # 1. अगर पहले से चैनल में पोस्टेड है तो EDIT करें
    if msg_id:
        try:
            if story.get("photo"):
                await bot.edit_message_media(
                    chat_id=channel_id,
                    message_id=msg_id,
                    media=InputMediaPhoto(media=story["photo"], caption=caption, parse_mode=ParseMode.HTML),
                    reply_markup=buttons
                )
            else:
                await bot.edit_message_text(
                    chat_id=channel_id,
                    message_id=msg_id,
                    text=caption,
                    reply_markup=buttons,
                    disable_web_page_preview=True,
                    parse_mode=ParseMode.HTML
                )
            return
        except Exception as e:
            print(f"⚠️ [Channel Sync Edit Error]: {e}")

    # 2. अगर पोस्टेड नहीं है तो NEW POST करें
    sent_msg = None
    try:
        if story.get("photo"):
            sent_msg = await bot.send_photo(
                chat_id=channel_id,
                photo=story["photo"],
                caption=caption,
                reply_markup=buttons,
                parse_mode=ParseMode.HTML
            )
        else:
            sent_msg = await bot.send_message(
                chat_id=channel_id,
                text=caption,
                reply_markup=buttons,
                disable_web_page_preview=True,
                parse_mode=ParseMode.HTML
            )

        if sent_msg:
            await save_channel_msg_id(str(story["_id"]), sent_msg.id)
    except Exception as e:
        print(f"❌ [Channel Post Error]: {e}")


# --- Main Command Handler ---

@Client.on_message(filters.command(["addstory", "editstory"]) & filters.private)
async def interactive_add_or_edit_story_handler(bot: Client, message: Message):
    if message.from_user.id not in Config.ADMIN_IDS:
        return await message.reply_text("⛔ **You are not authorized to use this command!**")

    # 📌 Step 1: Story Title
    title_ask = await message.chat.ask(
        "📝 <b>Step 1/8:</b> स्टोरी का <b>Title</b> भेजिए:\n\n"
        "<i>(नोट: केवल पहली लाइन सेव होगी | Cancel करने के लिए /cancel लिखें)</i>",
        reply_markup=get_cancel_btn(),
        parse_mode=ParseMode.HTML
    )
    if not title_ask.text or title_ask.text.strip().lower() == "/cancel":
        return await message.reply_text("❌ **Add Story Process Cancelled!**")
    
    story_title = title_ask.text.strip().split("\n")[0].strip()
    if len(story_title) < 2:
        return await message.reply_text("❌ **Invalid Title Length! Process Cancelled.**")


    # 🖼️ Step 2: Photo / Banner
    photo_ask = await message.chat.ask(
        "🖼️ <b>Step 2/8:</b> स्टोरी का <b>Photo / Banner</b> भेजें (Photo upload करें या Photo URL/File ID भेजें):",
        reply_markup=get_cancel_btn(),
        parse_mode=ParseMode.HTML
    )
    if photo_ask.text and photo_ask.text.strip().lower() == "/cancel":
        return await message.reply_text("❌ **Add Story Process Cancelled!**")

    story_photo = (
        photo_ask.photo.file_id if photo_ask.photo 
        else (photo_ask.text.strip() if photo_ask.text else "https://telegra.ph/file/default_banner.jpg")
    )


    # 🔗 Step 3: Story Link
    link_ask = await message.chat.ask(
        "🔗 <b>Step 3/8:</b> स्टोरी का <b>Play / Read Link</b> (URL) भेजें:",
        reply_markup=get_cancel_btn(),
        parse_mode=ParseMode.HTML
    )
    if not link_ask.text or link_ask.text.strip().lower() == "/cancel":
        return await message.reply_text("❌ **Add Story Process Cancelled!**")

    story_link = link_ask.text.strip()
    if not story_link.startswith(("http://", "https://")):
        return await message.reply_text("❌ **Invalid Link format! http:// या https:// Link भेजें. Process Cancelled.**")


    # 🔰 Step 4: Status (Ongoing / Completed)
    status_ask = await message.chat.ask(
        "🔰 <b>Step 4/8:</b> स्टोरी का <b>Status</b> लिखें:\n\n💡 <i>उदाहरण: <code>Ongoing</code> या <code>Completed</code></i>",
        reply_markup=get_cancel_btn(),
        parse_mode=ParseMode.HTML
    )
    if status_ask.text and status_ask.text.strip().lower() == "/cancel":
        return await message.reply_text("❌ **Add Story Process Cancelled!**")

    raw_status = status_ask.text.strip() if status_ask.text else "Ongoing"
    story_status = "Completed" if "complete" in raw_status.lower() else "Ongoing"


    # 🖥️ Step 5: Platform
    plat_ask = await message.chat.ask(
        f"🖥️ <b>Step 5/8:</b> स्टोरी का <b>Platform Name</b> लिखें:\n\n💡 <i>Suggested: {', '.join(DEFAULT_PLATFORMS)}</i>",
        reply_markup=get_cancel_btn(),
        parse_mode=ParseMode.HTML
    )
    if plat_ask.text and plat_ask.text.strip().lower() == "/cancel":
        return await message.reply_text("❌ **Add Story Process Cancelled!**")

    story_platform = plat_ask.text.strip() if plat_ask.text else "Pocket FM"


    # 🧩 Step 6: Category / Genre
    cat_ask = await message.chat.ask(
        f"🧩 <b>Step 6/8:</b> स्टोरी की <b>Category / Genre</b> लिखें:\n\n💡 <i>Suggested: {', '.join(DEFAULT_CATEGORIES)}</i>",
        reply_markup=get_cancel_btn(),
        parse_mode=ParseMode.HTML
    )
    if cat_ask.text and cat_ask.text.strip().lower() == "/cancel":
        return await message.reply_text("❌ **Add Story Process Cancelled!**")

    story_genre = cat_ask.text.strip().capitalize() if cat_ask.text else "General"


    # 🎬 Step 7: Episodes Count
    ep_ask = await message.chat.ask(
        "🎬 <b>Step 7/8:</b> स्टोरी के <b>Episodes</b> की संख्या लिखें:\n\n💡 <i>उदाहरण: <code>415 / ∞</code> या <code>100 Complete</code></i>",
        reply_markup=get_cancel_btn(),
        parse_mode=ParseMode.HTML
    )
    if ep_ask.text and ep_ask.text.strip().lower() == "/cancel":
        return await message.reply_text("❌ **Add Story Process Cancelled!**")

    story_episodes = ep_ask.text.strip() if ep_ask.text else "1 / ∞"


    # 📝 Step 8: Description
    desc_ask = await message.chat.ask(
        "📝 <b>Step 8/8:</b> स्टोरी का <b>Story Description</b> भेजें:",
        reply_markup=get_cancel_btn(),
        parse_mode=ParseMode.HTML
    )
    if desc_ask.text and desc_ask.text.strip().lower() == "/cancel":
        return await message.reply_text("❌ **Add Story Process Cancelled!**")

    story_description = desc_ask.text.strip() if desc_ask.text else "No description provided."


    # 💾 Save / Update Complete Metadata in MongoDB
    saved_story = await save_full_story_db(
        title=story_title,
        photo=story_photo,
        link=story_link,
        status=story_status,
        platform=story_platform,
        genre=story_genre,
        episodes=story_episodes,
        description=story_description
    )

    # 🚀 Trigger Update Channel Auto-Post / Sync
    if saved_story:
        asyncio.create_task(broadcast_or_sync_to_channel(bot, saved_story))

    # Bot Username for Preview
    bot_username = bot.me.username if bot.me else (await bot.get_me()).username

    status_emoji = "🟢" if story_status == "Completed" else "♨️"
    powered_by_text = f"⚡ <b>Powered By <a href='https://t.me/{bot_username}'>@{bot_username}</a></b>"
    
    caption_preview = (
        f"✅ <b>Story Saved / Updated Successfully!</b>\n\n"
        f"<b>{status_emoji} Story : {story_title}</b>\n"
        f"<b>🔰 Status : {story_status}</b>\n"
        f"<b>🖥️ Platform : {story_platform}</b>\n"
        f"<b>🧩 Genre : {story_genre}</b>\n"
        f"<b>🎬 Episodes : {story_episodes}</b>\n"
        f"═══════════════════\n"
        f"📝 <b>Story Description :-</b>\n"
        f"<blockquote expandable>{story_description}</blockquote>\n\n"
        f"{powered_by_text}"
    )

    preview_btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎧 Listen / Play Story", url=story_link)],
        [InlineKeyboardButton(f"⚡ Powered By @{bot_username}", url=f"https://t.me/{bot_username}")],
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


# --- Callback Handler for Cancel Button ---
@Client.on_callback_query(filters.regex("^cancel_wizard$"))
async def cancel_wizard_cb(bot: Client, query: CallbackQuery):
    try:
        await query.message.delete()
    except Exception:
        pass
    await query.message.reply_text("❌ **Story Addition Process Cancelled!**")
