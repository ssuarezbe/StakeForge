from __future__ import annotations

import re
from typing import Iterable

# Canonical machine-parseable citation token for eval + LLM replies.
# Example: "Per CITE[fts:a1b2c3d4e5f678901234], we should phase the rollout."
CITE_PATTERN = re.compile(r"CITE\[([^\]]+)\]")


def cite_token(evidence_id: str) -> str:
    return f"CITE[{evidence_id.strip()}]"


def extract_cite_ids(text: str) -> list[str]:
    return [m.group(1).strip() for m in CITE_PATTERN.finditer(text or "")]


def citation_validity_score(
    reply: str,
    *,
    allowed_ids: set[str],
) -> tuple[float, list[str]]:
    """
    Returns (validity_score, unknown_citations).
    Validity = 1.0 if every CITE[...] references an allowed id; else penalized by unknown/total cites.
    """
    cited = extract_cite_ids(reply)
    if not cited:
        return 1.0, []
    unknown = [c for c in cited if c not in allowed_ids]
    if not unknown:
        return 1.0, []
    return max(0.0, 1.0 - (len(unknown) / len(cited))), unknown


def must_cite_coverage_score(reply: str, *, must_include: Iterable[str]) -> float:
    need = [m.strip() for m in must_include if str(m).strip()]
    if not need:
        return 1.0
    cited = set(extract_cite_ids(reply))
    hit = sum(1 for m in need if m in cited)
    return hit / len(need)
