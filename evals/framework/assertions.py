"""High-level assertion helpers that produce clear error messages."""
from __future__ import annotations

from collections import Counter
from typing import Any, Sequence

from evals.framework.metrics import (
    precision,
    recall,
    f1_score,
    accuracy,
    duplicate_rate,
)


def assert_recall_above(
    predicted: set[str],
    ground_truth: set[str],
    threshold: float,
    label: str = "",
) -> float:
    r = recall(predicted, ground_truth)
    missing = ground_truth - predicted
    msg = f"Recall {r:.3f} below threshold {threshold:.3f}"
    if label:
        msg = f"[{label}] {msg}"
    if missing:
        msg += f"\n  Missing: {sorted(missing)[:10]}"
    assert r >= threshold, msg
    return r


def assert_precision_above(
    predicted: set[str],
    ground_truth: set[str],
    threshold: float,
    label: str = "",
) -> float:
    p = precision(predicted, ground_truth)
    extra = predicted - ground_truth
    msg = f"Precision {p:.3f} below threshold {threshold:.3f}"
    if label:
        msg = f"[{label}] {msg}"
    if extra:
        msg += f"\n  Unexpected: {sorted(extra)[:10]}"
    assert p >= threshold, msg
    return p


def assert_f1_above(
    predicted: set[str],
    ground_truth: set[str],
    threshold: float,
    label: str = "",
) -> float:
    f1 = f1_score(predicted, ground_truth)
    msg = f"F1 {f1:.3f} below threshold {threshold:.3f}"
    if label:
        msg = f"[{label}] {msg}"
    assert f1 >= threshold, msg
    return f1


def assert_accuracy_above(
    predictions: Sequence[str],
    labels: Sequence[str],
    threshold: float,
    label: str = "",
) -> float:
    acc = accuracy(predictions, labels)
    msg = f"Accuracy {acc:.3f} below threshold {threshold:.3f}"
    if label:
        msg = f"[{label}] {msg}"
    assert acc >= threshold, msg
    return acc


def assert_no_duplicates(
    items: Sequence[str],
    label: str = "",
    max_rate: float = 0.05,
) -> float:
    rate = duplicate_rate(items)
    msg = f"Duplicate rate {rate:.3f} exceeds max {max_rate:.3f}"
    if label:
        msg = f"[{label}] {msg}"
    if rate > max_rate:
        counts = Counter(items)
        dups = {k: v for k, v in counts.items() if v > 1}
        msg += f"\n  Duplicates: {dict(list(dups.items())[:5])}"
    assert rate <= max_rate, msg
    return rate


def assert_severity_not_inflated(
    severities: Sequence[str],
    max_critical_pct: float = 0.30,
    max_high_pct: float = 0.50,
    label: str = "",
) -> dict[str, float]:
    """Severity distribution should not be top-heavy."""
    if not severities:
        return {}
    counts = Counter(severities)
    total = len(severities)
    pcts = {k: v / total for k, v in counts.items()}
    crit_pct = pcts.get("critical", 0.0)
    high_pct = pcts.get("high", 0.0)
    msg_parts = []
    if crit_pct > max_critical_pct:
        msg_parts.append(
            f"Critical={crit_pct:.0%} exceeds max {max_critical_pct:.0%}"
        )
    if high_pct > max_high_pct:
        msg_parts.append(
            f"High={high_pct:.0%} exceeds max {max_high_pct:.0%}"
        )
    if msg_parts:
        msg = f"Severity inflation: {'; '.join(msg_parts)}"
        if label:
            msg = f"[{label}] {msg}"
        msg += f"\n  Distribution: {dict(counts)}"
        assert False, msg
    return pcts


def assert_all_grounded(
    findings: Sequence[dict[str, Any]],
    evidence_field: str = "source_reference",
    min_rate: float = 0.80,
    label: str = "",
) -> float:
    """Assert that a sufficient fraction of findings have evidence grounding."""
    if not findings:
        return 1.0
    grounded = sum(
        1
        for f in findings
        if f.get(evidence_field) and str(f[evidence_field]).strip()
    )
    rate = grounded / len(findings)
    msg = f"Grounding rate {rate:.3f} below threshold {min_rate:.3f}"
    if label:
        msg = f"[{label}] {msg}"
    assert rate >= min_rate, msg
    return rate
