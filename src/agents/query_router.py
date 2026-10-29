# query_router.py
import os
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from src.schemas.query_state import QueryState

class QueryIntent(BaseModel):
    query_type: str = Field(description="Must be one of: 'company', 'sector', 'regulator', 'semantic'")
    extracted_entity: str = Field(description="The specific company, sector, or regulator mentioned. If semantic, return 'None'.")

llm = ChatGoogleGenerativeAI(model="gemini-3.8-flash", api_key=os.getenv("GOOGLE_API_KEY"))
structured_llm = llm.with_structured_output(QueryIntent)

def route_query(state: QueryState) -> QueryState:
    print(f"\n🧭 Routing Query: '{state['query']}'")
    
    prompt = f"""
    Analyze the following financial query and classify it.
    Query: {state['query']}
    """
    
    result = structured_llm.invoke(prompt)
    state['query_type'] = result.query_type
    state['extracted_entity'] = result.extracted_entity
    state['results'] = []
    
    print(f"✅ Classified as: {state['query_type']} (Entity: {state['extracted_entity']})")
    return state