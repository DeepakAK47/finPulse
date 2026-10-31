# finPulse Architecture

## 1. System overview

finPulse is a local financial-news intelligence application. It accepts news
articles for enrichment and exposes natural-language search over the enriched
articles.

The current implementation is a development/demo system rather than a
production service:

- SQLite and ChromaDB persist state on the local filesystem.
- The embedding model is loaded in-process.
- Gemini is used for structured entity extraction and query classification.
- The API and Streamlit frontend are separate processes.
- There is no authentication, background queue, scheduler, or external news
  ingestion adapter yet.

The main runtime components are:

```text
                         +----------------------+
                         |  Streamlit frontend  |
                         |    frontend/app.py   |
                         +----------+-----------+
                                    |
                              POST /query
                                    |
                         +----------v-----------+
                         |    FastAPI service   |
                         |      api/main.py     |
                         +----------+-----------+
                                    |
                         +----------v-----------+
                         |   Query LangGraph    |
                         | router -> retrieval |
                         +-----+----------+-----+
                               |          |
                       structured LLM    |
                               |          |
                  +------------v--+   +--v-------------+
                  | Gemini Flash  |   | SQLite metadata |
                  | query routing |   | article records |
                  +---------------+   +----------------+
                                             ^
                                             |
                  +--------------------------+--------------------------+
                  |                                                     |
          +-------+--------+                                   +--------+-------+
          | Ingestion flow |                                   | ChromaDB       |
          | dedup ->       |---- embeddings ------------------>| vector store   |
          | extraction ->  |                                   | semantic query |
          | impact -> save |                                   +----------------+
          +----------------+
```

## 2. Source layout and responsibilities

| Area | Responsibility |
| --- | --- |
| [`src/agents/`](./src/agents/) | Individual ingestion and query-processing steps |
| [`src/graphs/`](./src/graphs/) | LangGraph state machines that compose the agents |
| [`src/schemas/`](./src/schemas/) | Typed state passed between graph nodes |
| [`src/database/`](./src/database/) | SQLite ORM setup and persistent ChromaDB collection |
| [`src/utils/embedding.py`](./src/utils/embedding.py) | Shared `all-MiniLM-L6-v2` embedding model |
| [`api/main.py`](./api/main.py) | FastAPI application and `POST /query` endpoint |
| [`frontend/app.py`](./frontend/app.py) | Streamlit user interface |
| [`data/mock_news.json`](./data/mock_news.json) | Local sample article input |
| [`tests/`](./tests/) and root test scripts | Smoke tests, stage checks, and benchmark code |

`api/routes.py` exists as a reserved module but is not currently wired into the
FastAPI application. The active endpoint is defined in `api/main.py`.

## 3. Ingestion architecture

### 3.1 Input

[`load_mock_news`](./src/agents/ingestion.py) reads
[`data/mock_news.json`](./data/mock_news.json) and assigns a UUID if an input
article does not already have an `id`. The sample data supplies stable IDs such
as `art-001`.

The ingestion graph expects a `NewsState` containing:

- `article_id`
- `title`
- `content`
- `source`
- deduplication fields (`is_duplicate`, `canonical_id`)
- enrichment fields (`companies`, `sectors`, `regulators`, `impacted_stocks`)

### 3.2 LangGraph workflow

The compiled graph is [`ingestion_app`](./src/graphs/ingestion_graph.py):

```text
deduplication
      |
      +-- duplicate --> END
      |
      +-- unique -----> extraction -> impact -> storage -> END
```

1. **Deduplication** — [`deduplicate_news`](./src/agents/deduplication.py)
   concatenates the title and content, creates an embedding, and queries the
   `news_articles` ChromaDB collection. A cosine distance below `0.25` marks
   the article as a duplicate and records the matching canonical ID. Unique
   articles are added to ChromaDB.
2. **Entity extraction** — [`extract_entities`](./src/agents/entity_extraction.py)
   sends the article to Gemini with a Pydantic structured-output schema and
   populates companies, sectors, and regulators.
3. **Impact analysis** — [`analyze_impact`](./src/agents/impact_analysis.py)
   applies local company, sector, and regulator-to-ticker mappings. It
   de-duplicates ticker symbols and attaches a confidence and impact type.
4. **Storage** — [`store_article`](./src/agents/storage.py) writes the enriched
   article to SQLite unless the article ID already exists.

Duplicate articles stop after the vector lookup. They are not written to the
SQLite article table by the current graph.

## 4. Query architecture

### 4.1 Request path

The Streamlit app sends the user's text to `http://127.0.0.1:8000/query`.
FastAPI validates the body using `QueryInput`, invokes the compiled
[`query_app`](./src/graphs/query_graph.py), and returns the original query,
the detected query type, and result records.

The query state contains:

