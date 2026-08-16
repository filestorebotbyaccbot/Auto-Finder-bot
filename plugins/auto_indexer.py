import re
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from pyrogram.enums import MessageEntityType, ParseMode
from config import Config
from database.stories_db import save_full_story_db, save_channel_msg_id


def parse_full_metadata(caption: str):
    """
    Extracts Title, Status, Platform, Genre, Episodes, and Description
    strictly from the channel post text/caption.
    """
    lines = [line.strip() for line in caption.split("\n") if line.strip()]
    
    # 1. Title (Always the First Line)
    raw_title = lines[0] if lines else "Untitled Story"

    # 2. Status (Ongoing vs Completed)
    status = "Ongoing"
    if re.search(r"(?i)status\s*:\s*(completed|complete)", caption) or "completed" in caption.lower():
        status = "Completed"

    # 3. Platform (Pocket FM / KuKu FM etc.)
    platform = "Pocket FM"
    plat_match = re.search(r"(?i)platform\s*:\s*([^\n]+)", caption)
    if plat_match:
        platform = plat_match.group(1).strip()

    # 4. Genre / Category
    genre = "General"
    genre_match = re.search(r"(?i)(genre|category)\s*:\s*([^\n]+)", caption)
    if genre_match:
        genre = genre_match.group(2).strip().capitalize()
    else:
        # Fallback to Hashtags if Genre: line is missing
        hashtags = re.findall(r"#(\w+)", caption)
        if hashtags:
            ignore_tags = ["story", "channel", "post", "update", "read", "link"]
            valid_tags = [tag.capitalize() for tag in hashtags if tag.lower() not in ignore_tags]
            if valid_tags:
                genre = valid_tags[0]

    # 5. Episodes
    episodes = "1 / ∞"
    ep_match = re.search(r"(?i)episodes\s*:\s*([^\n]+)", caption)
    if ep_match:
        episodes = ep_match.group(1).strip()

    # 6. Story Description
    description = "No description available."
    if "Story Description" in caption:
        # Splits after 'Story Description :-' or 'Story Description:'
        desc_part = re.split(r"(?i)story\s*description\s*[:\-]*", caption, maxsplit=1)
        if len(desc_part) > 1:
            description = desc_part[1].strip()
    elif len(lines) > 2:
        # If no explicit header, treat remaining lines after metadata as description
        description = "\n".join(lines[2:]).strip()

    return raw_title, status, platform, genre, episodes, description


def extract_custom_link(message: Message) -> str:
    """
    Extracts custom URL from post entities, buttons, or plain text.
    Falls back to official Telegram Channel post link if no custom URL found.
    """
    text = message.caption or message.text or ""
    entities = message.caption_entities or message.entities or []

    # 1. Check for Hyperlinks (e.g., [Read Story](https://customurl.com))
    for entity in entities:
        if entity.type == MessageEntityType.TEXT_LINK:
            return entity.url
        elif entity.type == MessageEntityType.URL:
            # Extract plain URL marked as entity
            return text[entity.offset : entity.offset + entity.length]

    # 2. Check for Inline Keyboard Button URLs
    if message.reply_markup and message.reply_markup.inline_keyboard:
        for row in message.reply_markup.inline_keyboard:
            for button in row:
                if button.url:
                    return button.url

    # 3. Regex Fallback: Search for any http/https link in text/caption
    urls = re.findall(r'(https?://[^\s]+)', text)
    if urls:
        return urls[0]

    # 4. Default Fallback: Standard Telegram Post Link
    if message.chat.username:
        return f"https://t.me/{message.chat.username}/{message.id}"
    else:
        clean_chat_id = str(message.chat.id).replace("-100", "")
        return f"https://t.me/c/{clean_chat_id}/{message.id}"


# --- 📢 UPDATE CHANNEL SYNC HELPERS ---

