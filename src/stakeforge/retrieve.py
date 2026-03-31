from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable

from stakeforge.duckdb_store import search_fts
from stakeforge.models import Evidence, approx_token_len
from stakeforge.pageindex_adapter import load_tree_artifact, search_tree
from stakeforge.paths import StakeForgePaths
from stakeforge.runtime import StakeForgeConfig


def retrieve(
    *,
    cfg: StakeForgeConfig,
    paths: StakeForgePaths,
    stakeholder_id: str,
    query: str,
    top_k: int = 8,
) -> list[Evidence]:
    """
    Hybrid orchestration (required by R2):
    - Parallel FTS + PageIndex (if enabled)
    - Union + dedupe by (source_uri, heading_path, text_hash)
    - Score merge policy:
      - normalized FTS bm25 score contributes 1.0
      - PageIndex keyword overlap contributes 0.6
    - Token budgeting across all returned evidence with per-source caps.
    """
    candidates: list[Evidence] = []

    if cfg.use_fts:
        for r in search_fts(paths.duckdb_path, stakeholder_id=stakeholder_id, query=query, top_k=top_k):
            candidates.append(
                Evidence(
                    evidence_id=f"fts:{r['passage_id']}",
                    stakeholder_id=r["stakeholder_id"],
                    source_uri=r["source_uri"],
                    heading_path=r.get("heading_path") or "",
                    text=r["text"],
                    retrieval_leg="fts",
                    score=float(r.get("score") or 0.0),
                )
            )

    if cfg.use_pageindex:
        pi_dir = paths.pageindex_dir / stakeholder_id
        if pi_dir.exists():
            for art in sorted(pi_dir.glob("*.pageindex.json")):
                tree = load_tree_artifact(art)
                hits = search_tree(tree, query=query, top_k=max(2, top_k // 2))
                source_uri = art.name.replace(".pageindex.json", ".md")
                for h in hits:
                    if not h.text.strip():
                        continue
                    candidates.append(
                        Evidence(
                            evidence_id=f"pageindex:{art.stem}:{h.node_id}",
                            stakeholder_id=stakeholder_id,
                            source_uri=source_uri,
                            heading_path=h.title_path,
                            text=h.text,
                            retrieval_leg="pageindex",
                            score=float(h.score),
                        )
                    )

    merged = _merge_and_budget(
        candidates,
        token_budget=cfg.token_budget,
        max_tokens_per_source=cfg.max_tokens_per_source,
        limit=top_k,
    )
    return merged


def _merge_and_budget(
    candidates: list[Evidence],
    *,
    token_budget: int,
    max_tokens_per_source: int,
    limit: int,
) -> list[Evidence]:
    # Normalize scores per-leg to reduce dominance.
    fts_scores = [e.score for e in candidates if e.retrieval_leg == "fts"]
    pi_scores = [e.score for e in candidates if e.retrieval_leg == "pageindex"]
    fts_max = max(fts_scores) if fts_scores else 0.0
    pi_max = max(pi_scores) if pi_scores else 0.0

    def fused_score(e: Evidence) -> float:
        if e.retrieval_leg == "fts":
            return (e.score / fts_max) if fts_max else 0.0
        if e.retrieval_leg == "pageindex":
            return 0.6 * ((e.score / pi_max) if pi_max else 0.0)
        return e.score

    # Dedupe by span identity.
    seen: set[str] = set()
    unique: list[tuple[float, Evidence]] = []
    for e in candidates:
        key = _dedupe_key(e)
        if key in seen:
            continue
        seen.add(key)
        unique.append((fused_score(e), e))

    unique.sort(key=lambda t: t[0], reverse=True)

    out: list[Evidence] = []
    remaining = token_budget
    per_source_remaining: dict[str, int] = {}

    for s, e in unique:
        if len(out) >= limit:
            break
        tok = approx_token_len(e.text)
        if tok <= 0:
            continue

        src_budget = per_source_remaining.get(e.source_uri, max_tokens_per_source)
        if tok > remaining or tok > src_budget:
            # try truncating
            max_tok = min(remaining, src_budget)
            if max_tok < 40:
                continue
            e = e.model_copy(update={"text": _truncate_to_tokens(e.text, max_tok)})
            tok = approx_token_len(e.text)

        remaining -= tok
        per_source_remaining[e.source_uri] = src_budget - tok
        out.append(e.model_copy(update={"score": float(s), "retrieval_leg": "hybrid"}))

    return out


def _dedupe_key(e: Evidence) -> str:
    h = hashlib.sha256(e.text.encode("utf-8")).hexdigest()[:16]
    return f"{e.source_uri}|{e.heading_path}|{h}"


def _truncate_to_tokens(text: str, max_tokens: int) -> str:
    # token ~= chars/4
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 1)].rstrip() + "…"

