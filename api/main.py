# api/main.py
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
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


@app.get("/articles")
def list_articles():
    """Return stored articles for the Streamlit frontend."""
    init_db()
    from src.database.sqlite_client import SessionLocal, NewsArticle

    db = SessionLocal()
    try:
        articles = db.query(NewsArticle).order_by(NewsArticle.id.desc()).all()
        return [
            {
                "id": article.id,
                "title": article.title,
                "content": article.content,
                "source": article.source,
                "is_duplicate": article.is_duplicate,
                "canonical_id": article.canonical_id,
                "companies": article.companies or [],
                "sectors": article.sectors or [],
                "regulators": article.regulators or [],
                "impacted_stocks": article.impacted_stocks or [],
            }
            for article in articles
        ]
    finally:
        db.close()


@app.post("/query")
def query_news(payload: QueryInput):
    initial_state = {"query": payload.query}
    result = query_app.invoke(initial_state)
    return {
        "query": payload.query,
        "query_type": result.get("query_type"),
        "results": result.get("results")
    }


@app.post("/fetch-latest")
def fetch_latest_news():
    """Fetch and store the latest articles, returning the processing result."""
    init_db()
    articles = fetch_real_news()[:5]
    processed = 0
    errors = []

    for article in articles:
        initial_state = {
            "article_id": article["id"],
            "title": article["title"],
            "content": article["content"],
            "source": article["source"],
            "is_duplicate": False,
            "canonical_id": None,
        }
        try:
            result = ingestion_app.invoke(initial_state)
            if not result.get("is_duplicate"):
                processed += 1
            print(
                f"Processed: {article['title'][:50]}... | "
                f"Duplicate: {result.get('is_duplicate')}"
            )
        except Exception as error:
            print(f"Error processing article: {error}")
            errors.append(str(error))

    return {
        "status": "success" if not errors else "partial",
        "fetched": len(articles),
        "processed": processed,
        "errors": errors,
    }
