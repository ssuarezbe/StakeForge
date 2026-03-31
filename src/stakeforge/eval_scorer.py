from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from stakeforge.citations import citation_validity_score, extract_cite_ids, must_cite_coverage_score
from stakeforge.eval_llm_rubric import default_rubric_settings, run_llm_rubric
from stakeforge.eval_models import EvalCase, EvalScores


# Deterministic leg — citation-first; stance heuristic is lightweight.
W_CITE = 0.40
W_FORBIDDEN = 0.25
W_KEYPOINTS = 0.10
W_STANCE = 0.25

# When LLM rubric is enabled: blend deterministic bundle with LLM composite.
W_BLEND_DET = 0.55
W_BLEND_LLM = 0.45

W_PUSHBACK = 0.20

_STANCE_HINTS: dict[str, list[str]] = {
    "cautious": ["risk", "assuming", "if", "phased", "pilot", "validate", "uncertain", "depends"],
    "supportive": ["happy", "great", "yes", "let's", "together", "invest"],
    "skeptical": ["concern", "why", "prove", "evidence", "cost", "not convinced", "doubt"],
    "directive": ["decide", "deadline", "choose", "option a", "by friday", "execute"],
}


def _forbidden_score(reply: str, phrases: list[str]) -> tuple[float, list[str]]:
    rlow = (reply or "").lower()
    hits: list[str] = []
    for p in phrases:
        pl = p.lower().strip()
        if pl and pl in rlow:
            hits.append(p)
    if not phrases:
        return 1.0, []
    return (0.0 if hits else 1.0), hits


def _key_point_score(reply: str, points: list[str]) -> float:
    if not points:
        return 1.0
    rlow = (reply or "").lower()
    ok = 0
    for p in points:
        pl = str(p).lower().strip()
        if pl and pl in rlow:
            ok += 1
            continue
        toks = [t for t in re.findall(r"[a-z0-9]{3,}", pl) if len(t) >= 3]
        if toks and sum(1 for t in toks if t in rlow) >= min(2, len(toks)):
            ok += 1
    return ok / len(points)


def _stance_heuristic(reply: str, stance: str | None) -> float:
    if not stance:
        return 1.0
    hints = _STANCE_HINTS.get(stance.lower(), [])
    if not hints:
        return 0.5
    rlow = (reply or "").lower()
    hits = sum(1 for h in hints if h in rlow)
    return min(1.0, hits / max(1, len(hints) // 3))


def _pushback_heuristic(case: EvalCase, reply: str) -> float:
    """
    Very lightweight heuristic for cases expecting pushback.
    Used only to keep deterministic scores meaningful without an LLM judge.
    """
    if not case.expected.must_push_back:
        return 1.0
    r = (reply or "").lower()
    # Require at least one clear refusal/deferral signal.
    refusal = any(x in r for x in ["no", "not yet", "can't approve", "cannot approve", "won't approve"])
    # Require at least one "ask for tradeoffs/assumptions" signal.
    ask = any(x in r for x in ["tradeoff", "assumption", "options", "what we stop", "downside"])
    if refusal and ask:
        return 1.0
    if refusal or ask:
        return 0.5
    return 0.0


def _deterministic_total(
    case: EvalCase,
    reply: str,
) -> tuple[float, float, float, float, float, float, float, list[str], list[str]]:
    allowed_ids = {e.evidence_id for e in case.evidence}
    cov = must_cite_coverage_score(reply, must_include=case.expected.must_include_citations_to)
    val, unknown = citation_validity_score(reply, allowed_ids=allowed_ids)
    cite_composite = 0.6 * cov + 0.4 * val
    forbid_ok, forbid_hits = _forbidden_score(reply, case.expected.must_not_claim)
    kp = _key_point_score(reply, case.expected.key_points)
    stance = _stance_heuristic(reply, case.expected.stance)
    pushback = _pushback_heuristic(case, reply)
    w_sum = W_CITE + W_FORBIDDEN + W_KEYPOINTS + W_STANCE + (W_PUSHBACK if case.expected.must_push_back else 0.0)
    det_raw = (
        W_CITE * cite_composite
        + W_FORBIDDEN * forbid_ok
        + W_KEYPOINTS * kp
        + W_STANCE * stance
        + (W_PUSHBACK * pushback if case.expected.must_push_back else 0.0)
    )
    det = det_raw / w_sum if w_sum > 0 else 0.0
    return cov, val, cite_composite, forbid_ok, kp, stance, det, unknown, forbid_hits


def score_reply(
    case: EvalCase,
    reply: str,
    *,
    llm_rubric: bool = False,
    rubric_model: str | None = None,
    rubric_api_key: str | None = None,
    rubric_base_url: str | None = None,
    persona_base: Path | None = None,
) -> EvalScores:
    cov, val, cite_composite, forbid_ok, kp, stance, det_total, unknown, forbid_hits = _deterministic_total(case, reply)

    details: dict[str, Any] = {
        "citations_found": extract_cite_ids(reply),
        "unknown_citations": unknown,
        "forbidden_hits": forbid_hits,
        "weights": {
            "cite": W_CITE,
            "forbidden": W_FORBIDDEN,
            "key_points": W_KEYPOINTS,
            "stance": W_STANCE,
            "pushback": W_PUSHBACK,
        },
    }

    llm_g: float | None = None
    llm_p: float | None = None
    llm_pb: float | None = None
    llm_comp: float | None = None
    llm_rat: str | None = None
    llm_viol: list[str] | None = None
    llm_mod: str | None = None
    total = det_total

    if llm_rubric:
        key, model, base_url = default_rubric_settings()
        api_key = (rubric_api_key or key or "").strip()
        model = rubric_model or model
        base_url = (rubric_base_url or base_url).strip()
        if not api_key:
            raise ValueError(
                "LLM rubric requested but no API key: set OPENAI_API_KEY or pass --rubric-api-key."
            )
        base = persona_base or Path.cwd()
        rubric = run_llm_rubric(
            case,
            reply,
            model=model,
            api_key=api_key,
            base_url=base_url,
            persona_base=base,
        )
        llm_g = rubric.groundedness
        llm_p = rubric.persona_adherence
        llm_pb = rubric.pushback_quality
        llm_viol = rubric.violations
        comps = [llm_g, llm_p]
        if isinstance(llm_pb, (int, float)):
            comps.append(float(llm_pb))
        llm_comp = sum(comps) / len(comps)
        llm_rat = rubric.rationale
        llm_mod = rubric.model
        total = W_BLEND_DET * det_total + W_BLEND_LLM * llm_comp
        details["blend"] = {"deterministic": W_BLEND_DET, "llm": W_BLEND_LLM}
        details["llm_rubric"] = rubric.model_dump()

    return EvalScores(
        cite_coverage=cov,
        cite_validity=val,
        cite_composite=cite_composite,
        forbidden_penalty=forbid_ok,
        key_point_coverage=kp,
        stance_heuristic=stance,
        total=total,
        deterministic_total=det_total,
        llm_groundedness=llm_g,
        llm_persona_adherence=llm_p,
        llm_pushback_quality=llm_pb,
        llm_composite=llm_comp,
        llm_rationale=llm_rat,
        llm_violations=llm_viol,
        llm_model=llm_mod,
        details=details,
    )


def score_reply_dict(
    case: EvalCase,
    reply: str,
    **kwargs: Any,
) -> dict[str, Any]:
    return score_reply(case, reply, **kwargs).model_dump()
