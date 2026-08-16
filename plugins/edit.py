import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from pyrogram.enums import ParseMode
from config import Config
from database.stories_db import stories_col, clean_text_for_search, update_story_field_db

# Store temporary edit state: {user_id: "title"}
EDIT_CACHE = {}


# --- Helper Function to Build Aesthetic HTML Caption ---
def build_aesthetic_caption(story: dict, bot_username: str = None) -> str:
    title = story.get("title", "Unknown Story")
    status = story.get("status", "Ongoing")
    platform = story.get("platform", "Pocket FM")
    genre = story.get("category", story.get("genre", "General")).capitalize()
    episodes = story.get("episodes", "1 / ∞")
    description = story.get("description", "No description available for this story.")

    # Status Emoji Logic
    status_emoji = "🟢" if str(status).lower() in ["completed", "complete"] else "♨️"

    # 🔥 Hyperlinked Text (नाम 'Loki' पर लिंक हिडन रहेगा)
    powered_by_text = f"⚡ <b>Pᴏᴡᴇʀᴇᴅ Bʏ :</b> <a href='https://t.me/{bot_username}'>Loki</a>\n" if bot_username else ""

    caption = (
        f"<b>📢 NEW STORY / UPDATE!</b>\n\n"
        f"<b>{status_emoji}Story : {title}</b>\n"
        f"<b>🔰Status : {str(status).capitalize()}</b>\n"
        f"<b>🖥️Platform : {platform}</b>\n"
        f"<b>🧩Genre : {genre}</b>\n"
        f"<b>🎬Episodes : {episodes}</b>\n"
        f"═══════════════════\n"
        f"📝 <b>Story Description :-</b>\n"
        f"<blockquote expandable>{description}</blockquote>\n\n"
        f"{powered_by_text}"
    )
    return caption


def build_channel_buttons(story: dict) -> InlineKeyboardMarkup:
    """चैनल पोस्ट के लिए बटन्स"""
    likes_count = len(story.get("likes", [])) if isinstance(story.get("likes"), list) else story.get("likes", 0)
    dislikes_count = len(story.get("dislikes", [])) if isinstance(story.get("dislikes"), list) else story.get("dislikes", 0)
    story_id = str(story["_id"])

    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎧 Lɪsᴛᴇɴ / Pʟᴀʏ Sᴛᴏʀʏ", url=story["link"])],
        [
            InlineKeyboardButton(f"👍 {likes_count}", callback_data=f"rate#like#{story_id}"),
            InlineKeyboardButton(f"👎 {dislikes_count}", callback_data=f"rate#dislike#{story_id}")
        ],
        [InlineKeyboardButton("⭐ Aᴅᴅ Fᴀᴠᴏʀɪᴛᴇ", callback_data=f"fav#toggle#{story_id}")]
    ])


async def sync_edited_story_to_channel(bot: Client, story: dict):
    """Update Channel पर मौजूद पोस्ट को लाइव एडिट करता है"""
    channel_id = getattr(Config, "UPDATE_CHANNEL", None)
    msg_id = story.get("channel_message_id")

    if not channel_id or not msg_id:
        return

    bot_username = bot.me.username if bot.me else (await bot.get_me()).username
    caption = build_aesthetic_caption(story, bot_username=bot_username)
    buttons = build_channel_buttons(story)

    try:
        if story.get("photo"):
            await bot.edit_message_media(
                chat_id=channel_id,
                message_id=msg_id,
                media=InputMediaPhoto(media=story["photo"], caption=caption, parse_mode=ParseMode.HTML),
                reply_markup=buttons
            )
        else:
            await bot.edit_message_text(
                chat_id=channel_id,
                message_id=msg_id,
                text=caption,
                reply_markup=buttons,
                disable_web_page_preview=True,
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        print(f"⚠️ [Edit Command Channel Sync Error]: {e}")


# 1. Main Edit Command (/edit Story Name)
@Client.on_message(filters.command("edit") & filters.private)
async def edit_story_start(bot: Client, message: Message):
    if message.from_user.id not in Config.ADMIN_IDS:
        return await message.reply_text("⛔ <b>ᴀᴄᴄᴇꜱꜱ ᴅᴇɴɪᴇᴅ! ᴏɴʟʏ ᴀᴅᴍɪɴꜱ ᴄᴀɴ ᴜꜱᴇ ᴛʜɪꜱ.</b>")

    text = message.text.split(maxsplit=1)
    if len(text) < 2:
        return await message.reply_text(
            "⚠️ <b>ɪɴᴠᴀʟɪᴅ ꜰᴏʀᴍᴀᴛ!</b>\n\n"
            "<b>Usage:</b> <code>/edit Story Title</code>\n"
            "<b>Example:</b> <code>/edit Celebrity Se Pyaar</code>"
        )

    story_title = text[1].strip()
    clean_query = clean_text_for_search(story_title)

    # Check if story exists in Database
    story = await stories_col.find_one({"$or": [{"search_title": clean_query}, {"title": story_title}]})
    if not story:
        return await message.reply_text(f"❌ <b>Story '{story_title}' not found in Database!</b>")

    # Save title in Cache for Callback query
    EDIT_CACHE[message.from_user.id] = story["title"]

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🟢 Status", callback_data="ed_field_status"),
            InlineKeyboardButton("📺 Platform", callback_data="ed_field_platform")
        ],
        [
            InlineKeyboardButton("🧩 Genre", callback_data="ed_field_genre"),
            InlineKeyboardButton("🎬 Episodes", callback_data="ed_field_episodes")
        ],
        [
            InlineKeyboardButton("📝 Description", callback_data="ed_field_description")
        ],
        [
            InlineKeyboardButton("🔗 Link", callback_data="ed_field_link"),
            InlineKeyboardButton("🖼️ Cover Photo", callback_data="ed_field_photo")
        ],
        [
            InlineKeyboardButton("❌ Cancel", callback_data="ed_cancel")
        ]
    ])

    await message.reply_text(
        f"🛠️ <b>ᴇᴅɪᴛ ᴍᴇɴᴜ ꜰᴏʀ:</b> <code>{story['title']}</code>\n\n"
        f"👇 Select which detail you want to change:",
        reply_markup=buttons,
        parse_mode=ParseMode.HTML
    )


