# 05 — Hybrid retrieval

Release 2 requires **two complementary recall mechanisms** and a **merge policy**. StakeForge implements:

1. **DuckDB full-text search (FTS)** — excellent for names, dates, acronyms, exact phrases.
2. **PageIndex-style tree navigation** — structure-first recall over Markdown headings (vectorless).
3. **Merge** — union candidates, dedupe spans, normalize scores, apply **token budgets**.

## Conceptual picture

```mermaid
flowchart TB
  subgraph leg1 [Lexical leg]
    Q1[User query] --> FTS[DuckDB FTS BM25 via match_bm25]
    FTS --> H1[Passage hits]
  end
  subgraph leg2 [Structure leg]
    Q1 --> PI[Load tree JSON per source]
    PI --> TW[Keyword overlap on titles + node text]
    TW --> H2[Node hits]
  end
  H1 --> POOL[Candidate pool]
  H2 --> POOL
  POOL --> DED[Dedupe by source + heading + text hash]
  DED --> BUD[Per-turn + per-source token budget]
  BUD --> OUT[Evidence list]
```

## Score fusion (intuition)

```mermaid
flowchart LR
  subgraph norm [Normalize within leg]
    A[FTS raw score]
    B[Tree raw score]
  end
  A --> NA[divide by max FTS]
  B --> NB[0.6 times max tree]
  NA --> SUM[Comparable contribution]
  NB --> SUM
```

- **FTS** contributes up to **`1.0`** after max-normalization.
- **PageIndex leg** contributes up to **`0.6`** after max-normalization so headings guide, but strong lexical hits still surface.

Exact numbers live in `src/stakeforge/retrieve.py`; the diagram expresses intent.

## Dedupe

Candidates that share the same **source**, **heading path**, and **text hash** collapse to one entry so you do not double-count the same span from both legs.

```mermaid
flowchart LR
  C1[fts hit span] --> K{same span as tree hit?}
  C2[tree hit span] --> K
  K -->|yes| ONE[Keep higher fused score]
  K -->|no| BOTH[Keep both]
```

## Token budgeting

Two knobs matter:

- **`token_budget`** — cap total evidence size for the prompt (approximate tokens).
- **`max_tokens_per_source`** — prevent one long doc from eating the whole budget.

```mermaid
flowchart TD
  L[Sorted by fused score] --> T{Fits budget?}
  T -->|no| TR[Truncate with ellipsis]
  T -->|yes| KEEP[Keep passage]
  TR --> KEEP
```

## Turning legs off

```mermaid
flowchart LR
  A[STAKEFORGE_USE_FTS=0] --> R[retrieve]
  B[STAKEFORGE_USE_PAGEINDEX=0] --> R
```

Use this for debugging (“is FTS hurting?”) without maintaining two code paths.

## Next document

[06 — Evaluation and rubric](06-evaluation-and-rubric.md)
