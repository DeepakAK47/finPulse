# this agent is responsible for actual data search based on router classification
from src.schemas.query_state import QueryState
from src.database.sqlite_client import SessionLocal, NewsArticle
from src.database.chroma_client import news_collection
from src.utils.embedding import get_embedding
import json

def retrieve_news(state: QueryState) -> QueryState:
    print(f"🔎 Retrieving data for type: {state['query_type']}")
    db = SessionLocal()
    results = []
    
    try:
        q_type = state['query_type']
        entity = state['extracted_entity']
        
        if q_type == "company":
            # 1. Direct match
            direct_matches = db.query(NewsArticle).filter(NewsArticle.companies.contains(entity)).all()
            # 2. Sector match (find sectors for this company, then get news for that sector)
            # For simplicity in this demo, we'll just fetch banking sector news if HDFC is asked
            sector_matches = db.query(NewsArticle).filter(NewsArticle.sectors.contains("Banking")).all()
            
            # Combine and deduplicate
            all_matches = {art.id: art for art in direct_matches + sector_matches}.values()
            results = [{"title": art.title, "content": art.content, "impact": art.impacted_stocks, "reason": "Direct + Sector Match"} for art in all_matches]

        elif q_type == "sector":
            sector_matches = db.query(NewsArticle).filter(NewsArticle.sectors.contains(entity)).all()
            results = [{"title": art.title, "content": art.content, "impact": art.impacted_stocks, "reason": "Sector Match"} for art in sector_matches]

        elif q_type == "regulator":
            reg_matches = db.query(NewsArticle).filter(NewsArticle.regulators.contains(entity)).all()
            results = [{"title": art.title, "content": art.content, "impact": art.impacted_stocks, "reason": "Regulator Match"} for art in reg_matches]

        elif q_type == "semantic":
            # Use ChromaDB for semantic search
            embedding = get_embedding(state['query'])
            chroma_res = news_collection.query(query_embeddings=[embedding], n_results=3)
            
            if chroma_res['ids'] and len(chroma_res['ids'][0]) > 0:
                ids = chroma_res['ids'][0]
                for art_id in ids:
                    art = db.query(NewsArticle).filter(NewsArticle.id == art_id).first()
                    if art:
                        results.append({"title": art.title, "content": art.content, "impact": art.impacted_stocks, "reason": "Semantic Match"})
                        
    finally:
        db.close()
        
    state['results'] = results
    print(f"✅ Found {len(results)} relevant articles.")
    return state