# src/agents/storage.py
from src.schemas.state import NewsState
from src.database.sqlite_client import SessionLocal, NewsArticle

def store_article(state: NewsState) -> NewsState:
    print(f"\n💾 Saving article to SQLite: '{state['title']}'")
    
    db = SessionLocal()
    try:
        # Check if it already exists (safety check)
        existing = db.query(NewsArticle).filter(NewsArticle.id == state['article_id']).first()
        
        if not existing:
            new_article = NewsArticle(
                id=state['article_id'],
                title=state['title'],
                content=state['content'],
                source=state['source'],
                is_duplicate=state.get('is_duplicate', False),
                canonical_id=state.get('canonical_id'),
                companies=state.get('companies', []),
                sectors=state.get('sectors', []),
                regulators=state.get('regulators', []),
                impacted_stocks=state.get('impacted_stocks', [])
            )
            db.add(new_article)
            db.commit()
            print("✅ Article successfully saved to SQLite database.")
        else:
            print("⚠️ Article already exists in database. Skipping save.")
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        db.rollback()
    finally:
        db.close()
        
    return state