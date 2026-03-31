# 07 — Dolt and reproducibility

Dolt is **optional**. When it works, it gives you a **SQL database you can diff, branch, and time-travel**—useful for “what did this persona know on date X?” narratives.

## Decision tree

```mermaid
flowchart TD
  A[ingest or prompt build] --> B{dolt mode}
  B -->|off| L[Artifacts only in .stakeforge]
  B -->|on| D[Require dolt binary]
  B -->|auto| E{dolt on PATH?}
  E -->|yes| C[Commit snapshots]
  E -->|no| L
```

## What gets committed on ingest

Simplified view:

```mermaid
flowchart LR
  SRC[sources/stakeholder/file.md] --> R[Dolt repo]
  DUCK[artifacts/passages.duckdb] --> R
  PI[artifacts/pageindex/...json] --> R
  SQL[metadata tables] --> R
```

Tables include **sources**, **pageindex_artifacts**, **rebuilds** (see `store.py`).

## Prompt revision logging

When Dolt is on and the repo exists, `build_persona_prompt` may copy:

- Evidence JSON logs
- Persona file snapshot

…and insert a row into **`prompt_revisions`**, then commit.

```mermaid
sequenceDiagram
  participant P as build-prompt
  participant D as Dolt repo
  P->>D: copy logs + persona
  P->>D: INSERT prompt_revisions
  P->>D: dolt commit
```

Failures are intentionally **non-fatal** (network-free CLI still works).

## Practical workflows

### Compare two ingest states

Use Dolt’s native tooling:

```bash
cd .stakeforge/dolt
dolt log --oneline
dolt diff <commit1> <commit2>
```

### Time-travel queries

Dolt supports `AS OF` semantics for SQL reads (consult [Dolt docs](https://docs.dolthub.com/)). StakeForge does not wrap every query yet; the committed **files** remain the portable audit trail.

## When to skip Dolt

```mermaid
flowchart LR
  DEMO[Local demo] --> OFF[dolt off]
  CI[Unit tests] --> OFF
  AUDIT[Regulated audit] --> ON[dolt on]
```

## Next document

[08 — Examples catalog](08-examples-catalog.md)
