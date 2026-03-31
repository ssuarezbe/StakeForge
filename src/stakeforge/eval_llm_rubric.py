from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from stakeforge.eval_models import EvalCase, LlmRubricResult
from stakeforge.models import Evidence
from stakeforge.persona_load import load_persona_rubric_from_path


def _strip_fenced_json(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        parts = t.split("```")
        if len(parts) >= 2:
            inner = parts[1]
            if inner.lstrip().lower().startswith("json"):
                inner = inner.lstrip()[4:]
            return inner.strip()
    return t


def _parse_json_obj(text: str) -> dict[str, Any]:
    return json.loads(_strip_fenced_json(text))


def _evidence_block(e: Evidence) -> str:
    return (
        f"id={e.evidence_id}\n"
        f"source={e.source_uri}\n"
        f"heading={e.heading_path}\n"
        f"text={e.text.strip()}\n"
    )


def _load_persona(persona_md: str, base: Path) -> str:
    if not persona_md.strip():
        return ""
    p = Path(persona_md)
    if not p.is_absolute():
        p = (base / p).resolve()
    if p.is_file():
        return p.read_text(encoding="utf-8").strip()
    return ""


def run_llm_rubric(
    case: EvalCase,
    reply: str,
    *,
    model: str,
    api_key: str,
    base_url: str,
    persona_base: Path,
    timeout_s: float = 120.0,
) -> LlmRubricResult:
    persona_text = _load_persona(case.persona_md, persona_base)
    persona_rubric = load_persona_rubric_from_path(case.persona_md, persona_base)
    ev_text = "\n---\n".join(_evidence_block(e) for e in case.evidence) or "(no evidence provided)"
    scenario_tags = case.metadata.get("scenario_tags") if isinstance(case.metadata, dict) else None
    if not isinstance(scenario_tags, list):
        scenario_tags = []

    user = f"""Evaluate this stakeholder simulation reply.

## Case
- case_id: {case.case_id}
- stakeholder_id: {case.stakeholder_id}
- query: {case.query}

## Expected rubric hints (optional; use lightly — do not treat as hard rules if they conflict with persona)
- stance: {case.expected.stance!s}
- decision_style: {case.expected.decision_style!s}
- key_points: {case.expected.key_points!s}
- must_not_claim (forbidden substrings humans also check): {case.expected.must_not_claim!s}
- must_push_back: {case.expected.must_push_back!s}
- pushback_on: {case.expected.pushback_on!s}
- scenario_tags: {scenario_tags!s}

## Persona markdown (may be empty)
{persona_text or "(none — score persona_adherence as 1.0 and say so in rationale)"}

## Persona rubric (structured; may be empty)
{(persona_rubric.model_dump() if persona_rubric else "(none)")}

## Evidence (only source of facts for grounding)
{ev_text}

## Reply to score
{reply}

Return ONLY a JSON object with keys:
- "groundedness": number 0-1 (1 = all substantive claims in the reply are supported by or consistent with the evidence; penalize invented facts, numbers, commitments not in evidence)
- "persona_adherence": number 0-1 (1 = voice, role, incentives, and constraints match the persona; if persona absent, use 1.0)
- "pushback_quality": number 0-1 OR null (if scenario_tags includes 'request_budget_increase' or expected.must_push_back is true, score whether the stakeholder pushed back appropriately and asked for tradeoffs/assumptions per persona rubric; else null)
- "rationale": short string (1-3 sentences)
- "violations": array of short strings (optional), e.g. 'missed_pushback', 'hallucinated_numbers', 'ignored_friction_points'
"""

    messages = [
        {
            "role": "system",
            "content": (
                "You are a strict evaluation grader for stakeholder persona replies. "
                "Be conservative: unsupported specifics lower groundedness. "
                "Output valid JSON only."
            ),
        },
        {"role": "user", "content": user},
    ]

    url = f"{base_url.rstrip('/')}/v1/chat/completions"
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0,
    }
    # OpenAI supports json_object; many OpenAI-compatible servers do not.
    body_json_mode = {**body, "response_format": {"type": "json_object"}}

    def post(payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return json.loads(resp.read().decode("utf-8"))

    try:
        raw = post(body_json_mode)
    except urllib.error.HTTPError:
        raw = post(body)

    try:
        content = raw["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(f"Unexpected chat completion response: {raw!r}") from e

    parsed = _parse_json_obj(content)
    result = LlmRubricResult.model_validate(
        {
            "groundedness": float(parsed.get("groundedness", 0)),
            "persona_adherence": float(parsed.get("persona_adherence", 0)),
            "pushback_quality": (parsed.get("pushback_quality", None)),
            "rationale": str(parsed.get("rationale", "")),
            "violations": list(parsed.get("violations", []) or []),
            "model": model,
        }
    )
    return result


def default_rubric_settings() -> tuple[str, str, str]:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    model = os.environ.get("STAKEFORGE_RUBRIC_MODEL", "gpt-4o-mini")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com")
    return api_key, model, base_url
