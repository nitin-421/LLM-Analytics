"""Shared cleaning and metrics for the LLM usage dashboard and notebook."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = (
    "request_id", "timestamp", "application", "environment", "model",
    "status", "prompt_tokens", "completion_tokens", "latency_ms",
)
PRICING = {
    "gpt-4o": (0.005, 0.015),
    "gpt-4o-mini": (0.00015, 0.0006),
    "claude-3-5-sonnet": (0.003, 0.015),
    "gemini-1.5-pro": (0.00125, 0.005),
}
DEFAULT_PRICING = (0.001, 0.003)


def clean_usage(data: pd.DataFrame) -> pd.DataFrame:
    """Coerce schema, remove unusable rows, and add derived metrics."""
    if data is None or data.empty:
        return pd.DataFrame(columns=[*REQUIRED_COLUMNS, "total_tokens", "cost_usd", "date"])
    frame = data.copy()
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    frame = frame[list(REQUIRED_COLUMNS)]
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce", utc=True)
    for column in ("prompt_tokens", "completion_tokens", "latency_ms"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    for column in ("application", "environment", "model", "status", "request_id"):
        frame[column] = frame[column].astype("string").str.strip()
    valid = (
        frame["timestamp"].notna()
        & frame["request_id"].notna()
        & frame["model"].notna()
        & frame["prompt_tokens"].notna() & frame["prompt_tokens"].ge(0)
        & frame["completion_tokens"].notna() & frame["completion_tokens"].ge(0)
        & frame["latency_ms"].notna() & frame["latency_ms"].ge(0)
    )
    frame = frame.loc[valid].drop_duplicates("request_id").copy()
    frame["prompt_tokens"] = frame["prompt_tokens"].astype("int64")
    frame["completion_tokens"] = frame["completion_tokens"].astype("int64")
    frame["latency_ms"] = frame["latency_ms"].astype("int64")
    frame["total_tokens"] = frame["prompt_tokens"] + frame["completion_tokens"]
    rates = frame["model"].map(PRICING).apply(
        lambda pair: pair if isinstance(pair, tuple) else DEFAULT_PRICING
    )
    frame["cost_usd"] = [
        (row.prompt_tokens * rate[0] + row.completion_tokens * rate[1]) / 1000
        for row, rate in zip(frame.itertuples(), rates)
    ]
    frame["date"] = frame["timestamp"].dt.date
    return frame.reset_index(drop=True)


def load_usage_data(path: str | Path = "data/llm_usage.csv") -> pd.DataFrame:
    """Load and clean a CSV, returning an empty frame for missing/empty files."""
    file_path = Path(path)
    if not file_path.exists() or file_path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return clean_usage(pd.read_csv(file_path))
    except (OSError, pd.errors.ParserError, ValueError):
        return pd.DataFrame()


def summarize(data: pd.DataFrame) -> dict[str, float | int]:
    """Return safe headline metrics."""
    if data is None or data.empty:
        return {"requests": 0, "cost_usd": 0.0, "tokens": 0, "success_rate": 0.0, "p95_latency_ms": 0.0}
    return {
        "requests": int(len(data)),
        "cost_usd": float(data["cost_usd"].sum()),
        "tokens": int(data["total_tokens"].sum()),
        "success_rate": float(data["status"].eq("success").mean() * 100),
        "p95_latency_ms": float(np.percentile(data["latency_ms"], 95)),
    }


def by_dimension(data: pd.DataFrame, dimension: str) -> pd.DataFrame:
    """Aggregate usage and reliability by a categorical dimension."""
    if data.empty or dimension not in data.columns:
        return pd.DataFrame()
    return data.groupby(dimension, dropna=False).agg(
        requests=("request_id", "count"), cost_usd=("cost_usd", "sum"),
        tokens=("total_tokens", "sum"), avg_latency_ms=("latency_ms", "mean"),
        success_rate=("status", lambda values: values.eq("success").mean() * 100),
    ).reset_index().sort_values("cost_usd", ascending=False)
