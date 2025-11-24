search_result = await search_select_graph.ainvoke(search_input)

# 1. Get the unified document list from the graph output
#    (use the real key name from your graph result – based on your screenshots
#     it's usually "results")
docs_raw = search_result.get("results", [])

# 2. Ensure we have Document objects
documents: list[Document] = [
    d if isinstance(d, Document) else Document(**d)
    for d in docs_raw
]

# 3. Build final answer + chunks + references
final_payload = await build_answer_with_references(
    question=payload.content,   # or payload.question / payload.input_text (use your real field)
    documents=documents,
)

# 4. Optionally pass through any extra debug info you still want
final_payload["search_utilities"] = search_result.get("search_utilities")
final_payload["count"] = len(documents)

return final_payload

