import time
from pyrogram import Client, filters
from pyrogram.types import Message
from config import Config
from database.stories_db import stories_col, users_col

# Convert seconds to readable string format
def get_readable_time(seconds: int) -> str:
    count = 0
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]
    
    while count < 4:
        count += 1
        if count < 3:
            remainder, result = divmod(seconds, 60)
        else:
            remainder, result = divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)

    for i in range(len(time_list)):
        time_list[i] = str(time_list[i]) + time_suffix_list[i]
    if len(time_list) == 4:
        time_list.append(time_list.pop(1))
        
    return ", ".join(time_list[::-1])


# Bot Start Time for Uptime calculation
BOT_START_TIME = time.time()


@Client.on_message(filters.command("stats") & filters.private)
async def stats_command_handler(bot: Client, message: Message):
    user_id = message.from_user.id

    # Admin verification
    if user_id not in Config.ADMIN_IDS and user_id != Config.OWNER_ID:
        return

    status_msg = await message.reply_text("📊 **Fetching database statistics...**")

    try:
        # Fetch MongoDB metrics
        total_users = await users_col.count_documents({})
        total_stories = await stories_col.count_documents({})
        
        # Calculate Bot Uptime
        uptime = get_readable_time(int(time.time() - BOT_START_TIME))

        stats_text = (
            f"📊 **<u>BOT DATABASE STATISTICS</u>**\n\n"
            f"👤 **Total Users:** `{total_users}`\n"
            f"📚 **Total Stories:** `{total_stories}`\n"
            f"⏱️ **Bot Uptime:** `{uptime}`\n\n"
            f"⚙️ **System Status:** `Running Fine 🚀`"
        )

        await status_msg.edit_text(stats_text)

    except Exception as e:
        await status_msg.edit_text(f"❌ **Error while fetching statistics:**\n`{e}`")
