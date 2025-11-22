import asyncio
import logging
from typing import Dict, List
import pandas as pd

from langgraph.graph import StateGraph, END, START
from src.chat.ai.chains.keyword_extraction import tachyon_keyword_completion
from src.chat.ai.chains.pick_documents import tachyon_pick_documents_completion
from src.chat.ai.graphs.states import SearchState, SearchResponse, SearchInput, VectorSearchInput, QuestionSearchInput, KeywordSearchInput
from src.chat.tachyon.vector_store import TachyonVS
from src.config import Config

logger = logging.getLogger(__name__)

async def vector_search_node(state: VectorSearchInput) -> dict:
    """
    Perform a standard vector search using the Tachyon Vector Store.
    """
    kwargs = state.field_filter or {}
    
    # FIX: Switch to HYBRID search.
    # This allows us to send 'reRanker': 'RRF' which satisfies the API's payload requirements.
    if "search_type" not in kwargs:
        kwargs["search_type"] = "hybrid"
    
    if "re_ranker" not in kwargs:
        kwargs["re_ranker"] = "RRF"

    search_response = await TachyonVS.aquery(
        **kwargs, 
        query=state.query,
        search_initiator=state.search_method
    )
    return {"search_data": [SearchResponse(search_input=state, search_results=search_response)]}

async def question_search_node(state: QuestionSearchInput) -> dict:
    """
    Perform a search using the question directly.
    """
    kwargs = state.field_filter or {}
    
    # FIX: Switch to HYBRID search.
    if "search_type" not in kwargs:
        kwargs["search_type"] = "hybrid"
        
    if "re_ranker" not in kwargs:
        kwargs["re_ranker"] = "RRF"
        
    search_response = await TachyonVS.aquery(
        **kwargs,
        query=state.query,
        search_initiator=state.search_method
    )
    return {"search_data": [SearchResponse(search_input=state, search_results=search_response)]}

async def keyword_search_node(state: KeywordSearchInput) -> dict:
    """
    Perform a keyword search using the Tachyon Vector Store.
    """
    keywords = await tachyon_keyword_completion(context=state.query)
    
    kwargs = state.field_filter or {}
    
    # FIX: Switch to HYBRID search.
    if "search_type" not in kwargs:
        kwargs["search_type"] = "hybrid"
        
    if "re_ranker" not in kwargs:
        kwargs["re_ranker"] = "RRF"
    
    search_response = await TachyonVS.aquery(
        **kwargs,
        query=keywords, 
        search_initiator=state.search_method
    )
    return {"search_data": [SearchResponse(search_input=state, search_results=search_response)]}

def search_router_node(state: SearchInput) -> list[str]:
    """Delegate the search based on the state configuration."""
    paths = []
    if state.vector_search:
        paths.append("vector_search_node")
    
    if state.question_search:
        paths.append("question_search_node")

    if state.keyword_search:
        paths.append("keyword_search_node")
        
    return paths

def collect_search_results_node(state: SearchState) -> SearchState:
    """
    Collect search results from different search nodes.
    """
    results_list = [search.search_results.df for search in state.search_data if not search.search_results.df.empty]
    
    if not results_list:
        logger.warning("No search results found from any node.")
        state.raw_results = {}
        return state

    results_df = pd.concat(results_list).sort_values("score", ascending=False)
    
    # Drop duplicates based on available unique fields
    results_df = results_df.drop_duplicates(subset=["title", "page", "content"])

    return {"raw_results": results_df.to_dict(orient="records")}


async def search_select_graph(state: SearchState):
    """
    Main entry point to run the graph and select documents.
    """
    response = await search_graph.ainvoke(state)
    
    raw_results = response.get("raw_results")
    if not raw_results:
        logger.warning("No raw results returned from search graph.")
        return []

    # Convert to Document objects
    from src.chat.ai.graphs.states import Document
    docs = [Document(**r) for r in raw_results]
    
    # Limit candidates
    max_docs = Config.tachyon.max_documents_considered
    docs = docs[:max_docs]

    available_documents_str = "\n\n".join([d.str_overview_repr for d in docs])
    
    # Ask LLM to pick
    picked_strings = await tachyon_pick_documents_completion(
        available_documents=available_documents_str, 
        query=state.query
    )
    
    # Match and Ensure Minimum
    from src.chat.ai.chains.pick_documents import _match_picked_documents, _ensure_minimum_documents
    
    matched_docs = _match_picked_documents(picked_strings, docs)
    final_docs = _ensure_minimum_documents(matched_docs, docs)
    
    return [d.model_dump() for d in final_docs]

# --- Graph Definition ---
graph_builder = StateGraph(SearchState)
graph_builder.add_node("vector_search_node", vector_search_node)
graph_builder.add_node("keyword_search_node", keyword_search_node)
graph_builder.add_node("question_search_node", question_search_node)
graph_builder.add_node("collect_search_results_node", collect_search_results_node)

graph_builder.add_conditional_edges(
    START,
    search_router_node,
    {
        "vector_search_node": "vector_search_node",
        "keyword_search_node": "keyword_search_node",
        "question_search_node": "question_search_node"
    }
)

graph_builder.add_edge("vector_search_node", "collect_search_results_node")
graph_builder.add_edge("keyword_search_node", "collect_search_results_node")
graph_builder.add_edge("question_search_node", "collect_search_results_node")
graph_builder.add_edge("collect_search_results_node", END)

search_graph = graph_builder.compile()
