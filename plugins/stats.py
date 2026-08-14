import traceback
from pyrogram import Client, filters
from pyrogram.types import Message
from config import Config
from database.stories_db import stories_col, users_col

@Client.on_message(filters.command("stats") & filters.private)
async def stats_command_handler(bot: Client, message: Message):
    user_id = message.from_user.id
    
    # Debug Console Log 1: Command trigger confirm
    print(f"\n🔍 [STATS DEBUG] Command triggered by User ID: {user_id}")
    print(f"🔍 [STATS DEBUG] Config.ADMIN_IDS content: {Config.ADMIN_IDS}")

    # Admin Checking with direct debug response
    if user_id not in Config.ADMIN_IDS:
        print(f"❌ [STATS DEBUG] User ID {user_id} is NOT in Config.ADMIN_IDS!")
        return await message.reply_text(
            f"⛔ **Access Denied!**\n\n"
            f"• Your Telegram ID: `{user_id}`\n"
            f"• Config Admin List: `{Config.ADMIN_IDS}`\n\n"
            f"*(Make sure your ID is present in Config.ADMIN_IDS)*"
        )

    status_msg = await message.reply_text("📊 **Fetching database statistics...**")

    try:
        # Fetching count from Database
        total_users = await users_col.count_documents({})
        total_stories = await stories_col.count_documents({})

        stats_text = (
            f"📊 **<u>BOT DATABASE STATISTICS</u>**\n\n"
            f"👤 **Total Users:** `{total_users}`\n"
            f"📚 **Total Stories:** `{total_stories}`\n\n"
            f"⚙️ **System Status:** `Running Fine 🚀`"
        )

        await status_msg.edit_text(stats_text)
        print("✅ [STATS DEBUG] Stats fetched and sent successfully!")

    except Exception as e:
        error_details = traceback.format_exc()
        # Print full error log to Terminal
        print(f"❌ [STATS ERROR DETAILS]:\n{error_details}")
        
        # Send exact error to Telegram Chat
        await status_msg.edit_text(
            f"❌ **An Error Occurred:**\n\n"
            f"```python\n{e}\n```"
        )
