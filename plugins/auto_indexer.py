import re
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import MessageEntityType
from config import Config
from database.stories_db import save_full_story_db


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


@Client.on_message(filters.chat(Config.SOURCE_CHANNELS) & (filters.photo | filters.text))
async def auto_index_channel_posts(bot: Client, message: Message):
    """
    Automatically detects new posts in specified source channels,
    extracts Title, Status, Platform, Genre, Episodes, Description, 
    fetches Link, and indexes full metadata into MongoDB.
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
    await save_full_story_db(
        title=clean_title,
        photo=photo_id,
        link=final_story_link,
        status=status,
        platform=platform,
        genre=genre,
        episodes=episodes,
        description=description
    )
    
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
