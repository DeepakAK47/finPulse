# test_stage2.py
from src.database.sqlite_client import init_db
from src.agents.ingestion import load_mock_news
from src.graphs.ingestion_graph import ingestion_app

if __name__ == "__main__":
    print("--- Starting Stage 2 Test ---")
    init_db()
    
    # Load the 6 mock articles
    articles = load_mock_news()
    
    # We are going to process articles 1, 2, and 5.
    # Article 5 is a semantic duplicate of Article 2.
    test_articles = [articles[0], articles[1], articles[4]]
    
    for article in test_articles:
        print(f"\n--- Processing: {article['id']} ---")
        
        # Initialize the State for LangGraph
        initial_state = {
            "article_id": article["id"],
            "title": article["title"],
            "content": article["content"],
            "source": article["source"],
            "is_duplicate": False,
            "canonical_id": None
        }
        
        # Run the graph
        result = ingestion_app.invoke(initial_state)
        
        if result.get("is_duplicate"):
            print(f"Final Result: DUPLICATE (Linked to {result['canonical_id']})")
        else:
            print(f"Final Result: UNIQUE (ID: {result['article_id']})")

    print("\n--- Stage 2 Complete ---")