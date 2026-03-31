from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from stakeforge.paths import StakeForgePaths
from stakeforge.retrieve import retrieve
from stakeforge.runtime import StakeForgeConfig, load_config_from_env_and_args
from stakeforge.store import ingest_markdown
from stakeforge.prompt import build_persona_prompt


def _cmd_eval_extract(args: argparse.Namespace) -> int:
    from stakeforge.eval_extract import append_case_jsonl

    append_case_jsonl(Path(args.notes).resolve(), Path(args.out).resolve())
    print(Path(args.out).resolve())
    return 0


def _cmd_eval_score(args: argparse.Namespace) -> int:
    from stakeforge.eval_models import EvalCase
    from stakeforge.eval_scorer import score_reply

    raw = Path(args.case).read_text(encoding="utf-8").strip()
    try:
        case = EvalCase.model_validate_json(raw)
    except Exception:
        case = EvalCase.model_validate(json.loads(raw))
    reply = Path(args.reply_file).read_text(encoding="utf-8")
    kwargs = _eval_score_kwargs(args)
    sc = score_reply(case, reply, **kwargs)
    print(json.dumps(sc.model_dump(), indent=2))
    return 0


def _cmd_eval_run(args: argparse.Namespace) -> int:
    from stakeforge.eval_run import average_total, run_dataset

    kwargs = _eval_score_kwargs(args)
    rows = run_dataset(Path(args.dataset).resolve(), Path(args.replies_dir).resolve(), **kwargs)
    summary = {"average_score": average_total(rows), "cases": rows}
    print(json.dumps(summary, indent=2))
    return 0


def _eval_score_kwargs(args: argparse.Namespace) -> dict:
    kwargs: dict = {"persona_base": Path(args.persona_base).resolve()}
    if getattr(args, "llm_rubric", False):
        kwargs["llm_rubric"] = True
        if getattr(args, "rubric_model", None):
            kwargs["rubric_model"] = args.rubric_model
        if getattr(args, "rubric_api_key", None):
            kwargs["rubric_api_key"] = args.rubric_api_key
        if getattr(args, "rubric_base_url", None):
            kwargs["rubric_base_url"] = args.rubric_base_url
    return kwargs


def _add_eval_rubric_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--llm-rubric",
        action="store_true",
        help="Call an OpenAI-compatible chat model for groundedness + persona adherence (needs OPENAI_API_KEY unless --rubric-api-key).",
    )
    parser.add_argument(
        "--rubric-model",
        default=None,
        help="Model id (default: $STAKEFORGE_RUBRIC_MODEL or gpt-4o-mini).",
    )
    parser.add_argument(
        "--rubric-api-key",
        default=None,
        help="API key (default: $OPENAI_API_KEY).",
    )
    parser.add_argument(
        "--rubric-base-url",
        default=None,
        help="API base URL (default: $OPENAI_BASE_URL or https://api.openai.com).",
    )
    parser.add_argument(
        "--persona-base",
        default=".",
        help="Directory to resolve persona_md paths from eval cases (default: cwd).",
    )


def _cmd_init(args: argparse.Namespace) -> int:
    paths = StakeForgePaths(root=Path(args.root).resolve())
    paths.ensure_dirs()
    print(str(paths.root))
    return 0


def _cmd_ingest(args: argparse.Namespace) -> int:
    cfg = load_config_from_env_and_args(args)
    paths = StakeForgePaths(root=Path(args.root).resolve())
    paths.ensure_dirs()

    ingest_markdown(
        cfg=cfg,
        paths=paths,
        stakeholder_id=args.stakeholder_id,
        md_path=Path(args.md_path).resolve(),
        source_uri=args.source_uri,
        commit_message=args.commit_message,
    )
    return 0


def _cmd_retrieve(args: argparse.Namespace) -> int:
    cfg = load_config_from_env_and_args(args)
    paths = StakeForgePaths(root=Path(args.root).resolve())
    paths.ensure_dirs()

    ev = retrieve(
        cfg=cfg,
        paths=paths,
        stakeholder_id=args.stakeholder_id,
        query=args.query,
        top_k=args.top_k,
    )
    if args.format == "json":
        print(json.dumps([e.model_dump() for e in ev], indent=2))
    else:
        for e in ev:
            print(e.format_markdown())
            print()
    return 0


