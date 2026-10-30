# api/main.py
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from pydantic import BaseModel
from src.graphs.query_graph import query_app

app = FastAPI(title="FinPulse API")

class QueryInput(BaseModel):
    query: str

@app.post("/query")
def query_news(payload: QueryInput):
    initial_state = {"query": payload.query}
    result = query_app.invoke(initial_state)
    return {
        "query": payload.query,
        "query_type": result.get("query_type"),
        "results": result.get("results")
    }