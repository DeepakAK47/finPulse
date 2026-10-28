# This creates the actual multi-agent graph. It routes the article through Deduplication. We also added a temporary extraction_node to show you how the graph moves forward.

# src/graphs/ingestion_graph.py
from langgraph.graph import StateGraph, END
from src.schemas.state import NewsState
from src.agents.deduplication import deduplicate_news

# --- Placeholder for Stage 3 ---
def extraction_node(state: NewsState):
    # We will build this in Stage 3. For now, it just passes the state.
    print("➡️ Moving to Entity Extraction (Stage 3)...")
    return state

# --- Routing Logic ---
def route_after_deduplication(state: NewsState):
    """Determines where to go after checking for duplicates."""
    if state.get('is_duplicate'):
        return "end" # Stop processing duplicates
    return "extraction" # Proceed to extraction if unique

# --- Build the Graph ---
workflow = StateGraph(NewsState)

# Add nodes (Agents)
workflow.add_node("deduplication", deduplicate_news)
workflow.add_node("extraction", extraction_node)

# Set the entry point
workflow.set_entry_point("deduplication")

# Add Conditional Edge (The "Brain" of the graph)
workflow.add_conditional_edges(
    "deduplication",
    route_after_deduplication,
    {
        "end": END,
        "extraction": "extraction"
    }
)

# After extraction, end the graph for now
workflow.add_edge("extraction", END)

# Compile the graph
ingestion_app = workflow.compile()