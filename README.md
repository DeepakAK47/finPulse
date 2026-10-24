# finPulse

finPulse is a planned financial-news intelligence platform for collecting,
organizing, and analyzing market-related news. The project is structured around
an API, a Streamlit frontend, persistent storage, and agent-style processing
pipelines.

> **Project status:** This repository currently contains the initial project
> scaffold. The application entry points and processing modules are placeholders
> and are not runnable yet.

## Planned capabilities

The project layout is prepared for:

- News ingestion and deduplication
- Entity extraction from financial news
- Impact analysis for companies, sectors, and markets
- Natural-language query routing
- SQLite-backed application data
- Chroma-backed vector search
- A FastAPI service layer
- A Streamlit dashboard

These capabilities are planned based on the current module structure and will
be implemented incrementally.

## Repository structure

```text
finPulse/
├── api/                    # FastAPI application and route definitions
├── data/                   # Local data, mock news, SQLite, and Chroma storage
├── frontend/               # Streamlit user interface
├── src/
│   ├── agents/             # Deduplication, extraction, impact, and query agents
│   ├── database/           # SQLite and Chroma integrations
│   ├── graphs/             # Ingestion and query workflows
│   ├── schemas/            # Shared application state and data models
│   └── utils/              # Shared utilities such as embeddings
├── tests/                  # Automated tests
├── ARCHITECTURE.md         # Architecture notes
└── requirements.txt        # Python dependencies
```

## Prerequisites

- Python 3.11 or newer
- Git

## Local setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the project dependencies once they are listed in
[`requirements.txt`](./requirements.txt):

```powershell
python -m pip install -r requirements.txt
```

## Running the project

The API and Streamlit entry points are not implemented yet. Once they are
available, the expected development commands are:

```powershell
# Start the API
uvicorn api.main:app --reload

# Start the Streamlit dashboard
streamlit run frontend/app.py
```

## Testing

Run the test suite with:

```powershell
python -m pytest
```

The existing test files are part of the scaffold and will become meaningful as
the corresponding processing modules are implemented.

## Data and local state

The `data/` directory is intended for local development data and generated
state. Do not commit credentials, API keys, or other secrets. Keep environment
configuration in a local `.env` file and add required variable names to the
documentation as integrations are added.

## Contributing

1. Create a focused branch for your change.
2. Keep processing logic in `src/` and expose it through `api/` or
   `frontend/` as appropriate.
3. Add or update tests in `tests/`.
4. Update [`ARCHITECTURE.md`](./ARCHITECTURE.md) when boundaries or data flows
   change.
5. Run the relevant tests before opening a pull request.