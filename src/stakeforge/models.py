from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from stakeforge.citations import cite_token


class Evidence(BaseModel):
    evidence_id: str
    stakeholder_id: str
    source_uri: str
    heading_path: str = ""
    text: str

    # Provenance / scoring
    retrieval_leg: Literal["fts", "pageindex", "hybrid"]
    score: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Optional offsets for citation
    start_char: Optional[int] = None
    end_char: Optional[int] = None

    def citation(self) -> str:
        hp = f" > {self.heading_path}" if self.heading_path else ""
        return f"{self.source_uri}{hp}"

    def format_markdown(self) -> str:
        return (
            f"> **Citation:** {self.citation()}\n"
            f"> **Evidence ID:** `{self.evidence_id}`\n"
            f"> **Cite in replies:** {cite_token(self.evidence_id)}\n"
            f"> **Leg:** `{self.retrieval_leg}`  **Score:** {self.score:.4f}\n\n"
            f"{self.text.strip()}\n"
        )


def approx_token_len(text: str) -> int:
    # Heuristic: English token ~ 4 chars. Works well enough for budgeting.
    return max(1, (len(text) + 3) // 4)

