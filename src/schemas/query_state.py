from typing import TypedDict,List,Optional,Dict

class QueryState(TypedDict):
    query: str
    query_type: str   # "company", "sector", "regulator", "semantic"
    extracted_entity: Optional[str] 
    results: List[Dict]