- `query`: original natural-language query
- `query_type`: `company`, `sector`, `regulator`, or `semantic`
- `extracted_entity`: entity selected by the classifier, or `None` for semantic
  queries
- `results`: retrieved article summaries

### 4.2 LangGraph workflow

```text
router -> retrieval -> END
```

1. **Router** — [`route_query`](./src/agents/query_router.py) uses Gemini
   structured output to classify the query and extract an entity.
2. **Retrieval** — [`retrieve_news`](./src/agents/querry_retrival.py) uses
   SQLite JSON-column filters for company, sector, and regulator searches.
   Semantic searches embed the query, retrieve up to three IDs from ChromaDB,
   and hydrate the matching article records from SQLite.

Company retrieval currently also includes articles tagged with the Banking
sector. This is a demo rule, not a general company-to-sector knowledge model.

## 5. Persistence and data model

### SQLite

[`NewsArticle`](./src/database/sqlite_client.py) is stored in the
`news_articles` table in `data/sqlite.db`:

| Column | Purpose |
| --- | --- |
| `id` | Primary article ID |
| `title`, `content`, `source` | Original article data |
| `is_duplicate` | Duplicate decision |
| `canonical_id` | ID of the matching canonical article |
| `companies`, `sectors`, `regulators` | JSON arrays from entity extraction |
| `impacted_stocks` | JSON array of ticker, confidence, and type objects |

`init_db()` creates the table if it does not exist. SQLAlchemy sessions are
created through `SessionLocal`, and `get_db()` provides a FastAPI-compatible
session generator for future route extraction.

### ChromaDB

[`chroma_client.py`](./src/database/chroma_client.py) creates a persistent
ChromaDB client under `data/chroma_db/` and gets or creates the
`news_articles` collection with cosine distance. The collection stores:

- the embedding generated from title plus content,
- the combined text as the document,
- the source as metadata,
- the article ID as the vector ID.

SQLite is the source of the displayed article and enrichment fields; ChromaDB
is the similarity index and stores the searchable text/vector representation.

## 6. External services and configuration

The embedding model is loaded globally by
[`get_embedding`](./src/utils/embedding.py), which avoids loading a second model
for every request. The first use may download `all-MiniLM-L6-v2`.

Gemini clients in the extraction and routing agents read `GOOGLE_API_KEY` from
the environment through `python-dotenv`. The key must be supplied through local
environment configuration such as `.env`; it must not be committed.

The repository currently has no populated dependency manifest. The runtime
requires the packages used by the implementation, including FastAPI,
Streamlit, SQLAlchemy, ChromaDB, Sentence Transformers, LangGraph,
LangChain Google GenAI integration, Pydantic, `python-dotenv`, and `requests`.

## 7. Running the local system

Initialize and exercise the implemented ingestion stages from the repository
root:

```powershell
python test_stage1.py
python test_stage2.py
python stage4_test.py
```

Start the API with Uvicorn, then start Streamlit in a second terminal:

```powershell
uvicorn api.main:app --reload
streamlit run frontend/app.py
```

The frontend assumes the API is available at `127.0.0.1:8000`. The local
database and vector store are created beneath `data/`.

## 8. Reliability and operational boundaries

The current design has several intentional development-stage limitations:

- Database writes and graph nodes log errors to stdout; production operation
  should replace this with structured logging and explicit error responses.
- The ingestion loader is file-based and synchronous.
- External LLM and embedding calls have no retry, timeout, or rate-limit
  policy in this codebase.
- ChromaDB and SQLite are local single-process persistence choices.
- The API has no authentication or request throttling.
- JSON substring filtering is convenient for the demo but is not a robust
  indexed entity-search strategy.
- Re-running the stage scripts with existing ChromaDB IDs can produce duplicate
  ID errors.

These constraints should be addressed before exposing the service to
untrusted users or production workloads.

## 9. Testing strategy

The root stage scripts are executable smoke tests for initialization, embedding,
vector insertion, deduplication, and the complete ingestion graph. The tests in
[`tests/`](./tests/) cover the implemented agent behavior where applicable.
[`benchmark.py`](./benchmark.py) measures duplicate detection, extraction
latency, and impact mapping against representative sample inputs.

When changing a graph state or persistence schema, update the corresponding
state definition, graph test, and this document together.

## 10. Planned evolution

The next architectural improvements are:

1. Move API handlers into `api/routes.py` and add a dedicated ingestion
   endpoint.
2. Populate and pin `requirements.txt`.
3. Add a real news-source adapter and an idempotent ingestion job.
4. Separate duplicate handling from vector insertion so canonical links and
   duplicate records can be persisted consistently.
5. Replace hard-coded impact mappings with a maintained instrument/entity
   catalog.
6. Add request validation, structured logging, retries, health checks, and
   authentication.
7. Add integration tests for SQLite, ChromaDB, Gemini failure paths, and the
   Streamlit/FastAPI boundary.