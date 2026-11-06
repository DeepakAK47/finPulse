"""FinPulse Streamlit application.

The dashboard reads the local SQLite store directly, so it remains useful when
the optional FastAPI/Gemini services are not running.
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "sqlite.db"
MOCK_NEWS_PATH = DATA_DIR / "mock_news.json"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.database.chroma_client import news_collection

COMPANY_TICKERS = {
    "HDFC Bank": "HDFCBANK",
    "ICICI Bank": "ICICIBANK",
    "Tata Motors": "TATAMOTORS",
}
SECTOR_TICKERS = {
    "Banking": ["HDFCBANK", "ICICIBANK", "SBIN"],
    "Automobile": ["TATAMOTORS", "M&M", "MARUTI"],
    "Financial Services": ["HDFCBANK", "ICICIBANK", "BAJFINANCE"],
}


def _json_value(value: Any, default: Any) -> Any:
    if value in (None, "", "null"):
        return default
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def _enrich_article(article: dict[str, Any]) -> dict[str, Any]:
    text = f"{article.get('title', '')} {article.get('content', '')}".lower()
    companies = [
        company for company in COMPANY_TICKERS if company.lower() in text
    ]
    sectors: list[str] = []
    if any(term in text for term in ("bank", "repo rate", "npa", "credit growth")):
        sectors.append("Banking")
    if any(term in text for term in ("car", "automobile", "ev sales", "motor")):
        sectors.append("Automobile")
    regulators = ["RBI"] if "rbi" in text or "reserve bank" in text else []
    
    impacted: list[dict[str, Any]] = []
    seen: set[str] = set()
    
    for company in companies:
        symbol = COMPANY_TICKERS[company]
        impacted.append({"symbol": symbol, "confidence": 1.0, "type": "direct"})
        seen.add(symbol)
        
    for sector in sectors:
        for symbol in SECTOR_TICKERS.get(sector, []):
            if symbol not in seen:
                impacted.append({"symbol": symbol, "confidence": 0.7, "type": "sector"})
                seen.add(symbol)
                
    if regulators and "BANKNIFTY" not in seen:
        impacted.append({"symbol": "BANKNIFTY", "confidence": 0.8, "type": "regulatory"})
        
    article.update(
        companies=companies,
        sectors=sectors,
        regulators=regulators,
        impacted_stocks=impacted,
        is_duplicate=False,
    )
    return article


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS news_articles (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, content TEXT NOT NULL,
            source TEXT NOT NULL, is_duplicate INTEGER DEFAULT 0,
            canonical_id TEXT, companies TEXT, sectors TEXT,
            regulators TEXT, impacted_stocks TEXT
        )
        """
    )
    connection.commit()
    return connection


def seed_sample_data() -> int:
    with MOCK_NEWS_PATH.open(encoding="utf-8") as file:
        articles = [_enrich_article(item) for item in json.load(file)]
    connection = _connect()
    try:
        for article in articles:
            connection.execute(
                """
                INSERT INTO news_articles
                    (id, title, content, source, is_duplicate, canonical_id,
                     companies, sectors, regulators, impacted_stocks)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title, content=excluded.content,
                    source=excluded.source,
                    companies=COALESCE(NULLIF(news_articles.companies, '[]'),
                                       excluded.companies),
                    sectors=COALESCE(NULLIF(news_articles.sectors, '[]'),
                                     excluded.sectors),
                    regulators=COALESCE(NULLIF(news_articles.regulators, '[]'),
                                        excluded.regulators),
                    impacted_stocks=COALESCE(
                        NULLIF(news_articles.impacted_stocks, '[]'),
                        excluded.impacted_stocks)
                """,
                (
                    article["id"],
                    article["title"],
                    article["content"],
                    article.get("source", "Unknown"),
                    int(article.get("is_duplicate", False)),
                    article.get("canonical_id"),
                    json.dumps(article["companies"]),
                    json.dumps(article["sectors"]),
                    json.dumps(article["regulators"]),
                    json.dumps(article["impacted_stocks"]),
                ),
            )
        connection.commit()
    finally:
        connection.close()
    return len(articles)


