# Ingestion Agent : for fetching news articles from various sources and storing them in the SQLite database.
    
# src/agents/ingestion.py
import os
import requests
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

def fetch_real_news() -> list:
    """
    Fetches real financial news from Finnhub API.
    Returns a list of articles formatted for the pipeline.
    """
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        raise ValueError("FINNHUB_API_KEY is not set in .env")

    print("📡 Fetching real-time news from Finnhub...")
    
    # Finnhub general news endpoint
    url = f"https://finnhub.io/api/v1/news?category=general&token={api_key}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        raw_articles = response.json()
    except Exception as e:
        print(f"❌ Failed to fetch news: {e}")
        return []

    formatted_articles = []
    for item in raw_articles[:10]:  # Limit to 10 articles per run to save API costs
        # Map Finnhub's schema to our NewsState schema
        article = {
            "id": str(uuid.uuid4()),  # Generate unique ID
            "title": item.get("headline", "No Title"),
            "content": item.get("summary", ""),  # Finnhub gives summary, not full content
            "source": item.get("source", "Finnhub"),
        }
        formatted_articles.append(article)

    print(f"✅ Fetched {len(formatted_articles)} real articles.")
    return formatted_articles
