import re
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import MessageEntityType
from config import Config
from database.stories_db import add_story_with_category_db


def extract_category_from_text(text: str) -> str:
    """
    Extracts category from caption/text using 'Category: Name' format or '#Hashtag'.
    Defaults to 'General' if not found.
    """
    if not text:
        return "General"

    # 1. Check for 'Category: Romance' or 'Category : Drama'
    cat_match = re.search(r"(?i)category\s*:\s*([^\n]+)", text)
    if cat_match:
        return cat_match.group(1).strip().capitalize()

    # 2. Check for Hashtags (#Romance, #Horror)
    hashtags = re.findall(r"#(\w+)", text)
    if hashtags:
        ignore_tags = ["story", "channel", "post", "update", "read", "link"]
        valid_tags = [tag.capitalize() for tag in hashtags if tag.lower() not in ignore_tags]
        if valid_tags:
            return valid_tags[0]

    return "General"


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


@Client.on_message(filters.chat(Config.SOURCE_CHANNELS) & (filters.photo | filters.text))
async def auto_index_channel_posts(bot: Client, message: Message):
    """
    Automatically detects new posts in specified source channels,
    extracts first line as Title, Category, fetches Custom or Post Link, and indexes into MongoDB.
    """
    caption_or_text = message.caption or message.text
    
    if not caption_or_text:
        return
    
    # Strictly extract ONLY the first line as Title
    raw_title = caption_or_text.strip()
    clean_title = raw_title.split("\n")[0].strip()
    
    # Extract Category automatically
    story_category = extract_category_from_text(caption_or_text)

    # Extract Photo File ID (or fallback default banner)
    photo_id = message.photo.file_id if message.photo else "https://telegra.ph/file/default_banner.jpg"
    
    # Extract Custom Link or Default Channel Post Link
    final_story_link = extract_custom_link(message)
        
    # Save into MongoDB with Category
    await add_story_with_category_db(
        title=clean_title,
        photo=photo_id,
        link=final_story_link,
        category=story_category
    )
    
    # Send Notification to Log Channel
    if Config.LOG_CHANNEL:
        try:
            log_text = (
                f"⚡ **Auto-Indexed New Story!**\n\n"
                f"📌 **Title:** `{clean_title}`\n"
                f"🏷️ **Category:** `{story_category}`\n"
                f"📢 **Channel:** {message.chat.title}\n"
                f"🔗 **Saved Link:** {final_story_link}"
            )
            await bot.send_message(chat_id=Config.LOG_CHANNEL, text=log_text)
        except Exception as e:
            print(f"⚠️ Log alert error in auto-indexer: {e}")
