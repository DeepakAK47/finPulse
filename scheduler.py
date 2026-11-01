# scheduler.py
from apscheduler.schedulers.blocking import BlockingScheduler
from src.database.sqlite_client import init_db
from src.agents.ingestion import fetch_real_news
from src.graphs.ingestion_graph import ingestion_app

def run_pipeline():
    print("\n⏰ Running scheduled news ingestion...")
    init_db()
    
    articles = fetch_real_news()
    
    for article in articles:
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

if __name__ == "__main__":
    print("🚀 Starting FinPulse Scheduler...")
    init_db()
    
    # Run once immediately on startup
    run_pipeline()
    
    # Schedule to run every 15 minutes
    scheduler = BlockingScheduler()
    scheduler.add_job(run_pipeline, 'interval', minutes=15)
    
    print("⏳ Scheduler active. Press Ctrl+C to stop.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass