from pyrogram import Client, filters
from pyrogram.types import Message
from database.stories_db import get_all_titles

@Client.on_message(filters.command(["allstories", "filter"]))
async def list_stories_handler(bot: Client, message: Message):
    titles = await get_all_titles()
    
    if not titles:
        return await message.reply_text("📚 **No stories found in database!**")
    
    text = "📚 **Available Stories List:**\n"
    text += "*(Tap any story name below to copy it instantly)*\n\n"
    
    for idx, title in enumerate(titles, 1):
        text += f"{idx}. `{title}`\n"
        
    await message.reply_text(text)
