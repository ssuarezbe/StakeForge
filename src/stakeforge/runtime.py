from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StakeForgeConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    use_fts: bool = True
    use_pageindex: bool = True
    token_budget: int = 1200
    max_tokens_per_source: int = 400
    dolt: str = "auto"  # auto|on|off


def _as_bool01(v: str) -> bool:
    v = v.strip()
    if v not in {"0", "1"}:
        raise ValueError(f"Expected '0' or '1', got: {v!r}")
    return v == "1"


def load_config_from_env_and_args(args) -> StakeForgeConfig:
    return StakeForgeConfig(
        use_fts=_as_bool01(getattr(args, "use_fts", "1")),
        use_pageindex=_as_bool01(getattr(args, "use_pageindex", "1")),
        token_budget=int(getattr(args, "token_budget", 1200)),
        max_tokens_per_source=int(getattr(args, "max_tokens_per_source", 400)),
        dolt=str(getattr(args, "dolt", "auto")),
    )

