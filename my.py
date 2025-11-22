# tachyon/vector_store.py
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# NOTE: This module assumes you already have:
#   - Config.tachyon.search_url
#   - Config.tachyon.collection_id
#   - Config.tachyon.timeout
#   - TachyonVS.get_headers()
#   - TachyonVS._make_async_request(url, payload_str, headers, timeout)
#   - TachyonVS._as_search_results(resp_json, **kwargs)
# If your names differ, adjust the references below.

class TachyonVS:
    """Light wrapper around Tachyon Search endpoints."""

    # ---------- PATCH START: payload builder + query ----------

    @classmethod
    def _build_payload(
        cls,
        query: str,
        search_count: int = 10,
        fields: Optional[List[str]] = None,
        field_filter: Optional[Dict[str, Any]] = None,
        search_type: str = "semantic",                   # "semantic" | "keyword" | "hybrid"
        re_ranker: Optional[str] = None,                 # e.g., "semantic-ranker-512-003" / "RRF"
    ) -> Dict[str, Any]:
        """
        Build a Tachyon payload that always asks for reference-friendly fields.
        """
        # Ask for reference fields explicitly; backend will ignore unknown ones.
        fields = fields or [
            # document-level identity
            "title", "hyperlink",
            # section identity
            "sectionTitle", "sectionHyperlink",
            # content / snippets
            "content", "snippet", "text",
            # citation/page-ish things
            "page", "citationIndex", "citationIndexs",
            # scoring
            "score", "rerank_score", "reranker_score",
        ]

        if search_type == "hybrid" and not re_ranker:
            # Hybrid must specify a re-ranker, otherwise results order is ambiguous.
            raise ValueError("Re-Ranking algorithm must be specified for hybrid search.")

        payload: Dict[str, Any] = {
            "query": (query or "").strip(),
            "limit": int(search_count or 10),
            "collectionId": getattr(getattr(Config, "tachyon"), "collection_id", None),
            "search_type": search_type,        # server accepts "semantic" | "keyword" | "hybrid"
            "reRanker": re_ranker,             # server will ignore if None
            "fields": fields,
            "filters": field_filter or None,
        }
        # Remove empty keys (keeps payload clean in logs and avoids server-side defaults confusion)
        payload = {k: v for k, v in payload.items() if v not in (None, "", [], {})}
        return payload

    @classmethod
    async def query(
        cls,
        query: str,
        search_count: int = 10,
        fields: Optional[List[str]] = None,
        field_filter: Optional[Dict[str, Any]] = None,
        search_type: str = "semantic",
        re_ranker: Optional[str] = None,
        search_initiator: Optional[str] = None,
    ):
        """
        Run a Tachyon search. Supports semantic-only or hybrid+re-ranking.
        """
        url = getattr(getattr(Config, "tachyon"), "search_url", None)
        timeout = getattr(getattr(Config, "tachyon"), "timeout", 30.0)

        if not url:
            raise RuntimeError("Config.tachyon.search_url is not set")

        payload = cls._build_payload(
            query=query,
            search_count=search_count,
            fields=fields,
            field_filter=field_filter,
            search_type=search_type,
            re_ranker=re_ranker,
        )

        headers = cls.get_headers(extra={"payload": json.dumps(payload), "initiator": (search_initiator or "")})
        start_time = datetime.now(timezone.utc)

        # Make the request using your existing async helper
        resp_json, initiator_used = await cls._make_async_request(url, json.dumps(payload), headers, timeout)

        # Helpful debug so you can confirm reranker usage in logs
        try:
            logger.debug(
                "tachyon.search response",
                extra={
                    "status_code": resp_json.get("status_code", 200),
                    "count": len(resp_json.get("result", {}).get("hits", [])),
                    "search_type": search_type,
                    "reRanker": re_ranker or "omitted_none",
                },
            )
        except Exception:
            pass

        # Convert to your SearchResults type using the existing helper
        return cls._as_search_results(
            resp_json,
            headers=headers,
            status_code=resp_json.get("status_code", 200),
            start_time=start_time,
            search_initiator=initiator_used,
        )

    # ---------- PATCH END ----------
