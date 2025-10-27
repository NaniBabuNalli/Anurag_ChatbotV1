import json
import os
from typing import List, Dict, Any

# Define the path to the JSON file relative to the 'chatbot_backend' directory
# Since main.py is in 'chatbot_backend' and scraped_data.json is in the parent directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(__file__), '..', 'scraped_data.json')

# Global variable to hold the loaded university data
UNIVERSITY_KNOWLEDGE_BASE = []

def load_knowledge_base():
    """
    Loads the scraped data into memory. This is our knowledge base.
    This function is called by the FastAPI startup event in main.py.
    """
    global UNIVERSITY_KNOWLEDGE_BASE
    if UNIVERSITY_KNOWLEDGE_BASE:
        print("Knowledge base already loaded.")
        return UNIVERSITY_KNOWLEDGE_BASE
        
    try:
        with open(DATA_FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Filter and prepare the data for efficient searching
            UNIVERSITY_KNOWLEDGE_BASE = data
        print(f"Successfully loaded {len(UNIVERSITY_KNOWLEDGE_BASE)} knowledge entries.")
        return UNIVERSITY_KNOWLEDGE_BASE
    except FileNotFoundError:
        print(f"ERROR: Knowledge base file not found at {DATA_FILE_PATH}")
        return []
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to decode JSON file: {e}")
        return []

def retrieve_contextual_answer(query: str, intent_name: str) -> str:
    """
    Performs a simple keyword search against the loaded knowledge base.
    It prioritizes matching the main category (flow) derived from the intent.
    """
    global UNIVERSITY_KNOWLEDGE_BASE
    
    if not UNIVERSITY_KNOWLEDGE_BASE:
        return "I apologize, the University knowledge base is currently unavailable. Please check back shortly."

    # 1. Map the Dialogflow Intent to a Category
    # Example intent: "Admissions.FeesQuery" -> We want "Admissions"
    try:
        category = intent_name.split('.')[-2].replace('_', ' ').title()
    except IndexError:
        # Fallback for simple intents that don't follow the dot convention
        category = intent_name.split('.')[0].replace('_', ' ').title()

    
    # 2. Prepare search terms
    search_query = query.lower()
    # Simple tokenization: remove common English words (optional for complex search, but good for simple keyword)
    ignore_words = {'the', 'a', 'is', 'what', 'are', 'for', 'of', 'in', 'and', 'how', 'much'}
    search_keywords = [w for w in search_query.split() if w not in ignore_words and len(w) > 3]
    
    best_match_content = None
    best_match_score = -1

    # 3. Search for the best match
    for item in UNIVERSITY_KNOWLEDGE_BASE:
        score = 0
        
        # Boost score if the item's category matches the detected category
        if item['category'].lower() == category.lower():
            score += 10
        
        # Score based on keyword presence in the content
        content_lower = item['content'].lower()
        for keyword in search_keywords:
            if keyword in content_lower:
                score += 3  # Higher keyword score for better relevance
        
        # Exact phrase match boost
        if search_query in content_lower:
            score += 5
            
        if score > best_match_score:
            best_match_score = score
            best_match_content = item

    # 4. Format the final response
    if best_match_content and best_match_score > 5:
        # Extract a snippet around the query for a more focused answer
        full_content = best_match_content['content']
        
        # Try to find the start of the query for context
        start_index = full_content.lower().find(search_query)
        if start_index == -1:
            start_index = 0 # If query not found (e.g., only keywords matched), start from top
            
        # Contextual start: Move back up to 150 chars, but not past the start
        snippet_start = max(0, start_index - 150)
        snippet_end = min(len(full_content), snippet_start + 450) # Take up to 450 characters
        
        snippet = full_content[snippet_start:snippet_end]
            
        # Clean up the snippet slightly for chat
        snippet = snippet.replace('\n', ' ').replace('  ', ' ')
        
        # Truncate at the end if it's too long
        if snippet_end < len(full_content):
            snippet += "..."
        
        # Provide the answer and a link for depth
        response_text = (
            f"**Information on {category}**: {snippet}\n\n"
            f"*(Source: {best_match_content['url']})*"
        )
        return response_text
    
    else:
        # Fallback response for general queries or low relevance
        return (
            f"I found some general information related to the '{category}' category, but could not find a specific answer for '{query}'. "
            "Could you please try rephrasing? For direct help, you can call +91-8181057057."
        )

# NOTE: The load_knowledge_base() call has been removed from here 
# and moved to the @app.on_event("startup") in main.py.
