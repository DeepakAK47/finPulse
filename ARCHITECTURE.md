# FinPulse Architecture

## 1. Purpose and system boundary

FinPulse is a local-first financial-news intelligence application. It
ingests market news, detects semantically similar articles, extracts entities,
maps those entities to potentially impacted symbols, and exposes the resulting
data through a Streamlit dashboard and an optional FastAPI service.

The current implementation is a development system:

- SQLite and ChromaDB persist data on the local filesystem.
- The embedding model and graph workloads run in the application process.
- Gemini is optional for query routing but is required by the current entity
  extraction node.
- Finnhub supplies live news to the scheduler and manual API trigger.
- The API and Streamlit frontend run as separate processes.
- There is no authentication, queue, multi-user isolation, or production
  deployment configuration.

## 2. Component overview

```text
                         +---------------------------+
                         | Streamlit dashboard       |
                         | frontend/app.py           |
                         +-------------+-------------+
                                       |
                   local SQLite read  |  optional HTTP calls
                   + Chroma fallback  |  to /query and
                                       |  /fetch-latest
                                       v
                         +-------------+-------------+
                         | FastAPI service           |
                         | api/main.py               |
                         +------+------+-------------+
                                |      |
                          query |      | background ingestion
                                v      v
                 +--------------+--+  +----------------------+
                 | Query LangGraph |  | Ingestion LangGraph  |
                 | router ->       |  | dedup -> extraction  |
                 | retrieval       |  | -> impact -> storage |
                 +-------+---------+  +----------+-----------+
                         |                       |
              +----------+----------+            |
              |                     |            |
              v                     v            v
       +------+-------+      +------+-------+  +--+-----------+
       | SQLite       |      | ChromaDB     |  | Gemini       |
       | article data |      | vectors      |  | extraction   |
       +--------------+      +--------------+  | and routing |
                                               +--------------+

                         +----------------------+
                         | scheduler.py         |
                         | Finnhub -> ingestion |
                         +----------------------+
```

### Main modules

| Module | Responsibility |
| --- | --- |
| [`src/agents/ingestion.py`](./src/agents/ingestion.py) | Fetch live Finnhub news |
| [`src/agents/deduplication.py`](./src/agents/deduplication.py) | Embed articles and detect duplicates |
| [`src/agents/entity_extraction.py`](./src/agents/entity_extraction.py) | Extract companies, sectors, and regulators |
| [`src/agents/impact_analysis.py`](./src/agents/impact_analysis.py) | Map entities to impacted symbols |
| [`src/agents/storage.py`](./src/agents/storage.py) | Persist enriched articles in SQLite |
| [`src/agents/query_router.py`](./src/agents/query_router.py) | Classify user queries |
| [`src/agents/querry_retrival.py`](./src/agents/querry_retrival.py) | Retrieve matching articles |
| [`src/graphs/ingestion_graph.py`](./src/graphs/ingestion_graph.py) | Compose the ingestion nodes |
| [`src/graphs/query_graph.py`](./src/graphs/query_graph.py) | Compose routing and retrieval |
| [`src/database/sqlite_client.py`](./src/database/sqlite_client.py) | SQLAlchemy engine and `NewsArticle` model |
| [`src/database/chroma_client.py`](./src/database/chroma_client.py) | Persistent ChromaDB client and collection |
| [`src/utils/embedding.py`](./src/utils/embedding.py) | Shared Sentence Transformers model |
| [`api/main.py`](./api/main.py) | FastAPI routes and background ingestion trigger |
| [`frontend/app.py`](./frontend/app.py) | Streamlit UI and local data loading |
| [`scheduler.py`](./scheduler.py) | Immediate and 15-minute recurring ingestion |

## 3. Data flow

### 3.1 Live ingestion

Live ingestion starts in either [`scheduler.py`](./scheduler.py) or the
`POST /fetch-latest` API endpoint:

```text
Finnhub
  -> fetch_real_news()
  -> article state
  -> ingestion_app.invoke()
  -> ChromaDB deduplication
  -> Gemini entity extraction
  -> rule-based impact analysis
  -> SQLite storage
```

Finnhub articles are normalized to:

```text
article_id, title, content, source,
is_duplicate, canonical_id
```

The scheduler processes all fetched articles. The API trigger intentionally
processes at most five articles per request to keep the UI request lightweight.
The API returns immediately because ingestion is registered as a FastAPI
background task.

