from pyrogram import Client, filters
from pyrogram.types import Message

@Client.on_message(filters.command(["id", "myid"]))
async def get_user_id_handler(bot: Client, message: Message):
    # 1. If replied to another user's message
    if message.reply_to_message:
        replied_user = message.reply_to_message.from_user
        if replied_user:
            text = (
                f"👤 **Replied User Details:**\n\n"
                f"✨ **Name:** {replied_user.mention}\n"
                f"🆔 **User ID:** `{replied_user.id}`\n"
                f"👤 **Username:** @{replied_user.username if replied_user.username else 'None'}"
            )
        else:
            text = "❌ Cannot fetch details for this user."
            
    # 2. Normal Command execution
    else:
        user = message.from_user
        text = (
            f"👤 **Your Details:**\n\n"
            f"✨ **Name:** {user.mention}\n"
            f"🆔 **User ID:** `{user.id}`\n"
            f"👤 **Username:** @{user.username if user.username else 'None'}\n"
        )
        
        # If used in Group/Channel, show Chat ID too
        if message.chat.type != "private":
            text += f"💬 **Chat ID:** `{message.chat.id}`"

    await message.reply_text(text)
