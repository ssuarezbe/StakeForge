from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from stakeforge.models import Evidence


class EvalEvidenceItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_id: Optional[str] = None
    source_uri: str = ""
    heading_path: str = ""
    text: str = ""


class EvalTask(BaseModel):
    model_config = ConfigDict(frozen=True)

    reply_type: Literal["stakeholder_reply"] = "stakeholder_reply"
    must_cite: bool = True
    max_words: int = 250


class EvalExpected(BaseModel):
    model_config = ConfigDict(frozen=True)

    must_include_citations_to: list[str] = Field(default_factory=list)
    must_not_claim: list[str] = Field(default_factory=list)
    stance: Optional[str] = None
    decision_style: Optional[str] = None
    key_points: list[str] = Field(default_factory=list)
    must_push_back: Optional[bool] = None
    pushback_on: Optional[str] = None


class EvalCase(BaseModel):
    model_config = ConfigDict(frozen=True)

    case_id: str
    stakeholder_id: str
    persona_md: str = ""
    query: str
    evidence: list[Evidence] = Field(default_factory=list)
    task: EvalTask = Field(default_factory=EvalTask)
    expected: EvalExpected = Field(default_factory=EvalExpected)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LlmRubricResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    groundedness: float = Field(ge=0.0, le=1.0, description="Factual claims in the reply supported by evidence.")
    persona_adherence: float = Field(
        ge=0.0,
        le=1.0,
        description="Reply matches the stakeholder persona (tone, constraints, role).",
    )
    pushback_quality: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="If applicable, did the stakeholder push back appropriately (e.g. on budget increase) per persona rubric?",
    )
    rationale: str = ""
    violations: list[str] = Field(default_factory=list)
    model: str = ""


class EvalScores(BaseModel):
    model_config = ConfigDict(frozen=True)

    cite_coverage: float
    cite_validity: float
    cite_composite: float
    forbidden_penalty: float
    key_point_coverage: float
    stance_heuristic: float
    total: float
    deterministic_total: float = 0.0
    llm_groundedness: float | None = None
    llm_persona_adherence: float | None = None
    llm_pushback_quality: float | None = None
    llm_composite: float | None = None
    llm_rationale: str | None = None
    llm_violations: list[str] | None = None
    llm_model: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
