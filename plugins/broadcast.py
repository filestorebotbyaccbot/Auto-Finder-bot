import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from config import Config
from database.stories_db import get_all_users_db

@Client.on_message(filters.command("broadcast") & filters.private)
async def broadcast_handler(bot: Client, message: Message):
    # Admin Permission Check
    if message.from_user.id not in Config.ADMIN_IDS:
        return await message.reply_text("⛔ **You are not authorized to use this command!**")

    # Reply Message Validation
    if not message.reply_to_message:
        return await message.reply_text(
            "⚠️ **उपयोग करने का तरीका:**\n\n"
            "जिस मैसेज (Photo/Text/Video/Link) को ब्रॉडकास्ट करना चाहते हैं, उसे **Reply** करके `/broadcast` टाइप करें।"
        )

    target_msg = message.reply_to_message
    all_users = await get_all_users_db()
    total_users = len(all_users)

    if total_users == 0:
        return await message.reply_text("❌ **डेटाबेस में कोई यूजर्स नहीं मिले!**")

    status_msg = await message.reply_text(f"🚀 **Broadcasting Started...**\n\n📊 Total Users: `{total_users}`")

    successful = 0
    failed = 0
    blocked = 0

    for user_id in all_users:
        try:
            # Copy and send the replied message to all users
            await target_msg.copy(chat_id=user_id)
            successful += 1
            # Small delay to prevent hitting Telegram flood limits
            await asyncio.sleep(0.05)
        except Exception as e:
            err = str(e).lower()
            if "blocked" in err or "user_is_blocked" in err:
                blocked += 1
            else:
                failed += 1

    # Final Progress Report
    report = (
        f"✅ **Broadcast Completed!**\n\n"
        f"👥 **Total Users:** `{total_users}`\n"
        f"🎉 **Successful:** `{successful}`\n"
        f"🚫 **Blocked Bot:** `{blocked}`\n"
        f"❌ **Failed:** `{failed}`"
    )

    await status_msg.edit_text(report)
