# StakeForge

AI-powered stakeholder simulation toolkit — from canvas to conversation to alignment scoring.

## Documentation

- **[Full guides & diagrams (`docs/`)](docs/README.md)** — architecture, workflows, retrieval, evaluation, structured persona rubric, Dolt, Podman verify.
- **[Runnable examples (`examples/`)](examples/README.md)** — Maria Chen persona, kickoff transcript, eval suites.

## Podman + Task (quick verification in a container)

Requires [Task](https://taskfile.dev/installation/) and [Podman](https://podman.io/). From the repo root:

```bash
task verify
```

This builds `localhost/stakeforge:dev` and runs eval suites, ingest/retrieve/build-prompt, and `eval extract`. Details: [docs/09-podman-taskfile.md](docs/09-podman-taskfile.md).

Quick visual index: [docs/00-visual-summary.md](docs/00-visual-summary.md).

## R2 CLI (quick)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .

stakeforge init
stakeforge ingest --stakeholder-id maria_chen \
  --md-path examples/conversations/2026-03-kickoff-maria.md
stakeforge build-prompt --stakeholder-id maria_chen \
  --persona-md examples/stakeholders/maria_chen.md \
  --query "What matters most on ROI and checkpoints?"
```

Replies should cite evidence inline as `CITE[<evidence_id>]` (shown in each evidence block of the generated prompt).

## GEPA-oriented eval

1. **Dataset JSONL**: one `EvalCase` per line — see `examples/eval/sample_cases.jsonl` or `cases.full.jsonl`.
2. **From interview notes**: YAML front matter with `stakeforge_eval:` — see `examples/eval/interview_with_eval_frontmatter.md`, then:

   ```bash
   stakeforge eval extract --notes examples/eval/interview_with_eval_frontmatter.md --out my_cases.jsonl
   ```

3. **Score one reply**:

   ```bash
   stakeforge eval score --case my_case.json --reply-file reply.txt --persona-base .
   ```

4. **Run a suite** (expects `replies/<case_id>.txt` or `.md`):

   ```bash
   stakeforge eval run --dataset examples/eval/cases.full.jsonl --replies-dir examples/eval/replies --persona-base .
   ```

5. **LLM rubric** (OpenAI-compatible Chat Completions): blends deterministic scoring with model-graded **groundedness**, **persona adherence**, and (when applicable) **pushback quality**. Structured `stakeforge_persona:` in the persona file is passed to the judge when present — see [docs/10-structured-persona-rubric.md](docs/10-structured-persona-rubric.md).

   ```bash
   export OPENAI_API_KEY=...
   # optional: export OPENAI_BASE_URL=... export STAKEFORGE_RUBRIC_MODEL=gpt-4o-mini

   stakeforge eval score --case my_case.json --reply-file reply.txt --llm-rubric --persona-base .
   stakeforge eval run --dataset cases.jsonl --replies-dir replies/ --llm-rubric --persona-base .
   ```

   Final score: `0.55 * deterministic_total + 0.45 * llm_composite`, where `llm_composite` is the mean of `groundedness`, `persona_adherence`, and `pushback_quality` when the latter is returned.
