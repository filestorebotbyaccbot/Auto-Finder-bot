import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database.stories_db import get_top_categories_db

@Client.on_message(filters.command(["top", "topcategories"]) & (filters.group | filters.private))
async def show_top_categories_cmd(bot: Client, message: Message):
    top_cats = await get_top_categories_db(limit=6)

    if not top_cats:
        return await message.reply_text("❌ **अभी डेटाबेस में कोई ट्रेंडिंग या टॉप कैटेगरी नहीं है!**")

    buttons = []
    text_content = "🔥 **<u>TOP & MOST POPULAR CATEGORIES</u>**\n\n"

    # 2x2 Grid Buttons Layout
    row = []
    for idx, item in enumerate(top_cats, 1):
        cat_name = item["category"]
        count = item["count"]
        
        text_content += f"**{idx}.** `{cat_name.capitalize()}` — **{count} Stories**\n"
        
        row.append(InlineKeyboardButton(f"🔥 {cat_name.capitalize()} ({count})", callback_data=f"pgcat#{cat_name}#1"))
        
        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton("❌ Close", callback_data="close_all_st")])
    markup = InlineKeyboardMarkup(buttons)

    text_content += "\n👇 **Tap any category below to browse stories:**"

    msg = await message.reply_text(text_content, reply_markup=markup)

    # Group me Auto-delete after 2 mins
    if message.chat.type.value != "private":
        await asyncio.sleep(120)
        try:
            await msg.delete()
            await message.delete()
        except Exception:
            pass