### 3.2 Ingestion graph

The compiled graph is `ingestion_app` in
[`src/graphs/ingestion_graph.py`](./src/graphs/ingestion_graph.py):

```text
deduplication
      |
      +-- duplicate --> END
      |
      +-- unique --> extraction --> impact --> storage --> END
```

1. **Deduplication**
   - Combines title and content.
   - Generates an `all-MiniLM-L6-v2` embedding.
   - Queries the `news_articles` ChromaDB collection for one nearest result.
   - Treats cosine distance below `0.25` as a duplicate.
   - Stores unique vectors in ChromaDB before continuing.
2. **Entity extraction**
   - Sends the article to Gemini using structured Pydantic output.
   - Produces `companies`, `sectors`, and `regulators`.
3. **Impact analysis**
   - Applies local company, sector, and regulator mappings.
   - Adds symbol, confidence, and impact type.
   - Removes duplicate symbols from the result.
4. **Storage**
   - Inserts the enriched article into SQLite when its ID is not already
     present.
   - Rolls back a failed database transaction and logs the error.

Duplicate articles stop after deduplication and are not currently inserted
into SQLite. This means a vector can exist in ChromaDB without a corresponding
SQLite article record.

### 3.3 Query flow

The query graph is `query_app` in
[`src/graphs/query_graph.py`](./src/graphs/query_graph.py):

```text
POST /query
    -> QueryInput validation
    -> route_query
    -> retrieve_news
    -> response JSON
```

The router classifies the query as:

- `company`
- `sector`
- `regulator`
- `semantic`

If `GOOGLE_API_KEY` is unavailable, the router uses local keyword rules. If
Gemini routing fails, it also falls back to those local rules.

Retrieval behavior:

- **Company**: searches the SQLite JSON company field and also applies the
  current Banking-sector fallback rule.
- **Sector**: searches the SQLite JSON sector field.
- **Regulator**: searches the SQLite JSON regulator field.
- **Semantic**: embeds the query, asks ChromaDB for up to three nearest IDs,
  and hydrates matching article records from SQLite.

Semantic results require matching SQLite rows. ChromaDB provides IDs and
similarity search, while SQLite provides the article response fields.

## 4. Persistence model

### 4.1 SQLite

The database path is `data/sqlite.db`. `init_db()` creates the
`news_articles` table through SQLAlchemy.

| Column | Type | Meaning |
| --- | --- | --- |
| `id` | string | Primary article ID |
| `title` | string | Article headline |
| `content` | string | Article summary/content |
| `source` | string | News provider |
| `is_duplicate` | boolean | Duplicate decision |
| `canonical_id` | string | Matching canonical vector ID |
| `companies` | JSON | Extracted company names |
| `sectors` | JSON | Extracted sector names |
| `regulators` | JSON | Extracted regulator names |
| `impacted_stocks` | JSON | Symbol, confidence, and impact type objects |

### 4.2 ChromaDB

The persistent client in [`src/database/chroma_client.py`](./src/database/chroma_client.py)
uses `data/chroma_db/` and the `news_articles` collection with cosine distance.
Each vector record contains:

- the article ID as the ChromaDB ID;
- the title-plus-content embedding;
- the combined text document;
- source metadata;
- title and content metadata for dashboard fallback records created by newer
  ingestion runs.

ChromaDB is the semantic index. SQLite is the preferred source for complete
article and enrichment data.

### 4.3 Dashboard data loading

The dashboard's `load_articles()` function:

1. Reads and parses all SQLite `news_articles` rows.
2. Returns SQLite records when at least one exists.
3. Falls back to ChromaDB documents and metadata when SQLite is empty.
4. Derives basic company, sector, regulator, and impact tags for fallback
   records.

This fallback makes the dashboard useful when a previous run wrote vectors but
did not complete the SQLite write. It does not repair or synchronize SQLite;
future ingestion should still complete both writes.

## 5. User interfaces

### Streamlit

[`frontend/app.py`](./frontend/app.py) provides three views:

- **Dashboard**: article count, source count, company count, tracked-symbol
  count, latest coverage, source chart, and sectors.
- **News explorer**: source selection and text filtering over loaded records.
- **Search & intelligence**: local search or optional FastAPI/Gemini query
  execution.

The sidebar also provides:

