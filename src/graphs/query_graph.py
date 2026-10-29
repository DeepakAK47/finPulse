# src/graphs/query_graph.py
from langgraph.graph import StateGraph, END
from src.schemas.query_state import QueryState
from src.agents.query_router import route_query
from src.agents.query_retrieval import retrieve_news

workflow = StateGraph(QueryState)

workflow.add_node("router", route_query)
workflow.add_node("retrieval", retrieve_news)

workflow.set_entry_point("router")
workflow.add_edge("router", "retrieval")
workflow.add_edge("retrieval", END)

query_app = workflow.compile()