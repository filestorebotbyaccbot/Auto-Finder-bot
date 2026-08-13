from database.db import stories_col, requests_col
from rapidfuzz import process, fuzz

async def add_story_db(title: str, photo: str, link: str, description: str = ""):
    """Inserts or updates a story document into MongoDB."""
    clean_title = title.strip().split("\n")[0]  # Store only 1st line as title
    
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
    Performs Exact + RapidFuzz matching against MongoDB story titles.
    """
    clean_query = query.strip().lower()
    
    # 1. Exact Match Check
    exact_match = await stories_col.find_one({"search_title": clean_query})
    if exact_match:
        return exact_match, 100

    # 2. RapidFuzz Search
    all_titles = await get_all_titles()
    if not all_titles:
        return None, 0

    best_match = process.extractOne(query, all_titles, scorer=fuzz.WRatio)
    if best_match and best_match[1] >= 60:
        matched_title = best_match[0]
        matched_doc = await stories_col.find_one({"title": matched_title})
        return matched_doc, best_match[1]

    return None, 0

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
  async def delete_single_story_db(query: str):
    """Deletes a single story document by title or exact match."""
    clean_query = query.strip().lower()
    
    # Check and delete by exact search title
    result = await stories_col.delete_one({"search_title": clean_query})
    if result.deleted_count > 0:
        return True
    
    # If exact match fails, try deleting by original title
    result_alt = await stories_col.delete_one({"title": query.strip()})
    return result_alt.deleted_count > 0

async def delete_all_stories_db():
    """Deletes all story documents from the database."""
    result = await stories_col.delete_many({})
    return result.deleted_count
    
