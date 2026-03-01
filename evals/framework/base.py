"""Base classes for structured eval cases and results."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class EvalCase:
    """A single evaluation test case with inputs and expected outputs."""

    eval_id: str
    name: str
    description: str
    inputs: dict[str, Any] = field(default_factory=dict)
    expected: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)


@dataclass
class EvalResult:
    """Result of running one eval case."""

    eval_id: str
    name: str
    passed: bool
    score: float = 0.0
    metric_name: str = ""
    threshold: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def summary_line(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return (
            f"[{status}] {self.eval_id} {self.name}: "
            f"{self.metric_name}={self.score:.3f} (threshold={self.threshold:.3f}) "
            f"[{self.duration_ms:.0f}ms]"
        )


class EvalSuite:
    """Collects eval results and produces a report."""

    def __init__(self, suite_name: str) -> None:
        self.suite_name = suite_name
        self.results: list[EvalResult] = []
        self._start_time = time.time()

    def add(self, result: EvalResult) -> None:
        self.results.append(result)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0

    def summary(self) -> str:
        lines = [
            f"\n{'=' * 60}",
            f"  Eval Suite: {self.suite_name}",
            f"  {self.passed}/{self.total} passed ({self.pass_rate:.0%})",
            f"  Duration: {(time.time() - self._start_time) * 1000:.0f}ms",
            f"{'=' * 60}",
        ]
        for r in self.results:
            lines.append(f"  {r.summary_line()}")
        lines.append(f"{'=' * 60}\n")
        return "\n".join(lines)

    def to_json(self) -> str:
        return json.dumps(
            {
                "suite": self.suite_name,
                "passed": self.passed,
                "failed": self.failed,
                "total": self.total,
                "pass_rate": self.pass_rate,
                "results": [
                    {
                        "eval_id": r.eval_id,
                        "name": r.name,
                        "passed": r.passed,
                        "score": r.score,
                        "metric_name": r.metric_name,
                        "threshold": r.threshold,
                        "details": r.details,
                        "duration_ms": r.duration_ms,
                    }
                    for r in self.results
                ],
            },
            indent=2,
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json())
