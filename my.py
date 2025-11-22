async def vector_search_node(state: VectorSearchInput) -> dict:
    """
    Perform a standard vector search using the Tachyon Vector Store.
    """
    # Ensure kwargs is at least an empty dict
    kwargs = state.field_filter or {}
    
    # FIX: Explicitly set search_type if missing to prevent 422
    if "search_type" not in kwargs:
        kwargs["search_type"] = "semantic"

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
    # Ensure kwargs is at least an empty dict
    kwargs = state.field_filter or {}
    
    # FIX: Explicitly set search_type if missing to prevent 422
    if "search_type" not in kwargs:
        kwargs["search_type"] = "semantic"
        
    search_response = await TachyonVS.aquery(
        **kwargs,
        query=state.query,
        search_initiator=state.search_method
    )
    return {"search_data": [SearchResponse(search_input=state, search_results=search_response)]}
