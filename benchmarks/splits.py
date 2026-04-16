from __future__ import annotations

from typing import Any


def sample_key(row: dict[str, Any]) -> str:
    if row.get("sample_id") is not None:
        return str(row["sample_id"])
    if row.get("id") is not None:
        return str(row["id"])
    return repr(sorted(row.items()))


def train_holdout_split(
    rows: list[dict[str, Any]],
    *,
    holdout_ratio: float = 0.2,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not rows:
        return [], []
    ordered = sorted(rows, key=sample_key)
    holdout_size = max(1, int(round(len(ordered) * float(holdout_ratio))))
    train_size = max(1, len(ordered) - holdout_size)
    train = ordered[:train_size]
    holdout = ordered[train_size:]
    if not holdout:
        holdout = [train.pop()]
    return train, holdout
