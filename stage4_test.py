# test_stage4.py
from src.database.sqlite_client import init_db
from src.agents.ingestion import load_mock_news
from src.graphs.ingestion_graph import ingestion_app

if __name__ == "__main__":
    print("--- Starting Full Ingestion Pipeline Test (Stage 4) ---")
    init_db()
    
    # Load data
    articles = load_mock_news()
    
    # We will process art-001 (HDFC Bank) as our test case
    # Note: Ensure you have cleared your sqlite.db and chroma_db before running to avoid conflicts
    test_article = articles[0] 
    
    print(f"\n--- Processing: {test_article['id']} ---")
    
    initial_state = {
        "article_id": test_article["id"],
        "title": test_article["title"],
        "content": test_article["content"],
        "source": test_article["source"],
        "is_duplicate": False,
        "canonical_id": None
    }
    
    # Run the full graph
    final_state = ingestion_app.invoke(initial_state)
    
    print("\n--- Final Enriched State ---")
    print(f"Companies: {final_state.get('companies')}")
    print(f"Impacted Stocks: {final_state.get('impacted_stocks')}")
    print("\n--- Stage 4 Complete ---")