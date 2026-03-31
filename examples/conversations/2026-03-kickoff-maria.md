# Kickoff interview — Maria Chen (Ops)

**Date:** 2026-03-12  
**Attendees:** Maria Chen (VP Ops), product lead, SRE lead  
**Recording ref:** `teams/2026-03-12-ops-kickoff` (not reproduced here)

## Why this initiative exists

Maria opened by framing the problem in units: late packages spike when the routing service degrades during peaks. She cares about **OTIF** and **cost per package**, not abstraction layers.

> “Every minute that service flickers, I’m paying overtime and burning trust with our biggest retail accounts.”

## Timeline and board pressure

Maria stated that the **CFO wants a credible ROI story before the Q2 board readout**. She is explicitly **not** asking for a science project—she wants a path that finance can model.

She said she needs **ROI numbers within six months** or she **cannot sponsor** additional headcount on the reliability workstream. She stressed that the number must be defensible: assumptions named, ranges shown, and a checkpoint at month three.

## Risk posture

Maria classified the org as “**measure twice, cut once**” for customer-facing changes. She wants **pilots in one region** before national rollout, and a written rollback that has been rehearsed.

She challenged the team on a prior incident where staging was skipped to meet a marketing deadline. That story is now her shorthand for “technical debt interest payments.”

## Dependencies she worries about

- Carrier integrations (peak behavior differs from contract testing).
- Data quality on lane-level cost attribution (Finance uses a different cube than Ops).

## What she asked from the team

1. A **phased plan** with owners and dates.
2. A **3-month checkpoint** with measurable leading indicators (error budget, p95 latency, incident counts).
3. Plain-language **tradeoff slides** she can reuse with her boss without re-explaining architecture.

## Closing sentiment

Maria ended on a constructive note: she will champion the work if the team meets her bar for rigor. She does not reward swagger; she rewards **evidence and follow-through**.
