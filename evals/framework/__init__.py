"""Eval framework — metrics, base classes, and utilities."""

from evals.framework.metrics import (
    precision,
    recall,
    f1_score,
    accuracy,
    mean_absolute_error,
    severity_agreement_rate,
    category_coverage,
    calibration_error,
    ndcg_at_k,
    mrr,
)
from evals.framework.base import EvalCase, EvalResult, EvalSuite
from evals.framework.assertions import (
    assert_recall_above,
    assert_precision_above,
    assert_f1_above,
    assert_accuracy_above,
    assert_no_duplicates,
    assert_severity_not_inflated,
    assert_all_grounded,
)

__all__ = [
    "precision",
    "recall",
    "f1_score",
    "accuracy",
    "mean_absolute_error",
    "severity_agreement_rate",
    "category_coverage",
    "calibration_error",
    "ndcg_at_k",
    "mrr",
    "EvalCase",
    "EvalResult",
    "EvalSuite",
    "assert_recall_above",
    "assert_precision_above",
    "assert_f1_above",
    "assert_accuracy_above",
    "assert_no_duplicates",
    "assert_severity_not_inflated",
    "assert_all_grounded",
]
