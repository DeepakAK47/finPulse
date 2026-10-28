# test stage1
from src.database.sqlite_client import init_db
from src.database.chroma_client import news_collection
from src.utils.embedding import get_embedding
from src.agents.ingestion import load_mock_news

if __name__ == "__main__":
    print("--- Starting Stage 1 Test ---")
    
    # 1. Initialize SQLite
    init_db()
    
    # 2. Load Data
    articles = load_mock_news()
    
    # 3. Test Embedding Generation on the first article
    if articles:
        first_article = articles[0]
        text_to_embed = f"{first_article['title']} {first_article['content']}"
        
        print("\nTesting embedding generation...")
        vector = get_embedding(text_to_embed)
        print(f"✅ Generated vector of size: {len(vector)} dimensions")
        
        # 4. Test ChromaDB insertion (Temporary test)
        print("\nTesting ChromaDB insertion...")
        news_collection.add(
            embeddings=[vector],
            documents=[text_to_embed],
            metadatas=[{"source": first_article["source"]}],
            ids=[first_article["id"]]
        )
        print("✅ Article successfully saved to ChromaDB!")
        
    print("\n--- Stage 1 Complete ---")

