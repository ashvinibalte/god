def _match_picked_documents(picked_doc_strs: list, available_docs: List[Document]) -> List[Document]:
    """
    Matches the LLM's selection against the actual document objects.
    Prioritizes Unique Title matching.
    """
    matched_docs = []

    for picked_str in picked_doc_strs:
        picked_str_clean = picked_str.strip()

        for doc in available_docs:
            if doc.title in picked_str_clean:
                matched_docs.append(doc)
                break

    unique_docs = []
    seen = set()
    for d in matched_docs:
        unique_id = f"{d.title}_{d.page}"
        if unique_id not in seen:
            unique_docs.append(d)
            seen.add(unique_id)

    return unique_docs
