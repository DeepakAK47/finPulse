# setup the realtionship between the tables
import os
from sqlalchemy import create_engine, Column, String, Boolean, JSON
from sqlalchemy.orm import declarative_base, sessionmaker

# 1. Define the path to your data/sqlite.db
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "data", "sqlite.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# 2. Create the Engine and Session
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 3. Define the Table Schema
class NewsArticle(Base):
    __tablename__ = "news_articles"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    source = Column(String, nullable=False)
    
    # Deduplication fields (Stage 2)
    is_duplicate = Column(Boolean, default=False)
    canonical_id = Column(String, nullable=True)
    
    # Extraction fields (Stage 3)
    companies = Column(JSON, nullable=True)
    sectors = Column(JSON, nullable=True)
    regulators = Column(JSON, nullable=True)
    impacted_stocks = Column(JSON, nullable=True)

# 4. Initialize the Database
def init_db():
    Base.metadata.create_all(bind=engine)
    print("✅ SQLite Database initialized.")

# 5. Dependency for FastAPI (we'll use this later)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()