def _load_chroma_articles() -> list[dict[str, Any]]:
    stored = news_collection.get(include=["documents", "metadatas"])
    documents = stored.get("documents") or []
    metadatas = stored.get("metadatas") or []
    ids = stored.get("ids") or []
    articles: list[dict[str, Any]] = []

    for index, document in enumerate(documents):
        if not document:
            continue
        metadata = metadatas[index] if index < len(metadatas) else {}
        metadata = metadata or {}
        articles.append(
            _enrich_article(
                {
                    "id": ids[index] if index < len(ids) else f"chroma-{index}",
                    "title": metadata.get("title") or document[:120],
                    "content": metadata.get("content") or document,
                    "source": metadata.get("source") or "ChromaDB",
                }
            )
        )
    return articles


@st.cache_data(ttl=30)
def load_articles() -> list[dict[str, Any]]:
    connection = _connect()
    try:
        rows = connection.execute(
            "SELECT * FROM news_articles ORDER BY rowid DESC"
        ).fetchall()
    finally:
        connection.close()
    articles = []
    for row in rows:
        article = dict(row)
        for field in ("companies", "sectors", "regulators", "impacted_stocks"):
            article[field] = _json_value(article[field], [])
        articles.append(article)
    if articles:
        return articles

    # Ingestion writes vectors before the enriched SQLite record. Keep the
    # dashboard useful when that second write has not completed yet.
    return _load_chroma_articles()


def classify_query(query: str) -> tuple[str, str | None]:
    lowered = query.lower()
    for company in COMPANY_TICKERS:
        if company.lower() in lowered:
            return "company", company
    for sector in (*SECTOR_TICKERS.keys(), "automotive"):
        if sector.lower() in lowered:
            return "sector", "Automobile" if sector == "automotive" else sector
    if "rbi" in lowered or "reserve bank" in lowered or "regulator" in lowered:
        return "regulator", "RBI"
    return "semantic", None


def search_articles(articles: list[dict[str, Any]], query: str) -> tuple[str, str | None, list[dict[str, Any]]]:
    query_type, entity = classify_query(query)
    terms = [term for term in re.findall(r"[a-z0-9]+", query.lower()) if len(term) > 2]
    matches = []
    for article in articles:
        searchable = " ".join(
            [
                article["title"],
                article["content"],
                article["source"],
                *article["companies"],
                *article["sectors"],
                *article["regulators"],
            ]
        ).lower()
        if entity and entity.lower() in searchable:
            score = 100
        else:
            score = sum(term in searchable for term in terms)
        if score:
            result = dict(article)
            result["reason"] = (
                f"{query_type.title()} match" if entity else "Keyword relevance match"
            )
            result["_score"] = score
            matches.append(result)
    matches.sort(key=lambda item: item["_score"], reverse=True)
    return query_type, entity, matches


def render_article(article: dict[str, Any], expanded: bool = False) -> None:
    impact = article.get("impacted_stocks", [])
    with st.expander(f"{article['title']}  ·  {article['source']}", expanded=expanded):
        st.write(article["content"])
        tags = article.get("companies", []) + article.get("sectors", []) + article.get("regulators", [])
        if tags:
            st.markdown(" ".join(f"`{tag}`" for tag in tags))
        if impact:
            st.markdown("**Potential market impact**")
            st.dataframe(
                pd.DataFrame(impact),
                hide_index=True,
                use_container_width=True,
                column_config={
                    "confidence": st.column_config.ProgressColumn(
                        "Confidence", min_value=0, max_value=1, format="%.1f"
                    )
                },
            )


def dashboard_page(articles: list[dict[str, Any]]) -> None:
    st.title("Market intelligence at a glance")
    st.caption("Local-first financial news analysis powered by the FinPulse data store.")
    sectors = sorted({sector for article in articles for sector in article["sectors"]})
    companies = sorted({company for article in articles for company in article["companies"]})
    impact_symbols = sorted(
        {item["symbol"] for article in articles for item in article["impacted_stocks"]}
    )
    metrics = st.columns(4)
    metrics[0].metric("Articles", len(articles))
    metrics[1].metric("Sources", len({article["source"] for article in articles}))
    metrics[2].metric("Companies", len(companies))
    metrics[3].metric("Tracked symbols", len(impact_symbols))
    st.divider()
    left, right = st.columns((1.15, 1))
    with left:
        st.subheader("Latest coverage")
        for article in articles[:5]:
            render_article(article)
    with right:
        st.subheader("Coverage by source")
        source_counts = pd.Series([article["source"] for article in articles]).value_counts()
        st.bar_chart(source_counts)
        st.subheader("Tracked sectors")
        st.write(", ".join(sectors) if sectors else "No sector tags yet.")


