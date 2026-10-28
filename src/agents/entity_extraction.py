# Entity Extraction Agent
# This agent is responsible for extracting entities from text using the gemini API. It takes a text as input and returns a list of extracted entities.
    
import os
from pydantic import BaseModel, Field
from typing import List
from langchain_google_genai import ChatGoogleGenerativeAI
from src.schemas.state import NewsState

# 1. Define the exact schema we want the LLM to return
class ExtractedEntities(BaseModel):
    companies: List[str] = Field(description="List of specific companies mentioned (e.g., HDFC Bank)")
    sectors: List[str] = Field(description="List of sectors mentioned (e.g., Banking, Automobile)")
    regulators: List[str] = Field(description="List of regulatory bodies mentioned (e.g., RBI, SEBI)")

# 2. Initialize the stable Gemini model
# Note: Do NOT pass temperature=0; Gemini 3.x Flash models ignore/deprecate it.
llm = ChatGoogleGenerativeAI(
    model="gemini-3.8-flash", 
    api_key=os.getenv("GOOGLE_API_KEY")
)

# 3. Force structured output
structured_llm = llm.with_structured_output(ExtractedEntities)

def extract_entities(state: NewsState) -> NewsState:
    print(f"\n🧠 Extracting entities for: '{state['title']}'")
    
    # Combine title and content for the LLM context
    text_to_analyze = f"Title: {state['title']}\nContent: {state['content']}"
    
    # Invoke the LLM
    result = structured_llm.invoke(text_to_analyze)
    
    # Update the state with the extracted data
    state['companies'] = result.companies
    state['sectors'] = result.sectors
    state['regulators'] = result.regulators
    
    print(f"✅ Extracted Companies: {state['companies']}")
    print(f"✅ Extracted Sectors: {state['sectors']}")
    print(f"✅ Extracted Regulators: {state['regulators']}")
    
    return state