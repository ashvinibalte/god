"""
    Search and retrieve relevant FX Post Trade documents, wire instructions, and currency guides.

    Use this tool when users ask questions about:
    - **Intermediary Banks & SSI:** (e.g., "Who is our intermediary bank for RUB?", "Wire instructions for CAD")
    - **Currency Specifics:** Cut-off times, suspended currencies (e.g., "Is BYN suspended?", "Cut-off for CZK")
    - **Systems Workflows:** Payment flows, Enterprise Payments Infrastructure details
    - **Party Codes & User Guidelines:** IBAN registries, Corporate currency lists, and formatting guides

    PARAMETERS:
    - content (str): The user's question or search query. Use natural language.
    - userJsonData (str): User context data. Set to "None" if no user data provided.

    RETURNS:
    - results: Array of relevant document chunks, each containing:
        * title: Name of the source document (e.g., "Incoming Wire Instruction", "CorporateCurrencyList.pdf")
        * url: Direct link to the full document
        * page: Page number where the information is found
        * content: The actual text content/rules
        * citation_index: Reference ID for the chunk
    - count: Number of chunks returned

    EXAMPLE CALLS:
    - query_policies("Who is our intermediary bank for RUB?", "None")
    - query_policies("What is the cut-off time for CZK?", "None")
    - query_policies("Is BYN a suspended currency?", "None")
    - query_policies("Provide wire instructions for Canadian branch", "None")
    
    You can use the returned chunks to provide comprehensive, accurate answers about FX operations.
    """
