# src/utils/embedding.py
# Don't load the model globally. This causes OOM on Render free tier.
_model = None

def get_embedding(text: str) -> list[float]:
    """Converts text to embedding, loading model only when needed."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        print("Loading embedding model...")
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    
    return _model.encode(text).tolist()