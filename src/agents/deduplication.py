# Deduplication Agent
# This agent checks ChromaDB for semantic similarity. If the distance is extremely low (meaning the meaning is identical), it marks it as a duplicate. If it's unique, it saves the new vector to ChromaDB so future articles can be compared against it.

# src/agents/deduplication.py
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
    
    # 3. Query ChromaDB for the most similar article
    results = news_collection.query(
        query_embeddings=[embedding],
        n_results=1
    )
    
    # 4. Check if we found a match
    if results['distances'] and len(results['distances'][0]) > 0:
        distance = results['distances'][0][0]
        
        # If the distance is below our threshold, it's a duplicate
        if distance < SIMILARITY_THRESHOLD:
            state['is_duplicate'] = True
            state['canonical_id'] = results['ids'][0][0]
            print(f"❌ DUPLICATE FOUND! Matches ID: {state['canonical_id']} (Distance: {distance:.3f})")
            return state

    # 5. If it's unique, save it to the Vector DB
    state['is_duplicate'] = False
    if not state.get('article_id'):
        state['article_id'] = str(uuid.uuid4())
        
    news_collection.add(
        embeddings=[embedding],
        documents=[text_to_embed],
        metadatas=[{"source": state["source"]}],
        ids=[state['article_id']]
    )
    print(f"✅ UNIQUE ARTICLE. Saved to Vector DB with ID: {state['article_id']}")
    return state

