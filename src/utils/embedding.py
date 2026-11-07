# src/utils/embedding.py
import os
from typing import Optional
import logging
from google import genai
from dotenv import load_dotenv
#IMP

load_dotenv()

client: genai.Client | None = None

def get_embedding(text: str) -> Optional[list[float]]:
    """Converts text to embedding using Gemini API (no local memory needed)."""
    if not os.getenv("GOOGLE_API_KEY"):
        print("Embedding unavailable: GOOGLE_API_KEY is not configured.")
        return None

    try:
        global client
        if client is None:
            client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        response = client.models.embed_content(
            model="text-embedding-004",
            contents=text
        )
        if not response.embeddings or not response.embeddings[0].values:
            print("Embedding unavailable: Gemini returned no vector.")
            return None
        return response.embeddings[0].values
    except Exception as error:
        print(f"Embedding API error: {error}")
        return None