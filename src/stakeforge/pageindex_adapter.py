from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any, Iterable, Optional

from pydantic import BaseModel, ConfigDict

class PageIndexNodeHit(BaseModel):
    model_config = ConfigDict(frozen=True)

    node_id: str
    title_path: str
    text: str
    score: float


def _safe_slug(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "doc"


def build_tree_artifact(md_path: Path, *, out_json_path: Path) -> dict[str, Any]:
    """
    Build a PageIndex-compatible tree JSON artifact.

    If `pageindex` is installed, this uses its markdown pipeline (no summaries, includes node text).
    Otherwise it falls back to a deterministic heading parser that emits the same shape.
    """
    out_json_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        from pageindex.page_index_md import md_to_tree  # type: ignore

        result = asyncio.run(
            md_to_tree(
                md_path=str(md_path),
                if_thinning=False,
                if_add_node_summary="no",
                if_add_node_text="yes",
                if_add_node_id="yes",
                if_add_doc_description="no",
            )
        )
    except Exception:
        result = _fallback_md_to_tree(md_path)

    out_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def load_tree_artifact(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def search_tree(
    tree: dict[str, Any],
    *,
    query: str,
    top_k: int = 6,
) -> list[PageIndexNodeHit]:
    """
    Vectorless structure-aware search:
    score = weighted keyword overlap against title path + text.
    """
    q_terms = _terms(query)
    hits: list[PageIndexNodeHit] = []

    def walk(nodes: Iterable[dict[str, Any]], title_stack: list[str]) -> None:
        for n in nodes:
            title = str(n.get("title", "")).strip()
            node_id = str(n.get("node_id", "")).strip() or "0000"
            text = str(n.get("text", "") or "").strip()
            path = title_stack + ([title] if title else [])
            title_path = " / ".join([p for p in path if p])

            title_score = _overlap_score(_terms(title_path), q_terms)
            text_score = _overlap_score(_terms(text), q_terms)
            score = 2.0 * title_score + 1.0 * text_score
            if score > 0:
                hits.append(PageIndexNodeHit(node_id=node_id, title_path=title_path, text=text, score=score))

            children = n.get("nodes") or []
            if isinstance(children, list) and children:
                walk(children, path)

    structure = tree.get("structure") or []
    if isinstance(structure, list):
        walk(structure, [])

    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:top_k]


def _terms(s: str) -> set[str]:
    s = s.lower()
    toks = re.findall(r"[a-z0-9]{2,}", s)
    return set(toks)


def _overlap_score(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / (len(b) ** 0.5)


def _fallback_md_to_tree(md_path: Path) -> dict[str, Any]:
    txt = md_path.read_text(encoding="utf-8")
    lines = txt.splitlines()
    heading_re = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")

    doc_name = md_path.stem
    structure: list[dict[str, Any]] = []
    stack: list[tuple[int, dict[str, Any]]] = []
    node_counter = 0

    def new_node(title: str, line_num: int) -> dict[str, Any]:
        nonlocal node_counter
        node_counter += 1
        return {"title": title, "node_id": f"{node_counter:04d}", "line_num": line_num, "text": "", "nodes": []}

    # Create a synthetic root node if first content is not headed.
    current_node: Optional[dict[str, Any]] = None

    def append_text(node: Optional[dict[str, Any]], ln: str) -> None:
        if node is None:
            return
        node["text"] = (node.get("text", "") + ("\n" if node.get("text") else "") + ln).strip("\n")

    in_code = False
    for i, ln in enumerate(lines, start=1):
        if ln.strip().startswith("```"):
            in_code = not in_code
        m = None if in_code else heading_re.match(ln)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            node = new_node(title, i)
            while stack and stack[-1][0] >= level:
                stack.pop()
            if stack:
                stack[-1][1]["nodes"].append(node)
            else:
                structure.append(node)
            stack.append((level, node))
            current_node = node
        else:
            append_text(current_node, ln)

    return {"doc_name": doc_name, "structure": structure}

