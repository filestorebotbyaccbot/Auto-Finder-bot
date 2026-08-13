import os

class Config:
    # --- Telegram Credentials ---
    API_ID = int(os.environ.get("API_ID", "123456"))
    API_HASH = os.environ.get("API_HASH", "your_api_hash_here")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token_here")
    
    # --- Log Channel ID (Channel ID starts with -100) ---
    LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", "-1001234567890"))
    
    # --- MongoDB Settings ---
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority")
    DATABASE_NAME = os.environ.get("DATABASE_NAME", "VC_Story_Finder_Bot")
    STORIES_COLLECTION = os.environ.get("STORIES_COLLECTION", "stories")
    REQUESTS_COLLECTION = os.environ.get("REQUESTS_COLLECTION", "story_requests")
    
    # --- Render Server Settings ---
    PORT = int(os.environ.get("PORT", "8080"))
    
    # --- Bot & Channel Settings ---
    ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "12345678").split()]
    STORY_CHANNEL = os.environ.get("STORY_CHANNEL", "https://t.me/YourStoryChannel")
    SUPPORT_GROUP = os.environ.get("SUPPORT_GROUP", "https://t.me/YourSupportGroup")
    OWNER_LINK = os.environ.get("OWNER_LINK", "https://t.me/YourOwnerUsername")
