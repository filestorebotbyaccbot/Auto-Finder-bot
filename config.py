import os

class Config:
    # --- Existing Configurations ---
    API_ID = int(os.environ.get("API_ID", "123456"))
    API_HASH = os.environ.get("API_HASH", "your_api_hash_here")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token_here")
    
    # --- Source Channels for Auto-Indexing (IDs usually start with -100) ---
    # Example: "-1001234567890 -1009876543210"
    SOURCE_CHANNELS = [int(x) for x in os.environ.get("SOURCE_CHANNELS", "-1003967446213").split()]
    
    # --- Database Settings ---
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority")
    DATABASE_NAME = os.environ.get("DATABASE_NAME", "VC_Story_Finder_Bot")
    STORIES_COLLECTION = os.environ.get("STORIES_COLLECTION", "stories")
    REQUESTS_COLLECTION = os.environ.get("REQUESTS_COLLECTION", "story_requests")
    
    # --- Log Channel & Bot Configurations ---
    LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", "-1003961183518"))
    PORT = int(os.environ.get("PORT", "8080"))
    ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "12345678").split()]
    STORY_CHANNEL = os.environ.get("STORY_CHANNEL", "https://t.me/freestoryhubMR")
    SUPPORT_GROUP = os.environ.get("SUPPORT_GROUP", "https://t.me/pratilipifm0900")
    OWNER_LINK = os.environ.get("OWNER_LINK", "https://t.me/KCXRY")

    # Force Subscribe Settings
    FSUB_ENABLE = os.environ.get("FSUB_ENABLE", "True").lower() == "true"  # True / False
    FORCE_SUB_CHANNEL = int(os.environ.get("FORCE_SUB_CHANNEL", "-1003226074080"))
    FORCE_SUB_LINK = os.environ.get("FORCE_SUB_LINK", "https://t.me/freestoryhubMR")

    # PM Search Restriction Settings (अगर True है तो PM में स्टोरी नहीं मिलेगी, केवल ग्रुप का मैसेज दिखेगा)
    DISABLE_PM_SEARCH = os.environ.get("DISABLE_PM_SEARCH", "True").lower() == "true"  # True / False
