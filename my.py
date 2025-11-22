async def keyword_search_node(state: KeywordSearchInput) -> dict:
    """
    Perform a keyword search using the Tachyon Vector Store.
    """
    # 1. Extract keywords
    keywords = await tachyon_keyword_completion(context=state.query)
    
    # 2. Prepare filters (ensure it's a dict)
    kwargs = state.field_filter or {}
    
    # 3. Explicitly set defaults to prevent 422 error if kwargs is empty
    # The API likely demands 'search_type' or 're_ranker' to be present
    if "search_type" not in kwargs:
        kwargs["search_type"] = "semantic" # Safe default
        
    # 4. Execute search
    search_response = await TachyonVS.aquery(
        **kwargs,
        query=keywords, 
        search_initiator=state.search_method
    )
    return {"search_data": [SearchResponse(search_input=state, search_results=search_response)]}
