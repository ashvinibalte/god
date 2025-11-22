# chat/ai/graphs/search.py
from __future__ import annotations

import os
from urllib.parse import urlparse
from typing import Any, Dict, List, Optional

import pandas as pd

# -------------------------------------------------------------------
# Normalization helpers: rename fields, coalesce missing values,
# and compose a human-friendly "reference" string for display.
# -------------------------------------------------------------------

_RENAME = {
    "title": "document_name",
    "hyperlink": "document_link",
    "sectionTitle": "section_name",
    "sectionHyperlink": "section_link",
    "snippet": "section_text_part",
    "text": "section_text_part",
    "content": "section_text_part",
    "score": "score",
    "rerank_score": "reranker_score",
    "reranker_score": "reranker_score",
    "citationIndex": "citation_index",
    "citation_index": "citation_index",
    "citationIndexs": "citation_indices",
    "citationIndices": "citation_indices",
    "page": "page",
}

def _derive_doc_name_from_link(url: str) -> str:
    if not url:
        return "Unknown Document"
    try:
        p = urlparse(url)
        base = os.path.basename(p.path) or p.netloc or "Unknown Document"
        return base
    except Exception:
        return "Unknown Document"

def _as_list(x):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return []
    return x if isinstance(x, list) else [x]

def _to_int_or_none(x):
    try:
        return int(x)
    except Exception:
        return None

def normalize_hits_df(hits: List[Dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(hits) if hits else pd.DataFrame()

    # rename to canonical names
    rename_cols = {k: v for k, v in _RENAME.items() if k in df.columns}
    if rename_cols:
        df = df.rename(columns=rename_cols)

    # ensure required columns exist
    for col in [
        "document_name", "document_link", "section_name", "section_link",
        "section_text_part", "page", "citation_index", "citation_indices",
        "score", "reranker_score"
    ]:
        if col not in df.columns:
            df[col] = None

    # document name fallback from link
    df["document_name"] = df["document_name"].fillna("").astype(str)
    mask = df["document_name"].eq("") & df["document_link"].notna()
    if mask.any():
        df.loc[mask, "document_name"] = df.loc[mask, "document_link"].apply(_derive_doc_name_from_link)
    df["document_name"] = df["document_name"].replace("", "Unknown Document")

    # scores
    df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(0.0)
    df["reranker_score"] = pd.to_numeric(df["reranker_score"], errors="coerce")

    # normalize citations
    if "citation_indices" in df.columns:
        df["citation_indices"] = df["citation_indices"].apply(_as_list)
        df["citation_indices"] = df["citation_indices"].apply(
            lambda xs: [y for y in (_to_int_or_none(x) for x in xs) if y is not None]
        )
    else:
        df["citation_indices"] = [[] for _ in range(len(df))]

    # infer page from citations if page is NaN
    if "page" not in df.columns:
        df["page"] = None
    need_page = df["page"].isna() & df["citation_indices"].astype(bool)
    if need_page.any():
        df.loc[need_page, "page"] = df.loc[need_page, "citation_indices"].apply(lambda xs: xs[0] if xs else None)

    # section name fallback
    def best_section_name(row):
        if row.get("section_name"):
            return row["section_name"]
        if pd.notna(row.get("page")):
            return f"Page {int(row['page'])}"
        txt = (row.get("section_text_part") or "").strip()
        return (txt[:80] + "…") if txt else "Untitled Section"
    df["section_name"] = df.apply(best_section_name, axis=1)

    # compose reference
    def make_ref(row):
        base = row["document_name"] or "Unknown Document"
        part = row.get("section_name") or "Section"
        page = row.get("page")
        if page is not None and page == page:
            return f"{base} ▸ {part} (p.{int(page)})"
        return f"{base} ▸ {part}"
    df["reference"] = df.apply(make_ref, axis=1)

    return df

# -------------------------------------------------------------------
# Building the final results structure used by your app
# -------------------------------------------------------------------

def build_results_from_df(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Turn the normalized DataFrame into your app's 'results' list.
    Each item contains a doc-level object with a list of sections.
    """
    results: List[Dict[str, Any]] = []

    if df.empty:
        return results

    for doc_name, group in df.groupby("document_name", dropna=False):
        first = group.iloc[0]
        doc = {
            "document_name": first["document_name"],
            "document_link": first.get("document_link") or "",
            "document_score": float(group["score"].max()),
            "document_sections": [],
        }

        for _, row in group.iterrows():
            doc["document_sections"].append({
                "section_name": row.get("section_name") or "",
                "section_link": row.get("section_link") or "",
                "section_text_part": row.get("section_text_part") or "",
                "page": int(row["page"]) if pd.notna(row.get("page")) else None,
                "citation_index": row.get("citation_index"),
                "citation_indices": row.get("citation_indices") or [],
                "score": float(row.get("score") or 0.0),
                "reranker_score": row.get("reranker_score"),
                "reference": row.get("reference") or "",
            })
        results.append(doc)

    # sort documents by their best score (desc)
    results.sort(key=lambda d: d.get("document_score", 0.0), reverse=True)
    return results

# -------------------------------------------------------------------
# Example node that collects hits -> normalizes -> builds results
# (use this inside your graph after vector search completes)
# -------------------------------------------------------------------

async def collect_search_results_node(state) -> Dict[str, Any]:
    """
    Expected `state.search_response` has an attribute `.hits` (list of dicts)
    as returned by TachyonVS.query(...).
    """
    search_response = getattr(state, "search_response", None)
    raw_hits = getattr(search_response, "hits", []) if search_response else []

    df = normalize_hits_df(raw_hits)
    results = build_results_from_df(df)

    # store in state for downstream nodes / printing
    state.results = results
    state.results_df = df  # optional: keep the dataframe for debugging

    return {"results": results}

# -------------------------------------------------------------------
# Helper: pretty print first section reference of each document
# -------------------------------------------------------------------

def print_top_references(results: List[Dict[str, Any]]) -> None:
    for i, doc in enumerate(results, 1):
        sec = (doc.get("document_sections") or [{}])[0]
        ref = sec.get("reference") or f"{doc.get('document_name','Unknown Document')} ▸ {sec.get('section_name','Section')}"
        print(f"{i}. {ref}")
