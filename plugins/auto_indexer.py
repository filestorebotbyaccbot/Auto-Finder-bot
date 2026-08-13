import re
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import MessageEntityType
from config import Config
from database.stories_db import add_story_db


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
    extracts the first line as Title, fetches Custom or Post Link, and indexes into MongoDB.
    """
    caption_or_text = message.caption or message.text
    
    if not caption_or_text:
        return
    
    # Extract ONLY the first line of text/caption as searchable title
    raw_title = caption_or_text.strip()
    clean_title = raw_title.split("\n")[0].strip()
    
    # Extract Photo File ID (or fallback placeholder if plain text post)
    photo_id = message.photo.file_id if message.photo else "https://telegra.ph/file/default_banner.jpg"
    
    # Extract Custom Link (or default channel post link)
    final_story_link = extract_custom_link(message)
        
    # Save into MongoDB
    await add_story_db(
        title=clean_title,
        photo=photo_id,
        link=final_story_link
    )
    
    # Send Notification to Log Channel
    if Config.LOG_CHANNEL:
        try:
            log_text = (
                f"⚡ **Auto-Indexed New Story!**\n\n"
                f"📌 **Title:** `{clean_title}`\n"
                f"📢 **Channel:** {message.chat.title}\n"
                f"🔗 **Saved Link:** {final_story_link}"
            )
            await bot.send_message(chat_id=Config.LOG_CHANNEL, text=log_text)
        except Exception as e:
            print(f"⚠️ Log alert error in auto-indexer: {e}")
