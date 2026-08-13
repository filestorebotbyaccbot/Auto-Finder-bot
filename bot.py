import logging
from pyrogram import Client
import pyromod  # Enables .ask() for conversation state
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
    
    # Initialize Port 8080 Keep-Alive Web Server for Render
    web_app = app.loop.run_until_complete(web_server())
    site = web.TCPSite(web.AppRunner(web_app), "0.0.0.0", Config.PORT)
    app.loop.run_until_complete(site.start())
    print(f"🌐 Keep-Alive Web Server running on Port {Config.PORT}")
    
    app.loop.run_forever()
