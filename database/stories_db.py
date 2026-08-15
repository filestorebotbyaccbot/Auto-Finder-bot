import re
from rapidfuzz import process, fuzz
from database.db import db, stories_col, requests_col

# Collections
users_col = db["bot_users"]


# --- Text Normalization Helper Function ---

def clean_text_for_search(text: str) -> str:
    """Removes special symbols and extra spaces for 100% accurate search matching."""
    if not text:
        return ""
    text = re.sub(r'[^\w\s]', ' ', str(text).lower())
    return " ".join(text.split())


# --- User Collection Helper Functions (For Broadcast & Log Check) ---

async def add_user_db(user_id: int, first_name: str, username: str = None) -> bool:
    """
    Check karta hai ki user database me pehle se hai ya nahi.
    - Agar NAYA user hai -> DB me insert karega aur TRUE return karega.
    - Agar PURANA user hai -> Name/Username update karega aur FALSE return karega.
    """
    user_id = int(user_id)  # Ensure integer type matching
    
    # Check if user already exists
    user = await users_col.find_one({"user_id": user_id})
    
    if not user:
        # Naya User: Insert into Database
        await users_col.insert_one({
            "user_id": user_id,
            "first_name": first_name,
            "username": username
        })
        return True  # 🟢 Return True ONLY for New User
    else:
        # Purana User: Update latest name/username silently
        await users_col.update_one(
            {"user_id": user_id},
            {"$set": {"first_name": first_name, "username": username}}
        )
        return False  # 🔴 Return False for Existing User


async def get_all_users_db():
    """Fetches all registered user IDs from MongoDB."""
    user_ids = []
    async for doc in users_col.find({}, {"user_id": 1}):
        if "user_id" in doc:
            user_ids.append(doc["user_id"])
    return user_ids


# --- Story Collection Helper Functions ---

async def save_full_story_db(
    title: str,
    photo: str,
    link: str,
    status: str = "Ongoing",
    platform: str = "Pocket FM",
    genre: str = "General",
    episodes: str = "1 / ∞",
    description: str = "No description available."
):
    """
    Saves complete story metadata into MongoDB.
    Used by Auto-Induction and Interactive Add/Edit System.
    """
    clean_title = title.strip().split("\n")[0]
    
    story_data = {
        "title": clean_title,
        "photo": photo,
        "link": link,
        "status": status.strip().capitalize(),
        "platform": platform.strip(),
        "category": genre.strip().capitalize(),
        "genre": genre.strip().capitalize(),
        "episodes": episodes.strip(),
        "description": description.strip(),
        "search_title": clean_text_for_search(clean_title)
    }
    
    await stories_col.update_one(
        {"search_title": story_data["search_title"]},
        {"$set": story_data},
        upsert=True
    )
    return True


async def add_story_db(title: str, photo: str, link: str, description: str = ""):
    """Inserts or updates a story document into MongoDB."""
    return await save_full_story_db(
        title=title,
        photo=photo,
        link=link,
        description=description
    )


async def add_story_with_category_db(title: str, photo: str, link: str, category: str = "General", description: str = ""):
    """Inserts or updates a story document with Category."""
    return await save_full_story_db(
        title=title,
        photo=photo,
        link=link,
        genre=category,
        description=description
    )


async def update_story_field_db(title: str, field_name: str, new_value: str) -> bool:
    """
    Updates a single field (status, platform, genre, episodes, description, link, photo) of a story.
    """
    clean_query = clean_text_for_search(title)
    story = await stories_col.find_one({"$or": [{"search_title": clean_query}, {"title": title.strip()}]})
    
    if not story:
        return False

    update_data = {field_name: new_value.strip()}
    if field_name in ["genre", "category"]:
        update_data["genre"] = new_value.strip().capitalize()
        update_data["category"] = new_value.strip().capitalize()

    await stories_col.update_one({"_id": story["_id"]}, {"$set": update_data})
    return True


async def get_all_titles():
    """Fetches all story titles from MongoDB."""
    titles = []
    async for doc in stories_col.find({}, {"title": 1}):
        if "title" in doc and doc["title"]:
            titles.append(doc["title"])
    return titles


# --- 🎲 RANDOM STORY HELPER FUNCTION ---

