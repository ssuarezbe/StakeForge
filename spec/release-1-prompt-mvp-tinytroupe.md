# Release 1 — Prompt-Only MVP + TinyTroupe Integration

**Iteration:** 1  
**Codename:** R1  
**Depends on:** None  
**Maps to:** `why.md` — Phase 1 (Prompt-Only MVP) and Phase 2 (TinyTroupe Integration)

---

## 1. Release goal

Ship a **markdown-native stakeholder kit** that anyone can use with a generic chat LLM, plus a **small code path** that turns those files into **TinyTroupe** personas and runs **multi-stakeholder simulations** with exportable traces.

---

## 2. Product outcome

Users can:

1. Maintain stakeholders as **repo files** (canvas + per-stakeholder markdown).
2. Use a **documented meta-prompt** (`generator.md`) to normalize raw notes into the stakeholder template.
3. **Convert** stakeholder markdown to TinyTroupe-compatible JSON and run **TinyWorld** scenarios (e.g. present a proposal, collect objections).
4. **Save** simulation outputs as artifacts (markdown or JSON summaries).

---

## 3. Scope

### In scope

- Directory layout and templates as described in `why.md`:

  - `canvas.md`
  - `stakeholders/*.md` (structured template: role/power/interest, quadrant, ingested context, persona prompt)
  - `conversations/` (convention for pasted meeting notes)
  - `generator.md` (canvas/notes → stakeholder file)
  - `README.md` (copy-paste workflow for Phase 1)

- **Converter** (script/CLI): `stakeholders/*.md` → TinyPerson JSON (validated, stable field mapping).
- **TinyWorld** scenario: at least one documented recipe + how to extract structured outcomes.
- Optional **TinyPersonFactory** enrichment from transcripts when inputs exceed a defined threshold (document the rule).

### Out of scope (later releases)

- Retrieval/RAG, databases, judges, hosted UI, Open WebUI, vector or hybrid search.

---

## 4. Technical requirements

- Phase 1 remains **zero application code** except what is strictly needed for Phase 2 (converter + runner docs).
- Pin **TinyTroupe** and **Python** versions in project docs or lockfile.
- Converter behavior must be **deterministic** for a given markdown input (no hidden network calls in the converter itself).

### Optional (non-blocking for R1)

- **PageIndex-friendly markdown:** encourage consistent `#` heading hierarchy in long `conversations/*.md` files so corpora are ready for Release 2.
- **Dolt:** optional snapshot of file hashes or contents for audit; not required to ship R1.

---

## 5. Deliverables checklist

| ID | Deliverable | Release criterion |
|----|-------------|-------------------|
| R1-01 | `canvas.md` + stakeholder template spec | Template documented with at least one complete example stakeholder. |
| R1-02 | `generator.md` | Produces valid stakeholder markdown from pasted raw inputs; README explains usage. |
| R1-03 | `conversations/` convention | Naming, dates, and paste guidelines documented. |
| R1-04 | Converter CLI/script | Emits TinyPerson JSON per file; reports validation errors clearly. |
| R1-05 | TinyWorld recipe + trace export | One scenario documented; output artifact format defined. |

---

## 6. Acceptance tests

- A new stakeholder can be onboarded **using only** markdown + the generator prompt (no custom app).
- Converter output loads in TinyTroupe **without hand-editing** JSON for the happy path.
- One TinyWorld run produces a **stored trace** and a **short per-stakeholder summary** (stance / concerns).

---

## 7. Release notes (what we tell users)

**R1 delivers:** file-based stakeholder personas, a generator prompt for consistency, and scripted TinyTroupe simulations. There is **no** automated retrieval or alignment scoring yet.

---

## 8. Next release handoff

Release 2 assumes R1 markdown and optional long-form `conversations/*.md` exist with stable structure. See `spec/release-2-pageindex-duckdb-rag.md`.