def _cmd_build_prompt(args: argparse.Namespace) -> int:
    cfg = load_config_from_env_and_args(args)
    paths = StakeForgePaths(root=Path(args.root).resolve())
    paths.ensure_dirs()

    evidence = retrieve(
        cfg=cfg,
        paths=paths,
        stakeholder_id=args.stakeholder_id,
        query=args.query,
        top_k=args.top_k,
    )
    prompt_md = build_persona_prompt(
        cfg=cfg,
        paths=paths,
        stakeholder_id=args.stakeholder_id,
        persona_md_path=Path(args.persona_md).resolve(),
        query=args.query,
        evidence=evidence,
    )
    if args.out:
        Path(args.out).write_text(prompt_md, encoding="utf-8")
    else:
        print(prompt_md)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="stakeforge")
    p.add_argument(
        "--root",
        default=os.environ.get("STAKEFORGE_ROOT", ".stakeforge"),
        help="StakeForge workspace root (default: .stakeforge or $STAKEFORGE_ROOT).",
    )
    p.add_argument(
        "--use-fts",
        default=os.environ.get("STAKEFORGE_USE_FTS", "1"),
        choices=["0", "1"],
        help="Enable DuckDB FTS leg (1/0).",
    )
    p.add_argument(
        "--use-pageindex",
        default=os.environ.get("STAKEFORGE_USE_PAGEINDEX", "1"),
        choices=["0", "1"],
        help="Enable PageIndex leg (1/0).",
    )
    p.add_argument(
        "--token-budget",
        default=os.environ.get("STAKEFORGE_TOKEN_BUDGET", "1200"),
        help="Max tokens of evidence returned (approx).",
    )
    p.add_argument(
        "--max-tokens-per-source",
        default=os.environ.get("STAKEFORGE_MAX_TOKENS_PER_SOURCE", "400"),
        help="Max tokens per source_uri (approx).",
    )
    p.add_argument(
        "--dolt",
        default=os.environ.get("STAKEFORGE_DOLT", "auto"),
        choices=["auto", "on", "off"],
        help="Use Dolt for versioned storage (auto/on/off).",
    )

    sub = p.add_subparsers(dest="cmd", required=True)

    s_init = sub.add_parser("init", help="Initialize a StakeForge workspace root.")
    s_init.set_defaults(func=_cmd_init)

    s_ingest = sub.add_parser("ingest", help="Ingest a markdown source into R2 stores.")
    s_ingest.add_argument("--stakeholder-id", required=True)
    s_ingest.add_argument("--md-path", required=True)
    s_ingest.add_argument("--source-uri", default=None)
    s_ingest.add_argument(
        "--commit-message",
        default=None,
        help="Commit message when Dolt is enabled (default autogenerated).",
    )
    s_ingest.set_defaults(func=_cmd_ingest)

    s_ret = sub.add_parser("retrieve", help="Hybrid retrieval returning cited evidence blocks.")
    s_ret.add_argument("--stakeholder-id", required=True)
    s_ret.add_argument("--query", required=True)
    s_ret.add_argument("--top-k", type=int, default=8)
    s_ret.add_argument("--format", choices=["md", "json"], default="md")
    s_ret.set_defaults(func=_cmd_retrieve)

    s_bp = sub.add_parser("build-prompt", help="Build persona prompt = static persona + evidence.")
    s_bp.add_argument("--stakeholder-id", required=True)
    s_bp.add_argument("--persona-md", required=True, help="R1-style stakeholder markdown file.")
    s_bp.add_argument("--query", required=True)
    s_bp.add_argument("--top-k", type=int, default=8)
    s_bp.add_argument("--out", default=None, help="Write prompt markdown to path instead of stdout.")
    s_bp.set_defaults(func=_cmd_build_prompt)

    s_eval = sub.add_parser("eval", help="Eval dataset tools (GEPA-oriented scoring).")
    eval_sub = s_eval.add_subparsers(dest="eval_cmd", required=True)

    e_ext = eval_sub.add_parser("extract", help="Append one EvalCase (from interview markdown frontmatter) to JSONL.")
    e_ext.add_argument("--notes", required=True, help="Interview notes .md with YAML frontmatter (stakeforge_eval).")
    e_ext.add_argument("--out", required=True, help="Path to cases.jsonl (appends one line).")
    e_ext.set_defaults(func=_cmd_eval_extract)

    e_sc = eval_sub.add_parser("score", help="Score a single reply against one EvalCase JSON.")
    e_sc.add_argument("--case", required=True, help="Path to one-line or pretty JSON EvalCase file.")
    e_sc.add_argument("--reply-file", required=True)
    _add_eval_rubric_args(e_sc)
    e_sc.set_defaults(func=_cmd_eval_score)

    e_run = eval_sub.add_parser("run", help="Score all cases; replies_dir must contain <case_id>.txt or .md")
    e_run.add_argument("--dataset", required=True, help="cases.jsonl")
    e_run.add_argument("--replies-dir", required=True)
    _add_eval_rubric_args(e_run)
    e_run.set_defaults(func=_cmd_eval_run)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except BrokenPipeError:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

