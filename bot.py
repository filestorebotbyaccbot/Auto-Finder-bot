import logging
from pyrogram import Client
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

if __name__ == "__main__":
    app.start()
    print("🚀 VC Story Finder Bot Client Started!")
    
    # Send Restart/Live Notification to Log Channel
    if Config.LOG_CHANNEL:
        try:
            me = app.get_me()
            app.send_message(
                chat_id=Config.LOG_CHANNEL,
                text=f"⚡ **{me.mention} is now LIVE & Running!**\n\n🆔 **Bot ID:** `{me.id}`\n🌐 **Server:** Render Web Service (Port {Config.PORT})"
            )
        except Exception as e:
            print(f"⚠️ Failed to send log to LOG_CHANNEL: {e}")

    # Fix: Correct aiohttp AppRunner initialization for Render Port 8080
    async def start_services():
        web_app = await web_server()
        runner = web.AppRunner(web_app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", Config.PORT)
        await site.start()
        print(f"🌐 Keep-Alive Web Server running on Port {Config.PORT}")

    app.loop.run_until_complete(start_services())
    app.loop.run_forever()
