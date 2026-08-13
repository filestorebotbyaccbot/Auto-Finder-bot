from database.db import db, stories_col, requests_col
from rapidfuzz import process, fuzz

# Collections
users_col = db["bot_users"]
welcome_col = db["group_settings"]


# --- Group Welcome Settings Helper Functions ---

async def set_welcome_db(chat_id: int, text: str):
    """Sets or updates a custom welcome message for a group."""
    await welcome_col.update_one(
        {"chat_id": chat_id},
        {"$set": {"welcome_text": text}},
        upsert=True
    )
    return True


async def get_welcome_db(chat_id: int):
    """Fetches custom welcome message for a group."""
    data = await welcome_col.find_one({"chat_id": chat_id})
    if data and "welcome_text" in data:
        return data["welcome_text"]
    return None


# --- User Collection Helper Functions (For Broadcast) ---

async def add_user_db(user_id: int, first_name: str, username: str = None):
    """Saves or updates a user in MongoDB for broadcasting."""
    user_data = {
        "user_id": user_id,
        "first_name": first_name,
        "username": username
    }
    await users_col.update_one(
        {"user_id": user_id},
        {"$set": user_data},
        upsert=True
    )
    return True


async def get_all_users_db():
    """Fetches all registered user IDs from MongoDB."""
    user_ids = []
    async for doc in users_col.find({}, {"user_id": 1}):
        if "user_id" in doc:
            user_ids.append(doc["user_id"])
    return user_ids


# --- Story Collection Helper Functions ---

async def add_story_db(title: str, photo: str, link: str, description: str = ""):
    """Inserts or updates a story document into MongoDB."""
    # Store strictly the first line as the title
    clean_title = title.strip().split("\n")[0]
    
    story_data = {
        "title": clean_title,
        "photo": photo,
        "link": link,
        "description": description,
        "search_title": clean_title.lower()
    }
    
    await stories_col.update_one(
        {"search_title": story_data["search_title"]},
        {"$set": story_data},
        upsert=True
    )
    return True


async def get_all_titles():
    """Fetches all story titles from MongoDB."""
    titles = []
    async for doc in stories_col.find({}, {"title": 1}):
        if "title" in doc:
            titles.append(doc["title"])
    return titles


async def search_story_db(query: str):
    """
    Performs Exact Match + RapidFuzz Top 4 Suggestions search against MongoDB story titles.
    """
    clean_query = query.strip().lower()
    
    # 1. Exact Match Check
    exact_match = await stories_col.find_one({"search_title": clean_query})
    if exact_match:
        return {"type": "exact", "data": exact_match}

    # 2. RapidFuzz Search
    all_titles = await get_all_titles()
    if not all_titles:
        return {"type": "none", "data": []}

    # Extract top 4 best matches
    matches = process.extract(
        query, 
        all_titles, 
        scorer=fuzz.WRatio, 
        limit=4
    )

    # Filter out matches below score threshold of 45
    filtered_matches = [match[0] for match in matches if match[1] >= 45]

    if not filtered_matches:
        return {"type": "none", "data": []}

    # If the top match score is very high (>= 85%), return it directly
    if matches[0][1] >= 85:
        matched_doc = await stories_col.find_one({"title": matches[0][0]})
        return {"type": "exact", "data": matched_doc}

    # Otherwise return up to 4 suggestions
    return {"type": "suggestions", "data": filtered_matches}


# --- Request Collection Helper Functions ---

async def add_request_db(user_id: int, user_name: str, story_name: str):
    """Saves a user story request into database."""
    request_data = {
        "user_id": user_id,
        "user_name": user_name,
        "story_name": story_name,
        "status": "pending"
    }
    await requests_col.insert_one(request_data)
    return True


# --- Delete Operations ---

async def delete_single_story_db(query: str):
    """Deletes a single story document by title or search title."""
    clean_query = query.strip().lower()
    
    # Try deleting by search title first
    result = await stories_col.delete_one({"search_title": clean_query})
    if result.deleted_count > 0:
        return True
    
    # Fallback to exact title match
    result_alt = await stories_col.delete_one({"title": query.strip()})
    return result_alt.deleted_count > 0


async def delete_all_stories_db():
    """Deletes all story documents from the database."""
    result = await stories_col.delete_many({})
    return result.deleted_count
