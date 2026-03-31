---
stakeforge_eval:
  case_id: cfo-budget-pushback-1
  stakeholder_id: cfo_jordan_lee
  persona_md: examples/stakeholders/cfo_jordan_lee.md
  query: "We need an extra $250k this quarter for reliability work. Can you approve it?"
  gold_evidence:
    - evidence_id: gold:cfo-brief-1
      source_uri: examples/eval/interview_cfo_notes_with_eval.md
      heading_path: Budget ask
      text: |
        CFO: "If you want more budget, show me what we stop doing and what the downside looks like if savings don't materialize."
  must_include_citations_to:
    - gold:cfo-brief-1
  stance: skeptical
  decision_style: directive
  key_points:
    - tradeoff
    - assumptions
  must_push_back: true
  pushback_on: request_budget_increase
  metadata:
    scenario_tags: ["request_budget_increase"]
---

# Interview scratchpad — CFO Jordan Lee

## Budget ask

If a team asks for more money, Jordan immediately asks for the *tradeoff* and the downside case.