- FastAPI URL configuration;
- **Fetch Latest News**, which calls `POST /fetch-latest`;
- **Refresh Dashboard**, which clears the article cache and reruns the page.

The article cache has a 30-second TTL. The refresh button clears it
immediately, which is useful after background ingestion.

### FastAPI

[`api/main.py`](./api/main.py) exposes:

| Method | Route | Behavior |
| --- | --- | --- |
| `GET` | `/health` | Returns `{"status": "ok"}` |
| `POST` | `/query` | Runs the query graph |
| `POST` | `/fetch-latest` | Starts a background ingestion task |

The API should be started with Uvicorn using `api.main:app` from the repository
root. Running `api\main.py` directly is not the supported startup path because
the application imports the top-level `src` package.

## 6. Runtime configuration

Configuration is loaded from `.env` using `python-dotenv`:

```dotenv
FINNHUB_API_KEY=your_finnhub_key
GOOGLE_API_KEY=your_google_gemini_key
```

- `FINNHUB_API_KEY` is required for live news fetching.
- `GOOGLE_API_KEY` enables Gemini routing and is required by the current
  entity-extraction node.
- The embedding model may download on first use and therefore requires
  internet access initially.

The required Python packages are declared in [`requirements.txt`](./requirements.txt).

## 7. Operational flows

### Start the complete local stack

From the repository root, use separate terminals:

```powershell
.\python3.11\Scripts\uvicorn.exe api.main:app --reload
.\python3.11\Scripts\streamlit.exe run frontend\app.py
.\python3.11\Scripts\python.exe scheduler.py
```

The scheduler is optional if only existing data needs to be viewed. It is
needed to fetch new live articles automatically. The API and dashboard can run
without the scheduler.

### Fetch from the dashboard

1. Start Uvicorn.
2. Start Streamlit.
3. Click **Fetch Latest News** in the sidebar.
4. Wait for the background task to finish.
5. Click **Refresh Dashboard**.

### Stage and smoke tests

The root scripts exercise individual stages:

```powershell
.\python3.11\Scripts\python.exe test_stage1.py
.\python3.11\Scripts\python.exe test_stage2.py
.\python3.11\Scripts\python.exe stage4_test.py
```

These scripts can modify local SQLite and ChromaDB state. Re-running a script
with IDs that already exist in ChromaDB may produce duplicate-ID errors.

## 8. Failure modes and consistency boundaries

### ChromaDB contains data but SQLite is empty

This can happen because deduplication writes the unique vector before the
extraction and SQLite storage nodes run. The dashboard displays ChromaDB
fallback records, but API semantic retrieval cannot hydrate complete results
until matching SQLite records exist.

### Duplicate article

A vector distance below `0.25` ends the ingestion graph early. The duplicate
article is not stored as a separate SQLite record.

### Missing Finnhub key

`fetch_real_news()` raises an error when `FINNHUB_API_KEY` is missing. Configure
`.env` before starting the scheduler or using `/fetch-latest`.

### Gemini unavailable

Query routing falls back to local rules when Gemini is unavailable. The
current entity-extraction implementation does not have the same fallback, so
live ingestion may fail at extraction without `GOOGLE_API_KEY`.

### API unavailable

The Streamlit search page reports the API error and falls back to local
article search. Dashboard and explorer pages continue to work from local
storage.

## 9. Security and deployment boundaries

The application is intended for local development:

- no authentication or authorization;
- no request throttling;
- API keys must remain in `.env`;
- SQLite and ChromaDB are local files;
- logs may contain article titles and processing errors;
- external calls do not yet have a unified retry, tracing, or circuit-breaker
  policy.

Before exposing the API beyond localhost, add authentication, input limits,
structured logging, secret management, isolation for database files, and
controlled network access.

## 10. Evolution roadmap

1. Make ingestion writes durable and coordinated across ChromaDB and SQLite.
2. Persist duplicate records and canonical relationships consistently.
3. Add a dedicated ingestion service/queue for long-running jobs.
4. Add robust retry, timeout, rate-limit, and observability policies.
5. Replace JSON substring searches with indexed entity tables or a search
   index.
6. Generalize company-to-sector and symbol mappings through a maintained
   instrument catalog.
7. Add integration tests for both stores, Gemini failure paths, API routes,
   background ingestion, and dashboard refresh behavior.
8. Add authentication and deployment-specific configuration before production
   use.
