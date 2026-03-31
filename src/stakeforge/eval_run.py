from __future__ import annotations

from pathlib import Path
from typing import Any

from stakeforge.eval_extract import load_cases_jsonl
from stakeforge.eval_scorer import score_reply


def run_dataset(
    dataset_path: Path,
    replies_dir: Path,
    **score_kwargs: Any,
) -> list[dict]:
    cases = load_cases_jsonl(dataset_path)
    rows: list[dict] = []
    for c in cases:
        rf = replies_dir / f"{c.case_id}.txt"
        if not rf.exists():
            rf = replies_dir / f"{c.case_id}.md"
        reply = rf.read_text(encoding="utf-8") if rf.exists() else ""
        sc = score_reply(c, reply, **score_kwargs)
        rows.append(
            {
                "case_id": c.case_id,
                "score": sc.total,
                "scores": sc.model_dump(),
                "missing_reply": not rf.exists(),
            }
        )
    return rows


def average_total(rows: list[dict]) -> float:
    if not rows:
        return 0.0
    ok = [r["score"] for r in rows if not r.get("missing_reply")]
    if not ok:
        return 0.0
    return sum(ok) / len(ok)
