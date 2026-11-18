"""Evaluate a Locust run against the frozen RNF-04 criteria (stdlib only).

Criteria, defined by the group before the first evaluative run:
p95 of the measured request <= 1500 ms and error rate <= 1 %.
"""
from __future__ import annotations

import csv
from pathlib import Path

P95_MS_MAX = 1500
ERROR_RATE_MAX = 0.01


def _int(value: str) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def evaluate(stats_csv: Path) -> dict:
    """Read the ``Aggregated`` row of Locust's ``*_stats.csv`` and return the verdict.

    Args:
        stats_csv: Path to the stats CSV written by ``locust --csv``.

    Returns:
        A dict with requests, failures, error_rate, p50_ms, p95_ms, verdict
        (``Aprobado``, ``Fallido`` or ``Invalido``) and the reasons.
    """
    with stats_csv.open(encoding="utf-8", newline="") as handle:
        rows = [r for r in csv.DictReader(handle) if r.get("Name") == "Aggregated"]
    if not rows:
        return {"verdict": "Invalido", "reasons": ["no Aggregated row in the stats CSV"]}
    row = rows[0]
    requests = _int(row["Request Count"]) or 0
    failures = _int(row["Failure Count"]) or 0
    p50, p95 = _int(row["50%"]), _int(row["95%"])
    result = {"requests": requests, "failures": failures, "p50_ms": p50, "p95_ms": p95,
              "error_rate": round(failures / requests, 6) if requests else None}
    if not requests or p95 is None:
        return {**result, "verdict": "Invalido", "reasons": ["no measured requests"]}
    reasons = []
    if p95 > P95_MS_MAX:
        reasons.append(f"p95 {p95} ms > {P95_MS_MAX} ms")
    if result["error_rate"] > ERROR_RATE_MAX:
        reasons.append(f"error rate {result['error_rate']:.2%} > {ERROR_RATE_MAX:.0%}")
    return {**result, "verdict": "Fallido" if reasons else "Aprobado", "reasons": reasons}
