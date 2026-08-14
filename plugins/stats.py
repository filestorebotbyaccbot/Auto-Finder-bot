from pyrogram import Client, filters
from pyrogram.types import Message
from config import Config
from database.stories_db import stories_col, users_col

# Custom Admin Filter Check using Config.ADMIN_IDS
async def admin_filter(_, __, message: Message):
    return message.from_user and message.from_user.id in Config.ADMIN_IDS

admin_only = filters.create(admin_filter)


@Client.on_message(filters.command("stats") & filters.private & admin_only)
async def stats_command_handler(bot: Client, message: Message):
    status_msg = await message.reply_text("📊 **Fetching database statistics...**")

    try:
        # Fetch count from database
        total_users = await users_col.count_documents({})
        total_stories = await stories_col.count_documents({})

        stats_text = (
            f"📊 **<u>BOT DATABASE STATISTICS</u>**\n\n"
            f"👤 **Total Users:** `{total_users}`\n"
            f"📚 **Total Stories:** `{total_stories}`\n\n"
            f"⚙️ **System Status:** `Running Fine 🚀`"
        )

        await status_msg.edit_text(stats_text)

    except Exception as e:
        await status_msg.edit_text(f"❌ **Error while fetching statistics:**\n`{e}`")