async def get_random_story_db():
    """
    Fetches a single random story from MongoDB using $sample aggregation pipeline.
    """
    pipeline = [{"$sample": {"size": 1}}]
    random_story = None
    async for doc in stories_col.aggregate(pipeline):
        random_story = doc
    return random_story


# --- 🔍 ENHANCED SEARCH & SUGGESTION SYSTEM ---

async def search_story_db(query: str):
    """
    Performs Exact Match + Advanced RapidFuzz Top 4 Suggestions Search.
    """
    raw_query = query.strip()
    clean_query = clean_text_for_search(raw_query)
    
    if not clean_query:
        return {"type": "none", "data": []}

    # 1. Direct Search Title Exact Match Check
    exact_match = await stories_col.find_one({"search_title": clean_query})
    if exact_match:
        return {"type": "exact", "data": exact_match}

    # 2. Fetch all DB titles
    all_titles = await get_all_titles()
    if not all_titles:
        return {"type": "none", "data": []}

    # Cleaned map of titles for accurate fuzz comparison
    cleaned_titles_map = {title: clean_text_for_search(title) for title in all_titles}

    # 3. RapidFuzz Extraction using token_set_ratio
    matches = process.extract(
        clean_query, 
        cleaned_titles_map, 
        scorer=fuzz.token_set_ratio, 
        limit=4
    )

    # High Confidence Match (>= 85%) -> Open Direct Story
    if matches and matches[0][1] >= 85:
        matched_original_title = matches[0][2]
        matched_doc = await stories_col.find_one({"title": matched_original_title})
        if matched_doc:
            return {"type": "exact", "data": matched_doc}

    # Suggestions Threshold (>= 30% score)
    filtered_matches = []
    for match in matches:
        score = match[1]
        original_title = match[2]
        if score >= 30:
            filtered_matches.append(original_title)

    if not filtered_matches:
        return {"type": "none", "data": []}

    return {"type": "suggestions", "data": filtered_matches}


# --- Category & Pagination Helper Functions ---

async def get_all_categories_db():
    """Fetches list of all unique categories from database."""
    categories = await stories_col.distinct("category")
    return [cat for cat in categories if cat]


async def get_stories_by_category_db(category_name: str, limit: int = 10):
    """Fetches stories matching a specific category."""
    stories = []
    async for doc in stories_col.find({"category": category_name}).limit(limit):
        stories.append(doc)
    return stories


async def get_stories_by_category_paged_db(category_name: str, page: int = 1, page_size: int = 5):
    """Fetches stories matching a category with pagination support."""
    skip = (page - 1) * page_size
    
    total_count = await stories_col.count_documents({"category": category_name})
    
    stories = []
    async for doc in stories_col.find({"category": category_name}).skip(skip).limit(page_size):
        stories.append(doc)
        
    return stories, total_count


async def get_top_categories_db(limit: int = 6):
    """Safely fetches top categories sorted by the number of stories."""
    try:
        pipeline = [
            {"$match": {"category": {"$ne": None, "$exists": True}}},
            {"$group": {"_id": "$category", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": limit}
        ]
        
        top_categories = []
        async for doc in stories_col.aggregate(pipeline):
            if doc and "_id" in doc and doc["_id"]:
                top_categories.append({"category": str(doc["_id"]), "count": doc["count"]})
                
        return top_categories
    except Exception as e:
        print(f"❌ [DB TOP CAT ERROR]: {e}")
        return []


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
    clean_query = clean_text_for_search(query)
    
    result = await stories_col.delete_one({"search_title": clean_query})
    if result.deleted_count > 0:
        return True
    
    result_alt = await stories_col.delete_one({"title": query.strip()})
    return result_alt.deleted_count > 0


async def delete_all_stories_db():
    """Deletes all story documents from the database."""
    result = await stories_col.delete_many({})
    return result.deleted_count


# --- Statistics Helper Functions ---

async def get_total_users_count():
    """Returns the total number of registered users."""
    return await users_col.count_documents({})


async def get_total_stories_count():
    """Returns the total number of stories in database."""
    return await stories_col.count_documents({})


async def get_total_requests_count():
    """Returns the total number of pending story requests."""
    return await requests_col.count_documents({"status": "pending"})
