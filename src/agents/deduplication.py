# Deduplication Agent
# This agent checks ChromaDB for semantic similarity. If the distance is extremely low (meaning the meaning is identical), it marks it as a duplicate. If it's unique, it saves the new vector to ChromaDB so future articles can be compared against it.

import uuid
from src.database.chroma_client import news_collection
from src.utils.embedding import get_embedding
from src.schemas.state import NewsState

# Cosine distance threshold. 
# 0.0 is identical, 1.0 is completely different. 
# We use 0.25 to catch re-worded articles (like our art-002 and art-005).
SIMILARITY_THRESHOLD = 0.25 

def deduplicate_news(state: NewsState) -> NewsState:
    print(f"\n🔍 Checking for duplicates: '{state['title']}'")
    
    # 1. Combine title and content for richer embedding
    text_to_embed = f"{state['title']} {state['content']}"
    
    # 2. Generate the vector
    embedding = get_embedding(text_to_embed)

    # Embeddings are optional for ingestion. SQLite should still receive
    # articles when Gemini is unavailable or rate-limited.
    if embedding:
        try:
            collection_count = news_collection.count()
            if collection_count:
                results = news_collection.query(
                    query_embeddings=[embedding],
                    n_results=1,
                )

                distances = results.get("distances") or []
                ids = results.get("ids") or []
                if distances and distances[0] and ids and ids[0]:
                    distance = distances[0][0]
                    if distance < SIMILARITY_THRESHOLD:
                        state["is_duplicate"] = True
                        state["canonical_id"] = ids[0][0]
                        print(
                            f"Duplicate found: {state['canonical_id']} "
                            f"(Distance: {distance:.3f})"
                        )
                        return state
        except Exception as error:
            print(f"Vector duplicate check unavailable; using SQLite: {error}")
            embedding = None

    # 5. If it's unique, save it to the Vector DB
    state['is_duplicate'] = False
    if not state.get('article_id'):
        state['article_id'] = str(uuid.uuid4())
        
    if embedding:
        try:
            news_collection.add(
                embeddings=[embedding],
                documents=[text_to_embed],
                metadatas=[
                    {
                        "source": state["source"],
                        "title": state["title"],
                        "content": state["content"],
                    }
                ],
                ids=[state["article_id"]],
            )
            print(f"Unique article saved to vector database: {state['article_id']}")
        except Exception as error:
            print(f"Vector storage unavailable; using SQLite: {error}")
    else:
        print("Unique article will be stored in SQLite without vector search.")
    return state
