import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database.stories_db import get_top_categories_db

# Helper function to prevent button text overflow
def clean_top_button_text(cat_name: str, count: int, max_len: int = 18) -> str:
    name = str(cat_name).capitalize().strip()
    if len(name) > max_len:
        name = f"{name[:max_len-3]}..."
    return f"🔥 {name} ({count})"


@Client.on_message(filters.command(["top", "topcategories"]) & (filters.group | filters.private))
async def show_top_categories_cmd(bot: Client, message: Message):
    top_cats = await get_top_categories_db(limit=6)

    if not top_cats:
        return await message.reply_text("❌ **अभी डेटाबेस में कोई ट्रेंडिंग या टॉप कैटेगरी नहीं है!**")

    buttons = []
    text_content = "🔥 <b><u>TOP & MOST POPULAR CATEGORIES</u></b>\n\n"

    # 2x2 Grid Buttons Layout
    row = []
    for idx, item in enumerate(top_cats, 1):
        cat_name = item["category"]
        count = item["count"]
        
        text_content += f"<b>{idx}.</b> <code>{cat_name.capitalize()}</code> — <b>{count} Stories</b>\n"
        
        # Clean button text to prevent grid overflow
        btn_label = clean_top_button_text(cat_name, count, max_len=18)
        row.append(InlineKeyboardButton(btn_label, callback_data=f"pgcat#{cat_name}#1"))
        
        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton("❌ Close", callback_data="close_all_st")])
    markup = InlineKeyboardMarkup(buttons)

    text_content += "\n👇 <b>Tap any category below to browse stories:</b>\n⏱️ <i>This message will auto-delete in 2 minutes.</i>"

    msg = await message.reply_text(text_content, reply_markup=markup)

    # Auto-delete after 2 mins (both group and private to keep chat clean)
    await asyncio.sleep(120)
    try:
        await msg.delete()
        await message.delete()
    except Exception:
        pass
