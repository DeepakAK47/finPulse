# Creating the Embedding model for the text data using the SentenceTransformer library.
from sentence_transformers import SentenceTransformer

# Load the model globally so it only loads once into memory
model = SentenceTransformer('all-MiniLM-L6-v2')

def get_embedding(text: str) -> list[float]:
    """Converts a string of text into a vector embedding."""
    return model.encode(text).tolist()