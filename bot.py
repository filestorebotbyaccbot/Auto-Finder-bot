import os
import logging
import asyncio
from pyrogram import Client, idle
import pyromod
from aiohttp import web
from config import Config
from web.render_server import web_server

logging.basicConfig(level=logging.INFO)

app = Client(
    "VCStoryFinderBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    plugins=dict(root="plugins")
)

async def main():
    # Start Pyrogram Client
    await app.start()
    me = await app.get_me()
    print(f"🚀 {me.first_name} Client Started Successfully!")

    # Check if coming back from /restart command
    if os.path.exists("restart_info.txt"):
        try:
            with open("restart_info.txt", "r") as f:
                chat_id, msg_id = f.read().splitlines()
            
            # Update Admin's Restart Message
            await app.edit_message_text(
                chat_id=int(chat_id),
                message_id=int(msg_id),
                text="✅ <b>ʙᴏᴛ ʜᴀꜱ ʙᴇᴇɴ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ʀᴇꜱᴛᴀʀᴛᴇᴅ!</b>"
            )
            os.remove("restart_info.txt")
        except Exception as e:
            print(f"⚠️ Failed to edit restart message: {e}")

        # Send Notification to LOG_CHANNEL on Restart
        if Config.LOG_CHANNEL:
            try:
                await app.send_message(
                    chat_id=Config.LOG_CHANNEL,
                    text=f"⚡ <b>ꜱʏꜱᴛᴇᴍ ɴᴏᴛɪꜰɪᴄᴀᴛɪᴏɴ:</b> {me.mention} ʜᴀꜱ ʙᴇᴇɴ ʀᴇꜱᴛᴀʀᴛᴇᴅ &amp; ᴍᴇᴍᴏʀʏ ᴄʟᴇᴀʀᴇᴅ!"
                )
            except Exception as e:
                print(f"⚠️ Failed to send restart log: {e}")
    
    # Normal Bootup Notification (First Time Deployment / Server Reboot)
    elif Config.LOG_CHANNEL:
        try:
            await app.send_message(
                chat_id=Config.LOG_CHANNEL,
                text=f"⚡ <b>{me.mention} ɪꜱ ɴᴏᴡ ʟɪᴠᴇ &amp; ʀᴜɴɴɪɴɢ!</b>\n\n🆔 <b>ʙᴏᴛ ɪᴅ:</b> <code>{me.id}</code>\n🌐 <b>ꜱᴇʀᴠᴇʀ:</b> ʀᴇɴᴅᴇʀ ᴡᴇʙ ꜱᴇʀᴠɪᴄᴇ (ᴘᴏʀᴛ {Config.PORT})"
            )
        except Exception as e:
            print(f"⚠️ Failed to send log to LOG_CHANNEL: {e}")

    # Start Web Server for Render Keep-Alive
    web_app = await web_server()
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", Config.PORT)
    await site.start()
    print(f"🌐 Keep-Alive Web Server running on Port {Config.PORT}")

    # Keep bot running until stopped
    await idle()
    await app.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
