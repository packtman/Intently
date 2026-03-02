"""Evaluation metrics used across the eval suite.

All functions operate on basic Python types (sets, lists, dicts) so they can be
used without importing ML libraries.
"""
from __future__ import annotations

import math
from collections import Counter
from typing import Any, Sequence


def precision(predicted: set[str], ground_truth: set[str]) -> float:
    """Fraction of predicted items that are in ground truth."""
    if not predicted:
        return 1.0 if not ground_truth else 0.0
    return len(predicted & ground_truth) / len(predicted)


def recall(predicted: set[str], ground_truth: set[str]) -> float:
    """Fraction of ground truth items that are in predicted."""
    if not ground_truth:
        return 1.0
    return len(predicted & ground_truth) / len(ground_truth)


def f1_score(predicted: set[str], ground_truth: set[str]) -> float:
    """Harmonic mean of precision and recall."""
    p = precision(predicted, ground_truth)
    r = recall(predicted, ground_truth)
    if p + r == 0:
        return 0.0
    return 2 * p * r / (p + r)


def accuracy(predictions: Sequence[str], labels: Sequence[str]) -> float:
    """Fraction of predictions that match labels (element-wise)."""
    if not labels:
        return 1.0
    correct = sum(1 for p, l in zip(predictions, labels) if p == l)
    return correct / len(labels)


def mean_absolute_error(predictions: Sequence[float], labels: Sequence[float]) -> float:
    """Mean absolute difference between predictions and labels."""
    if not labels:
        return 0.0
    return sum(abs(p - l) for p, l in zip(predictions, labels)) / len(labels)


def severity_agreement_rate(
    predicted_severities: Sequence[str],
    ground_truth_severities: Sequence[str],
    allow_one_off: bool = False,
) -> float:
    """Fraction of findings whose severity matches ground truth.

    If *allow_one_off* is True, predictions that are one severity level away
    (e.g. "high" vs "critical") count as correct.
    """
    SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
    if not ground_truth_severities:
        return 1.0
    correct = 0
    for pred, gt in zip(predicted_severities, ground_truth_severities):
        if pred == gt:
            correct += 1
        elif allow_one_off:
            diff = abs(SEVERITY_ORDER.get(pred, -1) - SEVERITY_ORDER.get(gt, -1))
            if diff <= 1:
                correct += 1
    return correct / len(ground_truth_severities)


def category_coverage(
    finding_categories: Sequence[str],
    expected_categories: set[str],
) -> float:
    """Fraction of expected categories that appear in findings."""
    if not expected_categories:
        return 1.0
    found = set(finding_categories)
    return len(found & expected_categories) / len(expected_categories)


def calibration_error(
    confidences: Sequence[float],
    correct: Sequence[bool],
    n_bins: int = 10,
) -> float:
    """Expected Calibration Error (ECE) — lower is better.

    Bins confidence values and computes the weighted average of
    |accuracy - confidence| per bin.
    """
    if not confidences:
        return 0.0
    bins: dict[int, list[tuple[float, bool]]] = {i: [] for i in range(n_bins)}
    for conf, cor in zip(confidences, correct):
        b = min(int(conf * n_bins), n_bins - 1)
        bins[b].append((conf, cor))
    ece = 0.0
    total = len(confidences)
    for items in bins.values():
        if not items:
            continue
        avg_conf = sum(c for c, _ in items) / len(items)
        avg_acc = sum(1 for _, cor in items if cor) / len(items)
        ece += len(items) / total * abs(avg_acc - avg_conf)
    return ece


def duplicate_rate(items: Sequence[str]) -> float:
    """Fraction of items that appear more than once."""
    if not items:
        return 0.0
    counts = Counter(items)
    duplicates = sum(c - 1 for c in counts.values() if c > 1)
    return duplicates / len(items)


def removal_rate(original_count: int, final_count: int) -> float:
    """Fraction of items removed."""
    if original_count == 0:
        return 0.0
    return (original_count - final_count) / original_count


def ndcg_at_k(relevance_scores: Sequence[float], k: int = 10) -> float:
    """Normalized Discounted Cumulative Gain at k."""
    def dcg(scores: Sequence[float], k: int) -> float:
        return sum(
            (2 ** s - 1) / math.log2(i + 2)
            for i, s in enumerate(scores[:k])
        )

    actual_dcg = dcg(relevance_scores, k)
    ideal = sorted(relevance_scores, reverse=True)
    ideal_dcg = dcg(ideal, k)
    if ideal_dcg == 0:
        return 0.0
    return actual_dcg / ideal_dcg


def mrr(ranked_correct: Sequence[bool]) -> float:
    """Mean Reciprocal Rank — for a single query's ranked results."""
    for i, correct in enumerate(ranked_correct):
        if correct:
            return 1.0 / (i + 1)
    return 0.0


def spearman_correlation(x: Sequence[float], y: Sequence[float]) -> float:
    """Spearman rank correlation coefficient."""
    n = len(x)
    if n < 2:
        return 0.0
    rank_x = _rank(x)
    rank_y = _rank(y)
    d_sq = sum((rx - ry) ** 2 for rx, ry in zip(rank_x, rank_y))
    return 1 - (6 * d_sq) / (n * (n ** 2 - 1))


def _rank(values: Sequence[float]) -> list[float]:
    """Assign ranks (1-based, averaged for ties)."""
    indexed = sorted(enumerate(values), key=lambda x: x[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i
        while j < len(indexed) and indexed[j][1] == indexed[i][1]:
            j += 1
        avg_rank = (i + j + 1) / 2
        for k in range(i, j):
            ranks[indexed[k][0]] = avg_rank
        i = j
    return ranks
