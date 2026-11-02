# query_router agent
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from src.schemas.query_state import QueryState

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


class QueryIntent(BaseModel):
    query_type: str = Field(description="Must be one of: 'company', 'sector', 'regulator', 'semantic'")
    extracted_entity: str = Field(description="The specific company, sector, or regulator mentioned. If semantic, return 'None'.")

def _local_route(query: str) -> QueryIntent:
    lowered = query.lower()
    company_names = ("HDFC Bank", "ICICI Bank", "Tata Motors")
    sectors = ("Banking", "Automobile", "Financial Services")

    for company in company_names:
        if company.lower() in lowered:
            return QueryIntent(query_type="company", extracted_entity=company)
    for sector in sectors:
        if sector.lower() in lowered:
            return QueryIntent(query_type="sector", extracted_entity=sector)
    if "rbi" in lowered or "reserve bank" in lowered or "regulator" in lowered:
        return QueryIntent(query_type="regulator", extracted_entity="RBI")
    return QueryIntent(query_type="semantic", extracted_entity="None")


def _classify(query: str) -> QueryIntent:
    if not GOOGLE_API_KEY:
        return _local_route(query)

    from langchain_google_genai import ChatGoogleGenerativeAI

    llm = ChatGoogleGenerativeAI(
        model="gemini-3.8-flash",
        api_key=GOOGLE_API_KEY,
        request_timeout=10,
        max_retries=0,
    )
    try:
        return llm.with_structured_output(QueryIntent).invoke(
            f"Analyze and classify this financial query as company, sector, regulator, or semantic.\nQuery: {query}"
        )
    except Exception as error:
        print(f"Gemini query routing failed; using local routing: {error}")
        return _local_route(query)

def route_query(state: QueryState) -> QueryState:
    print(f"\nRouting query: '{state['query']}'")
    
    result = _classify(state["query"])
    state['query_type'] = result.query_type
    state['extracted_entity'] = result.extracted_entity
    state['results'] = []
    
    print(f"Classified as: {state['query_type']} (Entity: {state['extracted_entity']})")
    return state