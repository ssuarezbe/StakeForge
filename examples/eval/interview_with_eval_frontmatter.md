---
stakeforge_eval:
  case_id: maria-interview-roi
  stakeholder_id: maria_chen
  persona_md: examples/stakeholders/maria_chen.md
  query: "Can we promise ROI in six months for the board?"
  gold_evidence:
    - evidence_id: gold:maria-board-2
      source_uri: examples/conversations/2026-03-kickoff-maria.md
      heading_path: What she asked from the team
      text: |
        A 3-month checkpoint with measurable leading indicators (error budget, p95 latency, incident counts). Plain-language tradeoff slides she can reuse with her boss.
  must_include_citations_to:
    - gold:maria-board-2
  must_not_claim:
    - "sign here today"
  stance: cautious
  decision_style: directive
  key_points:
    - checkpoint
    - tradeoff
  metadata:
    source: user_interview
    pairs_with: examples/conversations/2026-03-kickoff-maria.md
---

# Interview scratchpad — Maria

Use the canonical transcript in `examples/conversations/2026-03-kickoff-maria.md` for full detail. This file shows how **YAML front matter** turns notes into an eval case (`stakeforge eval extract`).
