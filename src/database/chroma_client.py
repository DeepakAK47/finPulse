# setup for vector database
import chromadb # library to manage the vector database 
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHROMA_PATH = os.path.join(BASE_DIR, "data", "chroma_db")
os.makedirs(CHROMA_PATH, exist_ok=True)

# Initialize persistent client (saves to disk)
client = chromadb.PersistentClient(path=CHROMA_PATH)

# Get or create the collection. 
# We use "cosine" distance because it's best for text similarity.
news_collection = client.get_or_create_collection(
    name="news_articles", 
    metadata={"hnsw:space": "cosine"}
)
print("ChromaDB initialized.")