# 2. Callback Query Handler for Buttons
@Client.on_callback_query(filters.regex(r"^ed_"))
async def edit_callback_handler(bot: Client, query: CallbackQuery):
    user_id = query.from_user.id

    if user_id not in Config.ADMIN_IDS:
        return await query.answer("⛔ Access Denied!", show_alert=True)

    if query.data == "ed_cancel":
        EDIT_CACHE.pop(user_id, None)
        await query.message.delete()
        return await query.answer("Cancelled!")

    story_title = EDIT_CACHE.get(user_id)
    if not story_title:
        return await query.answer("⚠️ Session Expired! Please type /edit again.", show_alert=True)

    field = query.data.replace("ed_field_", "")
    field_labels = {
        "status": "Status (e.g. Completed / Ongoing)",
        "platform": "Platform (e.g. Pocket FM / Pratilipi FM)",
        "genre": "Genre / Category (e.g. Romantic / Action)",
        "episodes": "Episodes Count (e.g. 43 / 43)",
        "description": "Story Description",
        "link": "Listen / Play Link",
        "photo": "Cover Photo URL"
    }

    label = field_labels.get(field, field)
    await query.message.delete()

    # Ask user for input
    ask_msg = await bot.send_message(
        chat_id=query.message.chat.id,
        text=f"✏️ <b>Now send the new value for [{label}] for '{story_title}':</b>\n\n"
             f"⏱️ <i>Reply within 60 seconds...</i>",
        parse_mode=ParseMode.HTML
    )

    try:
        # Listen for user reply
        response: Message = await bot.listen(chat_id=query.message.chat.id, user_id=user_id, timeout=60)
        new_val = response.text.strip() if response.text else ""

        if not new_val:
            return await ask_msg.edit_text("❌ <b>Invalid input! Text message required.</b>", parse_mode=ParseMode.HTML)

        # Update Database
        success = await update_story_field_db(story_title, field, new_val)
        
        if success:
            # Delete asking message
            try:
                await ask_msg.delete()
            except Exception:
                pass

            # Fetch fresh story object from Database
            updated_story = await stories_col.find_one({"search_title": clean_text_for_search(story_title)})
            
            if not updated_story:
                return await bot.send_message(query.message.chat.id, "✅ <b>Successfully Updated!</b>")

            # 🚀 Auto-Sync live changes to Update Channel
            asyncio.create_task(sync_edited_story_to_channel(bot, updated_story))

            # Fetch Bot Username for Preview
            bot_username = bot.me.username if bot.me else (await bot.get_me()).username
            status_emoji = "🟢" if str(updated_story.get('status', '')).lower() in ["completed", "complete"] else "♨️"
            powered_by_text = f"⚡ <b>Pᴏᴡᴇʀᴇᴅ Bʏ :</b> <a href='https://t.me/{bot_username}'>Loki</a>"

            # Build aesthetic preview for admin
            preview_caption = (
                f"✅ <b><u>FIELD UPDATED SUCCESSFULLY!</u></b>\n"
                f"📌 <b>Updated Field:</b> <code>{field.capitalize()}</code>\n"
                f"═══════════════════\n"
                f"<b>{status_emoji}Story : {updated_story.get('title')}</b>\n"
                f"<b>🔰Status : {str(updated_story.get('status')).capitalize()}</b>\n"
                f"<b>🖥️Platform : {updated_story.get('platform')}</b>\n"
                f"<b>🧩Genre : {str(updated_story.get('category', updated_story.get('genre'))).capitalize()}</b>\n"
                f"<b>🎬Episodes : {updated_story.get('episodes')}</b>\n"
                f"═══════════════════\n"
                f"📝 <b>Story Description :-</b>\n"
                f"<blockquote expandable>{updated_story.get('description')}</blockquote>\n\n"
                f"{powered_by_text}"
            )

            photo_url = updated_story.get("photo")
            story_link = updated_story.get("link", "https://t.me")

            action_buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🎧 Lɪsᴛᴇɴ / Pʟᴀʏ Sᴛᴏʀʏ", url=story_link)],
                [InlineKeyboardButton("❌ Cʟᴏsᴇ", callback_data="close_all_st")]
            ])

            # Try sending with Photo so cover photo doesn't disappear
            if photo_url and (photo_url.startswith("http") or not photo_url.startswith("http")):
                try:
                    return await bot.send_photo(
                        chat_id=query.message.chat.id,
                        photo=photo_url,
                        caption=preview_caption,
                        reply_markup=action_buttons,
                        parse_mode=ParseMode.HTML
                    )
                except Exception as e:
                    print(f"❌ Failed to send photo preview: {e}")

            # Fallback to Text if photo URL breaks/fails
            await bot.send_message(
                chat_id=query.message.chat.id,
                text=preview_caption,
                reply_markup=action_buttons,
                disable_web_page_preview=True,
                parse_mode=ParseMode.HTML
            )
        else:
            await ask_msg.edit_text("❌ <b>Failed to update database!</b>", parse_mode=ParseMode.HTML)

    except asyncio.TimeoutError:
        await ask_msg.edit_text("⏱️ <b>Timeout! You didn't send any message in 60 seconds.</b>", parse_mode=ParseMode.HTML)
