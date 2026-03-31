from __future__ import annotations

from pathlib import Path
from typing import Optional

from stakeforge.eval_extract import parse_frontmatter  # shared YAML frontmatter parser
from stakeforge.persona_schema import StakeforgePersona


def load_persona_markdown_with_rubric(persona_md_path: Path) -> tuple[str, Optional[StakeforgePersona]]:
    """
    Returns (persona_body_markdown, stakeforge_persona_rubric).

    - If YAML frontmatter contains `stakeforge_persona: {...}`, it is parsed.
    - Persona body is the markdown after the frontmatter block.
    - If no frontmatter exists, rubric is None and body is full file.
    """
    raw = persona_md_path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(raw)
    if not fm:
        return raw.strip(), None
    blob = fm.get("stakeforge_persona")
    if not isinstance(blob, dict):
        return body.strip(), None
    try:
        rubric = StakeforgePersona.model_validate(blob)
    except Exception:
        rubric = None
    return body.strip(), rubric


def load_persona_rubric_from_path(persona_md: str, base: Path) -> Optional[StakeforgePersona]:
    p = Path(persona_md)
    if not p.is_absolute():
        p = (base / p).resolve()
    if not p.is_file():
        return None
    _body, rub = load_persona_markdown_with_rubric(p)
    return rub

