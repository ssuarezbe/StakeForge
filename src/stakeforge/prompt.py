from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Iterable

from stakeforge.dolt import DoltRepo
from stakeforge.models import Evidence
from stakeforge.persona_load import load_persona_markdown_with_rubric
from stakeforge.persona_schema import render_persona_rubric_md
from stakeforge.paths import StakeForgePaths
from stakeforge.runtime import StakeForgeConfig


def build_persona_prompt(
    *,
    cfg: StakeForgeConfig,
    paths: StakeForgePaths,
    stakeholder_id: str,
    persona_md_path: Path,
    query: str,
    evidence: list[Evidence],
) -> str:
    persona_body, persona_rubric = load_persona_markdown_with_rubric(persona_md_path)
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"

    # Use JSON mode so datetimes (Evidence.created_at) are serializable.
    evidence_json = [e.model_dump(mode="json") for e in evidence]
    prompt_id = _stable_id(stakeholder_id, str(persona_md_path), query, json.dumps(evidence_json, sort_keys=True))
    evidence_json_path = paths.logs_dir / f"evidence.{prompt_id}.json"
    evidence_json_path.write_text(json.dumps(evidence_json, indent=2, ensure_ascii=False), encoding="utf-8")

    prompt_md = _render_prompt_md(
        stakeholder_id=stakeholder_id,
        persona_md=persona_body,
        persona_rubric_md=(render_persona_rubric_md(persona_rubric) if persona_rubric else ""),
        query=query,
        evidence=evidence,
        generated_at=now,
    )

    # Optional: log revision to Dolt for auditability.
    if cfg.dolt in {"auto", "on"} and paths.dolt_dir.exists():
        try:
            repo = DoltRepo(paths.dolt_dir)
            rel_ev = _copy_into_dolt(repo, evidence_json_path, dst_rel=Path("logs") / evidence_json_path.name)
            rel_persona = _copy_into_dolt(repo, persona_md_path, dst_rel=Path("personas") / stakeholder_id / persona_md_path.name)
            repo.sql(
                f"""
                INSERT INTO prompt_revisions(prompt_id, stakeholder_id, created_at, persona_md_path, query, evidence_json_path)
                VALUES ('{_esc(prompt_id)}', '{_esc(stakeholder_id)}', '{_esc(now)}', '{_esc(str(rel_persona))}', '{_esc(query)}', '{_esc(str(rel_ev))}');
                """
            )
            repo.add([repo.path / rel_ev, repo.path / rel_persona])
            repo.commit(f"prompt: {stakeholder_id} {prompt_id}")
        except Exception:
            pass

    return prompt_md


def _render_prompt_md(
    *,
    stakeholder_id: str,
    persona_md: str,
    persona_rubric_md: str,
    query: str,
    evidence: list[Evidence],
    generated_at: str,
) -> str:
    ev_blocks = "\n\n".join([e.format_markdown() for e in evidence]) if evidence else "_No evidence found._"
    rubric_block = persona_rubric_md.strip() or "_No structured rubric found (stakeforge_persona frontmatter)._"
    return f"""# StakeForge Persona Prompt (R2)

**stakeholder_id:** `{stakeholder_id}`  
**generated_at:** `{generated_at}`  
**query:** {query}

---

## Reply rules (eval / GEPA)

- Stay in character per the persona section.
- When you use information from evidence, cite it inline using **exactly** `CITE[<evidence_id>]` tokens shown under each block (example: `CITE[fts:abc123]`).
- Do not invent facts; if evidence is thin, say what is unknown and what you would validate next.
- Avoid claims that contradict evidence or add unstoppable guarantees unless evidence supports them.

---

## Stakeholder rubric (structured)

{rubric_block}

---

## Static persona (R1)

{persona_md}

---

## Evidence (R2: PageIndex + DuckDB FTS)

{ev_blocks}
"""


def _stable_id(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\x1f")
    return h.hexdigest()[:16]


def _copy_into_dolt(repo: DoltRepo, src: Path, *, dst_rel: Path) -> Path:
    dst = repo.path / dst_rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(src.read_bytes())
    return dst_rel


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "''")