def build_channel_caption(story: dict) -> str:
    """चैनल पोस्ट के लिए एस्थेटिक कैप्श्न तैयार करता है"""
    title = story.get("title", "Unknown Story")
    status = story.get("status", "Ongoing")
    platform = story.get("platform", "Pocket FM")
    genre = story.get("category", story.get("genre", "General")).capitalize()
    episodes = story.get("episodes", "1 / ∞")
    description = story.get("description", "No description available.")

    status_emoji = "🟢" if str(status).lower() in ["completed", "complete"] else "♨️"

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
        f"🔔 <i>Stay tuned for daily updates!</i>"
    )
    return caption


def build_channel_buttons(story: dict) -> InlineKeyboardMarkup:
    """चैनल पोस्ट के लिए बटन्स (Likes, Dislikes & Favorite)"""
    likes_count = len(story.get("likes", [])) if isinstance(story.get("likes"), list) else story.get("likes", 0)
    dislikes_count = len(story.get("dislikes", [])) if isinstance(story.get("dislikes"), list) else story.get("dislikes", 0)
    story_id = str(story["_id"])

    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎧 Lɪsᴛᴇɴ / Pʟᴀʏ Sᴛᴏʀʏ", url=story["link"])],
        [
            InlineKeyboardButton(f"👍 {likes_count}", callback_data=f"rate#like#{story_id}"),
            InlineKeyboardButton(f"👎 {dislikes_count}", callback_data=f"rate#dislike#{story_id}")
        ],
        [InlineKeyboardButton("⭐ Aᴅᴅ Fᴀᴠᴏʀɪᴛᴇ", callback_data=f"fav#toggle#{story_id}")]
    ])


async def broadcast_or_sync_to_channel(bot: Client, story: dict):
    """अपडेट चैनल में नयी ऑटो-इंडेक्स स्टोरी पोस्ट करता है या एडिट करता है"""
    channel_id = getattr(Config, "UPDATE_CHANNEL", None)
    if not channel_id:
        return

    caption = build_channel_caption(story)
    buttons = build_channel_buttons(story)
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
            print(f"⚠️ [Auto-Index Channel Sync Edit Error]: {e}")

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
        print(f"❌ [Auto-Index Channel Post Error]: {e}")


# --- Main Event Handler ---

@Client.on_message(filters.chat(Config.SOURCE_CHANNELS) & (filters.photo | filters.text))
async def auto_index_channel_posts(bot: Client, message: Message):
    """
    Automatically detects new posts in specified source channels,
    extracts Title, Status, Platform, Genre, Episodes, Description, 
    fetches Link, and indexes full metadata into MongoDB.
    Also triggers broadcast to UPDATE_CHANNEL.
    """
    caption_or_text = message.caption or message.text
    
    if not caption_or_text:
        return
    
    # Extract Full Metadata from Caption
    clean_title, status, platform, genre, episodes, description = parse_full_metadata(caption_or_text)

    # Extract Photo File ID (or fallback default banner)
    photo_id = message.photo.file_id if message.photo else "https://telegra.ph/file/default_banner.jpg"
    
    # Extract Custom Link or Default Channel Post Link
    final_story_link = extract_custom_link(message)
        
    # Save into MongoDB with Full Metadata
    saved_story = await save_full_story_db(
        title=clean_title,
        photo=photo_id,
        link=final_story_link,
        status=status,
        platform=platform,
        genre=genre,
        episodes=episodes,
        description=description
    )
    
    # 🚀 Post / Update on Update Channel Automatically
    if saved_story:
        asyncio.create_task(broadcast_or_sync_to_channel(bot, saved_story))

    # Send Notification to Log Channel
    if Config.LOG_CHANNEL:
        try:
            log_text = (
                f"⚡ **Auto-Indexed New Story!**\n\n"
                f"📌 **Title:** `{clean_title}`\n"
                f"🔰 **Status:** `{status}`\n"
                f"🖥️ **Platform:** `{platform}`\n"
                f"🧩 **Genre:** `{genre}`\n"
                f"🎬 **Episodes:** `{episodes}`\n"
                f"📢 **Channel:** {message.chat.title}\n"
                f"🔗 **Saved Link:** {final_story_link}"
            )
            await bot.send_message(chat_id=Config.LOG_CHANNEL, text=log_text)
        except Exception as e:
            print(f"⚠️ Log alert error in auto-indexer: {e}")


