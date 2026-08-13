import motor.motor_asyncio
from config import Config

# Async Motor Mongo Client Initialization
client = motor.motor_asyncio.AsyncIOMotorClient(Config.MONGO_URI)

# Dynamic DB & Collections Selection
db = client[Config.DATABASE_NAME]
stories_col = db[Config.STORIES_COLLECTION]
requests_col = db[Config.REQUESTS_COLLECTION]

print(f"💾 MongoDB Connected Successfully -> DB: '{Config.DATABASE_NAME}'")
