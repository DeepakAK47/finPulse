# src/graphs/ingestion_graph.py
from langgraph.graph import StateGraph, END
from src.schemas.state import NewsState

# Import all our agents
from src.agents.deduplication import deduplicate_news
from src.agents.entity_extraction import extract_entities
from src.agents.impact_analysis import analyze_impact
from src.agents.storage import store_article

def route_after_deduplication(state: NewsState):
    if state.get('is_duplicate'):
        return "end"
    return "extraction"

# Build the Graph
workflow = StateGraph(NewsState)

# Add all nodes
workflow.add_node("deduplication", deduplicate_news)
workflow.add_node("extraction", extract_entities)
workflow.add_node("impact", analyze_impact)
workflow.add_node("storage", store_article)

# Set entry point
workflow.set_entry_point("deduplication")

# Add Conditional Edge
workflow.add_conditional_edges(
    "deduplication",
    route_after_deduplication,
    {"end": END, "extraction": "extraction"}
)

# Connect the rest of the pipeline linearly
workflow.add_edge("extraction", "impact")
workflow.add_edge("impact", "storage")
workflow.add_edge("storage", END)

# Compile
ingestion_app = workflow.compile()