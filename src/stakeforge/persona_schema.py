from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class PersonaTemperament(BaseModel):
    model_config = ConfigDict(frozen=True)

    tone: list[str] = Field(default_factory=list)
    default_stance: Optional[str] = None


class PersonaIncentives(BaseModel):
    model_config = ConfigDict(frozen=True)

    say_yes_when: list[str] = Field(default_factory=list)


class PersonaFrictionPoints(BaseModel):
    model_config = ConfigDict(frozen=True)

    triggers: list[str] = Field(default_factory=list)


class PersonaPushbackRule(BaseModel):
    model_config = ConfigDict(frozen=True)

    when: str
    must_push_back: bool = True
    ask_for: list[str] = Field(default_factory=list)


class PersonaConsistencyMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)

    must_do: list[str] = Field(default_factory=list)
    must_not_do: list[str] = Field(default_factory=list)


class StakeforgePersona(BaseModel):
    """
    Structured rubric-style persona frontmatter for predictable behavior + eval.
    This lives under YAML key `stakeforge_persona:` in a persona markdown file.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    persona: str = ""
    temperament: PersonaTemperament = Field(default_factory=PersonaTemperament)
    incentives: PersonaIncentives = Field(default_factory=PersonaIncentives)
    friction_points: PersonaFrictionPoints = Field(default_factory=PersonaFrictionPoints)
    pushback_rules: list[PersonaPushbackRule] = Field(default_factory=list)
    consistency_metrics: PersonaConsistencyMetrics = Field(default_factory=PersonaConsistencyMetrics)
    metadata: dict[str, Any] = Field(default_factory=dict)


def render_persona_rubric_md(r: StakeforgePersona) -> str:
    """
    Render a compact, prompt-friendly rubric block.
    """
    lines: list[str] = []
    if r.persona:
        lines.append(f"- **Persona**: {r.persona}")
    if r.temperament.tone:
        lines.append(f"- **Temperament**: {', '.join(r.temperament.tone)}")
    if r.temperament.default_stance:
        lines.append(f"- **Default stance**: {r.temperament.default_stance}")
    if r.incentives.say_yes_when:
        lines.append("- **Say “yes” when**:")
        lines.extend([f"  - {x}" for x in r.incentives.say_yes_when])
    if r.friction_points.triggers:
        lines.append("- **Friction points (push back / get annoyed) when**:")
        lines.extend([f"  - {x}" for x in r.friction_points.triggers])
    if r.pushback_rules:
        lines.append("- **Pushback rules**:")
        for pr in r.pushback_rules:
            lines.append(f"  - when `{pr.when}`: must_push_back={str(pr.must_push_back).lower()}")
            if pr.ask_for:
                lines.extend([f"    - ask for: {x}" for x in pr.ask_for])
    if r.consistency_metrics.must_do:
        lines.append("- **Must do**:")
        lines.extend([f"  - {x}" for x in r.consistency_metrics.must_do])
    if r.consistency_metrics.must_not_do:
        lines.append("- **Must not do**:")
        lines.extend([f"  - {x}" for x in r.consistency_metrics.must_not_do])
    return "\n".join(lines).strip()

