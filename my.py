async def build_answer_with_references(question: str, documents: list[Document]) -> dict:
    # Load config (reads configs/dev.yml)
    cfg = Config()

    # ✔ Use default_search_count exactly from dev.yml
    chunk_limit = cfg.tachyon.default_search_count

    # Limit results
    top_docs = documents[:chunk_limit]

    chunks = [doc.to_chunk_dict(i + 1) for i, doc in enumerate(top_docs)]

    # TODO: replace with your Tachyon-based final answer generation
    answer = "AI answer will go here."

    references = []
    for c in chunks:
        if c["file_name"]:
            if c["page"] is not None:
                references.append(f"[{c['ref_id']}] {c['file_name']}, p. {c['page']}")
            else:
                references.append(f"[{c['ref_id']}] {c['file_name']}")

    return {
        "answer": answer,
        "chunks": chunks,
        "references": references,
    }
