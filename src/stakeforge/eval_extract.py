from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any

import yaml

from stakeforge.duckdb_store import passage_id_for
from stakeforge.eval_models import EvalCase, EvalExpected, EvalEvidenceItem, EvalTask
from stakeforge.models import Evidence


_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(md_text: str) -> tuple[dict[str, Any] | None, str]:
    m = _FRONTMATTER_RE.match(md_text)
    if not m:
        return None, md_text
    raw = m.group(1)
    data = yaml.safe_load(raw)
    if data is None:
        return None, md_text
    if not isinstance(data, dict):
        return None, md_text[m.end() :]
    return data, md_text[m.end() :]


def eval_blob_from_frontmatter(data: dict[str, Any]) -> dict[str, Any]:
    ev = data.get("stakeforge_eval")
    if isinstance(ev, dict):
        return ev
    return data


def _gold_to_evidence(stakeholder_id: str, items: list[dict[str, Any]]) -> list[Evidence]:
    out: list[Evidence] = []
    for it in items:
        row = EvalEvidenceItem.model_validate(it)
        eid = row.evidence_id
        if not eid:
            eid = passage_id_for(stakeholder_id, row.source_uri, row.heading_path, row.text)
            eid = f"gold:{eid}"
        out.append(
            Evidence(
                evidence_id=eid,
                stakeholder_id=stakeholder_id,
                source_uri=row.source_uri or "interview-notes",
                heading_path=row.heading_path,
                text=row.text,
                retrieval_leg="hybrid",
                score=1.0,
            )
        )
    return out


def extract_case_from_markdown(md_path: Path) -> EvalCase:
    text = md_path.read_text(encoding="utf-8")
    fm, _body = parse_frontmatter(text)
    if fm is None:
        raise ValueError(f"No YAML frontmatter found in {md_path}")
    blob = eval_blob_from_frontmatter(fm)
    stakeholder_id = str(blob.get("stakeholder_id", "")).strip()
    if not stakeholder_id:
        raise ValueError("stakeforge_eval.stakeholder_id is required")
    query = str(blob.get("query", "")).strip()
    if not query:
        raise ValueError("stakeforge_eval.query is required")

    case_id = str(blob.get("case_id") or "").strip() or f"case-{uuid.uuid4().hex[:10]}"
    persona_md = str(blob.get("persona_md") or "").strip()

    gold = blob.get("gold_evidence") or []
    if not isinstance(gold, list):
        gold = []
    evidence = _gold_to_evidence(stakeholder_id, [dict(x) for x in gold])

    must_cite = blob.get("must_include_citations_to")
    if must_cite is None and evidence:
        must_cite = [e.evidence_id for e in evidence]
    if must_cite is not None and not isinstance(must_cite, list):
        must_cite = []
    must_cite = [str(x).strip() for x in (must_cite or []) if str(x).strip()]

    expected = EvalExpected(
        must_include_citations_to=must_cite,
        must_not_claim=[str(x) for x in (blob.get("must_not_claim") or [])],
        stance=(str(blob["stance"]) if blob.get("stance") else None),
        decision_style=(str(blob["decision_style"]) if blob.get("decision_style") else None),
        key_points=[str(x) for x in (blob.get("key_points") or [])],
        must_push_back=(bool(blob["must_push_back"]) if "must_push_back" in blob else None),
        pushback_on=(str(blob["pushback_on"]) if blob.get("pushback_on") else None),
    )

    task_raw = blob.get("task") or {}
    task = EvalTask.model_validate(task_raw) if isinstance(task_raw, dict) else EvalTask()

    meta = blob.get("metadata") if isinstance(blob.get("metadata"), dict) else {}
    meta = {**meta, "source_file": str(md_path)}

    return EvalCase(
        case_id=case_id,
        stakeholder_id=stakeholder_id,
        persona_md=persona_md,
        query=query,
        evidence=evidence,
        task=task,
        expected=expected,
        metadata=meta,
    )


def append_case_jsonl(md_path: Path, jsonl_path: Path) -> EvalCase:
    case = extract_case_from_markdown(md_path)
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("a", encoding="utf-8") as f:
        f.write(case.model_dump_json() + "\n")
    return case


def load_cases_jsonl(path: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        cases.append(EvalCase.model_validate_json(line))
    return cases
