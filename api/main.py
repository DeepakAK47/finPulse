# api/main.py
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from src.graphs.query_graph import query_app

# Imports for the manual ingestion trigger
from src.agents.ingestion import fetch_real_news
from src.graphs.ingestion_graph import ingestion_app
from src.database.sqlite_client import init_db

app = FastAPI(title="FinPulse API")

@app.get("/health")
def health():
    return {"status": "ok"}


class QueryInput(BaseModel):
    query: str

@app.post("/query")
def query_news(payload: QueryInput):
    initial_state = {"query": payload.query}
    result = query_app.invoke(initial_state)
    return {
        "query": payload.query,
        "query_type": result.get("query_type"),
        "results": result.get("results")
    }


# --- NEW ENDPOINT FOR STREAMLIT UI ---
@app.post("/fetch-latest")
def fetch_latest_news(background_tasks: BackgroundTasks):
    """Triggers the real-time ingestion pipeline manually from the UI."""
    
    def run_pipeline():
        print("\n⏰ Manual trigger: Running news ingestion...")
        init_db()
        articles = fetch_real_news()
        
        # Limit to 5 articles to prevent long wait times and API rate limits
        for article in articles[:5]:
            initial_state = {
                "article_id": article["id"],
                "title": article["title"],
                "content": article["content"],
                "source": article["source"],
                "is_duplicate": False,
                "canonical_id": None
            }
            try:
                # Run the full LangGraph pipeline
                result = ingestion_app.invoke(initial_state)
                print(f"Processed: {article['title'][:50]}... | Duplicate: {result.get('is_duplicate')}")
            except Exception as e:
                print(f"❌ Error processing article: {e}")

    # Run the pipeline in the background so the UI doesn't freeze
    background_tasks.add_task(run_pipeline)
    
    return {
        "status": "success", 
        "message": "Fetching latest news in the background. Please wait a moment and refresh."
    }

