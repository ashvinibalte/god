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

def _ensure_minimum_documents(matched_documents: list, available_docs_ordered: list, min_required: int = None) -> list:
    """
    Ensure we have the minimum number of documents.
    Uses Config.tachyon.min_picked_documents (from dev.yml) as default.
    """
    # Fallback to Config value if not provided explicitly
    if min_required is None:
        min_required = Config.tachyon.min_picked_documents

    if len(matched_documents) >= min_required:
        return matched_documents

    result = matched_documents.copy()
    existing_ids = {f"{d.title}_{d.page}" for d in result}

    for doc in available_docs_ordered:
        doc_id = f"{doc.title}_{doc.page}"
        if doc_id not in existing_ids:
            result.append(doc)
            if len(result) >= min_required:
                break

    return result