def explorer_page(articles: list[dict[str, Any]]) -> None:
    st.title("News explorer")
    st.caption("Filter and inspect every article currently stored in SQLite.")
    sources = sorted({article["source"] for article in articles})
    selected_sources = st.multiselect("Sources", sources, default=sources)
    text = st.text_input("Filter articles", placeholder="Search title, content, company, sector...")
    filtered = [
        article for article in articles
        if article["source"] in selected_sources
        and (not text or text.lower() in json.dumps(article).lower())
    ]
    st.info(f"Showing {len(filtered)} of {len(articles)} articles")
    for article in filtered:
        render_article(article)


def intelligence_page(articles: list[dict[str, Any]], api_url: str) -> None:
    st.title("Search & intelligence")
    st.caption("Ask the AI multi-agent system about the market.")
    
    query = st.text_input("Ask about the market", placeholder="e.g. HDFC Bank, RBI policy, banking sector")
    use_api = st.checkbox("Use FastAPI/Gemini when available", value=True)
    
    if st.button("Analyze query", type="primary", disabled=not query):
        query_type = entity = None
        results: list[dict[str, Any]]
        
        if use_api:
            with st.spinner("LangGraph agents are analyzing your query..."):
                try:
                    response = requests.post(f"{api_url.rstrip('/')}/query", json={"query": query}, timeout=30)
                    response.raise_for_status()
                    payload = response.json()
                    query_type = payload.get("query_type")
                    entity = payload.get("extracted_entity")
                    results = payload.get("results", [])
                except requests.RequestException as error:
                    st.error(f"🚨 FastAPI backend is offline ({error}). Falling back to basic local search.")
                    query_type, entity, results = search_articles(articles, query)
        else:
            query_type, entity, results = search_articles(articles, query)
            
        st.success(f"🧠 AI Intent Classified: **{(query_type or 'unknown').title()}**" + (f" · Entity: **{entity}**" if entity else ""))
        
        if not results:
            st.warning("No matching articles found.")
            
        for article in results:
            render_article(article, expanded=True)


def main() -> None:
    st.set_page_config(page_title="FinPulse Intelligence", page_icon="📈", layout="wide")
    st.markdown(
        """
        <style>
        .block-container {max-width: 1400px; padding-top: 2rem;}
        [data-testid="stMetric"] {background: linear-gradient(135deg,#102a43,#176b87);
          padding: 1rem; border-radius: .75rem; color: white;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.title("📈 FinPulse")
    st.sidebar.caption("Financial news intelligence")
    api_url = st.sidebar.text_input("FastAPI URL", "https://finpulse-a0tg.onrender.com")
    
    st.sidebar.divider()
    
    # --- NEW: Fetch Latest News Button ---
    if st.sidebar.button("📡 Fetch Latest News", use_container_width=True):
        with st.sidebar.spinner("Triggering backend pipeline..."):
            try:
                response = requests.post(f"{api_url.rstrip('/')}/fetch-latest", timeout=10)
                if response.status_code == 200:
                    st.sidebar.success("Fetch started! Wait 15s, then click Refresh.")
                else:
                    st.sidebar.error(f"Backend error: {response.status_code}")
            except requests.exceptions.ConnectionError:
                st.sidebar.error("Backend offline. Is Uvicorn running?")
                
    # --- NEW: Refresh Dashboard Button ---
    if st.sidebar.button("↻ Refresh Dashboard", use_container_width=True):
        load_articles.clear() # Clears the cache
        st.rerun()            # Force Streamlit to re-read the SQLite DB

    articles = load_articles()
    
    page = st.sidebar.radio("Navigate", ["Dashboard", "News explorer", "Search & intelligence"])
    if page == "Dashboard":
        dashboard_page(articles)
    elif page == "News explorer":
        explorer_page(articles)
    else:
        intelligence_page(articles, api_url)
        
    st.sidebar.divider()
    st.sidebar.caption(f"SQLite: {DB_PATH.name} · {len(articles)} articles")


if __name__ == "__main__":
    main()