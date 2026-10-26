# finPulse

finPulse is a financial-news intelligence project for ingesting market news,
storing it locally, generating semantic embeddings, and preparing the data for
downstream analysis.

## Current status

The repository is currently at **Stage 1**. The implemented workflow:

1. Initializes a local SQLite database.
2. Loads the sample articles in [`data/mock_news.json`](./data/mock_news.json).
3. Generates an embedding for the first article with
   `all-MiniLM-L6-v2`.
4. Stores that embedding in the persistent ChromaDB collection
   `news_articles`.

The FastAPI entry point, Streamlit frontend, LangGraph workflows, and
deduplication, entity-extraction, impact-analysis, and query-routing modules
are present as project structure but are not implemented yet.

## Architecture

```text
mock_news.json
      |
      v
  ingestion agent
      |
      +--> SQLite (article metadata and analysis fields)
      |
      +--> Sentence Transformer --> ChromaDB (semantic vectors)
```

### Repository layout

```text
finPulse/
├── api/                    # Reserved for the FastAPI service
├── data/
│   ├── mock_news.json      # Local sample news dataset
│   ├── sqlite.db           # SQLite database created by the Stage 1 test
│   └── chroma_db/         # Persistent ChromaDB data
├── frontend/               # Reserved for the Streamlit dashboard
├── src/
│   ├── agents/             # Ingestion and planned processing agents
│   ├── database/           # SQLite and ChromaDB setup
│   ├── graphs/             # Reserved for ingestion/query workflows
│   ├── schemas/            # Shared state definitions
│   └── utils/              # Embedding utilities
├── tests/                  # Tests to be added as modules are implemented
├── test_stage1.py          # End-to-end Stage 1 smoke test
├── ARCHITECTURE.md         # Architecture notes
└── requirements.txt        # Dependency manifest (currently empty)
```

## Prerequisites

- Python 3.11 or newer
- Git
- A Python environment with the packages used by the Stage 1 workflow:
  `chromadb`, `sentence-transformers`, and `sqlalchemy`

The dependency manifest is not populated yet. Until it is updated, install the
Stage 1 dependencies directly:

```powershell
python -m pip install chromadb sentence-transformers sqlalchemy
```

The first embedding run may download the `all-MiniLM-L6-v2` model. Internet
access is therefore required the first time `src/utils/embedding.py` is used.

## Setup

From the repository root, create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install chromadb sentence-transformers sqlalchemy
```

## Run the Stage 1 workflow

```powershell
python test_stage1.py
```

On success, the script initializes `data/sqlite.db`, loads the six sample
articles, generates a 384-dimensional embedding, and writes the first article
to the `news_articles` ChromaDB collection under `data/chroma_db/`.

The script is intentionally a smoke test rather than a production ingestion
command. Running it repeatedly with the same sample IDs can cause ChromaDB to
reject duplicate IDs.

## Testing

Run the available Python tests with:

```powershell
python -m pytest
```

The current test modules are placeholders. `test_stage1.py` is the executable
validation path for the implemented functionality.

## Local data and secrets

SQLite and ChromaDB state are stored under `data/` for local development.
These files can be regenerated and should not be treated as portable
production data. Do not commit credentials, API keys, model tokens, or other
secrets. Keep local environment values in `.env`.

## Roadmap

- Populate and maintain `requirements.txt`.
- Complete the ingestion graph and persist complete article records.
- Implement deduplication and entity extraction.
- Add impact analysis and natural-language query routing.
- Expose the workflows through FastAPI.
- Build the Streamlit dashboard.
- Add unit and integration coverage for each processing stage.

## Contributing

1. Create a focused branch for your change.
2. Keep processing logic in `src/` and expose it through `api/` or
   `frontend/` as appropriate.
3. Add or update tests alongside implemented behavior.
4. Update [`ARCHITECTURE.md`](./ARCHITECTURE.md) when boundaries or data flows
   change.
5. Run the relevant tests before opening a pull request.
