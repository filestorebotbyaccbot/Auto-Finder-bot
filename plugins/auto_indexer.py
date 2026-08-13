from pyrogram import Client, filters
from pyrogram.types import Message
from config import Config
from database.stories_db import add_story_db

@Client.on_message(filters.chat(Config.SOURCE_CHANNELS) & (filters.photo | filters.text))
async def auto_index_channel_posts(bot: Client, message: Message):
    """
    Automatically detects new posts in specified source channels,
    extracts the first line as Title, and indexes into MongoDB.
    """
    caption_or_text = message.caption or message.text
    
    if not caption_or_text:
        return
    
    # Extract ONLY the first line of text/caption as searchable title
    raw_title = caption_or_text.strip()
    clean_title = raw_title.split("\n")[0].strip()
    
    # Extract Photo File ID (or fallback placeholder if plain text post)
    photo_id = message.photo.file_id if message.photo else "https://telegra.ph/file/default_banner.jpg"
    
    # Construct Direct Post Link
    # If channel has username -> https://t.me/username/123
    # If channel is private -> https://t.me/c/123456789/123
    if message.chat.username:
        post_link = f"https://t.me/{message.chat.username}/{message.id}"
    else:
        clean_chat_id = str(message.chat.id).replace("-100", "")
        post_link = f"https://t.me/c/{clean_chat_id}/{message.id}"
        
    # Save into MongoDB
    await add_story_db(
        title=clean_title,
        photo=photo_id,
        link=post_link
    )
    
    # Optional Notification to Log Channel
    if Config.LOG_CHANNEL:
        try:
            log_text = (
                f"⚡ **Auto-Indexed New Story!**\n\n"
                f"📌 **Title:** `{clean_title}`\n"
                f"📢 **Channel:** {message.chat.title}\n"
                f"🔗 **Post Link:** {post_link}"
            )
            await bot.send_message(chat_id=Config.LOG_CHANNEL, text=log_text)
        except Exception as e:
            print(f"⚠️ Log alert error in auto-indexer: {e}")
