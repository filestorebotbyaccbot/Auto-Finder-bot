from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from database.stories_db import add_request_db

# 1. User Request Command Handler (/request <story_name>)
@Client.on_message(filters.command("request"))
async def request_command_handler(bot: Client, message: Message):
    # Command Validation
    if len(message.command) < 2:
        return await message.reply_text(
            "⚠️ **उपयोग करने का तरीका:**\n`/request <स्टोरी का नाम>`\n\n**उदाहरण:** `/request Veer Gatha`"
        )
    
    story_name = message.text.split(None, 1)[1].strip()
    user = message.from_user
    
    # Save Request into MongoDB
    await add_request_db(
        user_id=user.id,
        user_name=user.first_name,
        story_name=story_name
    )
    
    # Reply to User
    await message.reply_text(
        f"✅ **आपकी स्टोरी रिक्वेस्ट दर्ज कर ली गई है!**\n\n"
        f"📚 **स्टोरी:** `{story_name}`\n"
        f"जैसे ही स्टोरी अपलोड होगी, आपको बॉट द्वारा सूचित कर दिया जाएगा।"
    )
    
    # Admin Alert Notification Text
    admin_text = (
        f"📝 **नई स्टोरी रिक्वेस्ट आई है!**\n\n"
        f"👤 **यूजर:** {user.mention} (`{user.id}`)\n"
        f"📚 **स्टोरी का नाम:** `{story_name}`"
    )
    
    # Admin Inline Button (Callback data embeds user_id and story_name)
    admin_btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Mark as Uploaded", callback_data=f"req_done#{user.id}#{story_name[:20]}")]
    ])
    
    # Send Notification to all Admins
    for admin_id in Config.ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                reply_markup=admin_btn
            )
        except Exception as e:
            print(f"⚠️ Failed to send request alert to admin {admin_id}: {e}")


# 2. Admin Callback Handler for "Mark as Uploaded" Button
@Client.on_callback_query(filters.regex(r"^req_done#"))
async def request_done_callback(bot: Client, query: CallbackQuery):
    # Admin Security Check
    if query.from_user.id not in Config.ADMIN_IDS:
        return await query.answer("⛔ केवल एडमिन ही इसे अप्रूव कर सकते हैं!", show_alert=True)
    
    # Extract embedded data from callback
    _, user_id_str, story_snippet = query.data.split("#")
    user_id = int(user_id_str)
    
    # Notify the user that their story is uploaded
    try:
        user_notify_text = (
            f"🎉 **आपकी स्टोरी अपलोड हो गई है!**\n\n"
            f"📚 **स्टोरी:** `{story_snippet}`\n"
            f"अब आप ग्रुप में नाम टाइप करके या सर्च करके स्टोरी पढ़ सकते हैं।"
        )
        await bot.send_message(chat_id=user_id, text=user_notify_text)
        user_notified = True
    except Exception:
        user_notified = False
        
    # Update Admin Message Layout
    updated_admin_text = query.message.text + f"\n\n✨ **Status:** Uploaded by {query.from_user.mention}"
    if not user_notified:
        updated_admin_text += " *(यूजर को PM ब्लॉक होने के कारण मैसेज नहीं जा सका)*"
        
    await query.message.edit_text(
        text=updated_admin_text,
        reply_markup=None  # Remove the button after action
    )
    
    await query.answer("✅ यूजर को सूचित कर दिया गया है!")
