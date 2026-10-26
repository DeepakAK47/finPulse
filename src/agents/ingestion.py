# Ingestion Agent : for fetching news articles from various sources and storing them in the SQLite database.
    
import json
import os
import uuid

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOCK_DATA_PATH = os.path.join(BASE_DIR, "data", "mock_news.json")

def load_mock_news() -> list:
    """Reads the mock news dataset from the data folder."""
    if not os.path.exists(MOCK_DATA_PATH):
        raise FileNotFoundError(f"Mock data not found at {MOCK_DATA_PATH}")
        
    with open(MOCK_DATA_PATH, "r", encoding="utf-8") as file:
        articles = json.load(file)
        
    # Ensure every article has a unique ID
    for article in articles:
        if "id" not in article:
            article["id"] = str(uuid.uuid4())
            
    print(f"📥 Ingested {len(articles)} articles from mock dataset.")
    return articles