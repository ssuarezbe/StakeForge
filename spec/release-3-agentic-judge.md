# Release 3 — Agentic Judge for Stakeholder Alignment

**Iteration:** 3  
**Codename:** R3  
**Depends on:** Release 1 (`spec/release-1-prompt-mvp-tinytroupe.md`) + Release 2 (`spec/release-2-pageindex-duckdb-rag.md`)  
**Maps to:** `why.md` — Phase 4 (Agentic Judge for Stakeholder Alignment)

---

## 1. Release goal

Automatically **evaluate** whether a proposal (or design document) **addresses each stakeholder’s** documented concerns, using:

- **Structured test definitions** (promptfoo-style YAML or equivalent) with **LLM rubrics**, as sketched in `why.md`.
- An **agentic judge** option that can **pull evidence** via Release 2 retrieval (PageIndex + DuckDB FTS on Dolt-versioned corpora) so verdicts are grounded in **what stakeholders actually said**, not only static persona summaries.

---

## 2. Product outcome

Users can:

1. Define **per-stakeholder rubrics** derived from R1 markdown (power/interest, quotes, risks, constraints).
2. Run a **batch evaluator**: `proposal × stakeholder × rubric` → pass/fail (or score) + rationale.
3. Optionally run an **agentic** path: judge retrieves citations from the R2 stack before scoring.
4. **Record** each run in **Dolt** (or equivalent versioned store) with links to **corpus commit** and **persona prompt version** for regression analysis.

---

## 3. Scope

### In scope

- `judge/stakeholder-alignment.yaml` (or parallel structure) with variables such as:

  - `proposal`
  - `stakeholder_profile` (from R1)
  - optional `retrieved_evidence` (filled by agentic step)

- CLI or CI-friendly **runner** producing a **JSON report** (and optional Markdown summary).
- **Minimal dashboard:** Markdown table or static HTML summarizing scores by stakeholder and run id.
- **Dolt table** `judge_runs` (or equivalent): run id, timestamp, corpus commit hash, persona template hash, per-stakeholder results, aggregate score.

### Out of scope

- New retrieval backends (extend R2 only if required for judge quality; prefer configuration).
- Full product UI beyond static report artifacts.

---

## 4. Rubric design rules

- Assertions use **observable criteria** (e.g. “states ROI horizon ≤ 6 months” vs “is persuasive”).
- Include **negative tests** where appropriate (e.g. must not promise big-bang rollout for risk-averse stakeholders).
- Rubrics are **versioned in git**; optional mirror of rubric version in Dolt for alignment with `judge_runs`.

---

## 5. Deliverables checklist

| ID | Deliverable | Release criterion |
|----|-------------|-------------------|
| R3-01 | Stakeholder alignment test suite | At least one test per stakeholder concern in the pilot; uses `llm-rubric` or equivalent. |
| R3-02 | Evaluation runner | Single command produces JSON report; exit code policy documented for CI. |
| R3-03 | Agentic judge path (optional flag) | When enabled, retrieves evidence via R2 before scoring; citations appear in rationale. |
| R3-04 | `judge_runs` in Dolt | Persisted runs with corpus/persona version pointers; query examples documented. |
| R3-05 | Summary artifact | Human-readable rollup by stakeholder and run. |

---

## 6. Acceptance tests

- On a pilot set with **known-good** and **known-bad** proposals, judge ordering matches **human expectation** at or above a team-agreed threshold.
- Failed tests show **which rubric failed** and, if agentic mode is on, **which evidence** supported the verdict.
- Re-running the same proposal against an **older Dolt corpus commit** can demonstrate **score drift** when stakeholder data changes (documented example).

---

## 7. Release notes (what we tell users)

**R3 delivers:** automated **stakeholder alignment checks** over proposals, with optional **evidence-grounded** judging tied to **versioned** stakeholder corpora from R2. **R1** personas and **R2** retrieval remain the upstream sources of truth.

---

## 8. Reference implementation hints (non-normative)

Tools listed in `why.md` (e.g. [promptfoo](https://github.com/promptfoo/promptfoo), [quotient-ai/judges](https://github.com/quotient-ai/judges)) may be adopted wholesale if they meet R3 deliverables and Dolt logging requirements.
