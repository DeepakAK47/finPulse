# Schema for input state
from typing import TypedDict, List, Dict, Optional

class NewsState(TypedDict):
    # Input Data
    article_id: str
    title: str
    content: str
    source: str
    
    # Stage 2: Deduplication
    is_duplicate: bool
    canonical_id: Optional[str]
    
    # Stage 3: Extraction
    companies: Optional[List[str]]
    sectors: Optional[List[str]]
    regulators: Optional[List[str]]
    impacted_stocks: Optional[List[Dict]]

    