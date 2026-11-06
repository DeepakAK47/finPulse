# src/utils/embedding.py
import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

# Initialize the Gemini client
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

def get_embedding(text: str) -> list[float]:
    """Converts text to embedding using Gemini API (no local memory needed)."""
    try:
        response = client.models.embed_content(
            model="text-embedding-004",
            contents=text
        )
        return response.embeddings[0].values
    except Exception as e:
        print(f"❌ Embedding API error: {e}")
        return [] # Return empty list to prevent crash