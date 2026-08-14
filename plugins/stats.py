import traceback
from pyrogram import Client, filters
from pyrogram.types import Message
from config import Config
from database.stories_db import (
    get_total_users_count, 
    get_total_stories_count, 
    get_total_requests_count
)

@Client.on_message(filters.command("stats") & filters.private)
async def stats_command_handler(bot: Client, message: Message):
    user_id = message.from_user.id
    
    # Check Admin Access using Config.ADMIN_IDS
    if user_id not in Config.ADMIN_IDS:
        return await message.reply_text(
            f"⛔ **Access Denied!**\n\n"
            f"Your Telegram ID (`{user_id}`) is not authorized to use this command."
        )

    status_msg = await message.reply_text("📊 **Fetching database statistics...**")

    try:
        # DB Helper functions se live metrics fetch karna
        total_users = await get_total_users_count()
        total_stories = await get_total_stories_count()
        pending_requests = await get_total_requests_count()

        stats_text = (
            f"📊 **<u>BOT DATABASE STATISTICS</u>**\n\n"
            f"👤 **Total Users:** `{total_users}`\n"
            f"📚 **Total Stories:** `{total_stories}`\n"
            f"📝 **Pending Requests:** `{pending_requests}`\n\n"
            f"⚡ **System Status:** `Operational & Healthy 🚀`"
        )

        await status_msg.edit_text(stats_text)

    except Exception as e:
        error_details = traceback.format_exc()
        print(f"❌ [STATS DB ERROR]:\n{error_details}")
        
        await status_msg.edit_text(
            f"❌ **Database Fetching Error:**\n\n"
            f"```python\n{e}\n```"
        )
