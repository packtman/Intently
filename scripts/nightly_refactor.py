#!/usr/bin/env python3
"""
Nightly Refactor Scanner — Continuous Garbage Collection

This script analyzes the codebase against golden principles and generates
targeted cleanup suggestions. It is designed to be called by the nightly
GitHub Actions workflow.

When an LLM API key is available, it prompts the model to review specific
directories and produce small, actionable refactoring PRs. Without an API key,
it performs static analysis only.

Usage:
    python scripts/nightly_refactor.py [--output-dir docs/generated] [--dry-run]

Output:
    - docs/generated/refactor_candidates.json (machine-readable findings)
    - Individual refactor suggestions with file paths and proposed changes
"""
from __future__ import annotations

import ast
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

SRC_ROOT = Path(__file__).parent.parent / "src" / "context_graph"
DOCS_ROOT = Path(__file__).parent.parent / "docs"
OUTPUT_DIR = DOCS_ROOT / "generated"
GOLDEN_PRINCIPLES = DOCS_ROOT / "golden_principles.md"


@dataclass
class RefactorCandidate:
    file: str
    line: int
    category: str
    description: str
    priority: str  # low, medium, high
    suggested_fix: str

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "line": self.line,
            "category": self.category,
            "description": self.description,
            "priority": self.priority,
            "suggested_fix": self.suggested_fix,
        }


def check_missing_type_hints(candidates: list[RefactorCandidate]) -> None:
    """Find public functions without return type annotations."""
    for py_file in SRC_ROOT.rglob("*.py"):
        if "tests" in str(py_file) or "__pycache__" in str(py_file):
            continue

        try:
            with open(py_file, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source, filename=str(py_file))
        except (SyntaxError, UnicodeDecodeError):
            continue

        rel_path = str(py_file.relative_to(SRC_ROOT.parent.parent))

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("_"):
                    continue
                if node.returns is None:
                    candidates.append(
                        RefactorCandidate(
                            file=rel_path,
                            line=node.lineno,
                            category="type_hints",
                            description=f"Public function '{node.name}' missing return type annotation",
                            priority="low",
                            suggested_fix=f"Add return type: def {node.name}(...) -> ReturnType:",
                        )
                    )


def check_missing_docstrings(candidates: list[RefactorCandidate]) -> None:
    """Find public classes and functions without docstrings."""
    for py_file in SRC_ROOT.rglob("*.py"):
        if "tests" in str(py_file) or "__pycache__" in str(py_file):
            continue

        try:
            with open(py_file, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source, filename=str(py_file))
        except (SyntaxError, UnicodeDecodeError):
            continue

        rel_path = str(py_file.relative_to(SRC_ROOT.parent.parent))

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name.startswith("_"):
                    continue
                docstring = ast.get_docstring(node)
                if not docstring:
                    kind = "Class" if isinstance(node, ast.ClassDef) else "Function"
                    candidates.append(
                        RefactorCandidate(
                            file=rel_path,
                            line=node.lineno,
                            category="docstrings",
                            description=f"{kind} '{node.name}' missing docstring",
                            priority="low",
                            suggested_fix=f'Add a docstring explaining purpose, parameters, and return value.',
                        )
                    )


def check_large_files(candidates: list[RefactorCandidate]) -> None:
    """Find files exceeding 500 lines that should be decomposed."""
    for py_file in SRC_ROOT.rglob("*.py"):
        if "tests" in str(py_file) or "__pycache__" in str(py_file):
            continue

        try:
            with open(py_file, "r", encoding="utf-8") as f:
                line_count = sum(1 for _ in f)
        except (UnicodeDecodeError, IOError):
            continue

        if line_count > 500:
            rel_path = str(py_file.relative_to(SRC_ROOT.parent.parent))
            candidates.append(
                RefactorCandidate(
                    file=rel_path,
                    line=1,
                    category="file_size",
                    description=f"File has {line_count} lines (threshold: 500). Consider decomposition.",
                    priority="medium",
                    suggested_fix="Split into multiple focused modules following single-responsibility principle.",
                )
            )


def check_bare_excepts(candidates: list[RefactorCandidate]) -> None:
    """Find bare except clauses."""
    for py_file in SRC_ROOT.rglob("*.py"):
        if "tests" in str(py_file) or "__pycache__" in str(py_file):
            continue

        try:
            with open(py_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except (UnicodeDecodeError, IOError):
            continue

        rel_path = str(py_file.relative_to(SRC_ROOT.parent.parent))
        for i, line in enumerate(lines, 1):
            if re.match(r"\s*except\s*:", line):
                candidates.append(
                    RefactorCandidate(
                        file=rel_path,
                        line=i,
                        category="error_handling",
                        description="Bare except clause catches SystemExit and KeyboardInterrupt",
                        priority="medium",
                        suggested_fix="Replace with 'except Exception:' or catch specific exceptions.",
                    )
                )


def check_todo_comments(candidates: list[RefactorCandidate]) -> None:
    """Find TODO/FIXME/HACK comments that indicate tech debt."""
    for py_file in SRC_ROOT.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        try:
            with open(py_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except (UnicodeDecodeError, IOError):
            continue

        rel_path = str(py_file.relative_to(SRC_ROOT.parent.parent))
        for i, line in enumerate(lines, 1):
            match = re.search(r"#\s*(TODO|FIXME|HACK|XXX)\b(.*)", line)
            if match:
                candidates.append(
                    RefactorCandidate(
                        file=rel_path,
                        line=i,
                        category="tech_debt",
                        description=f"{match.group(1)}: {match.group(2).strip()[:100]}",
                        priority="low",
                        suggested_fix="Address the TODO or convert to a tracked issue.",
                    )
                )


def generate_llm_prompt(candidates: list[RefactorCandidate]) -> str:
    """Generate a prompt for an LLM to produce targeted cleanup suggestions."""
    principles = ""
    if GOLDEN_PRINCIPLES.exists():
        principles = GOLDEN_PRINCIPLES.read_text()[:3000]

    high_priority = [c for c in candidates if c.priority in ("high", "medium")][:20]

    prompt = f"""You are reviewing the Intently codebase for technical debt and style violations.

## Golden Principles (abbreviated):
{principles}

## Top Refactor Candidates:
{json.dumps([c.to_dict() for c in high_priority], indent=2)}

## Task:
For each candidate, produce a minimal, self-contained fix. Output JSON array:
[
  {{
    "file": "path/to/file.py",
    "action": "replace",
    "old_code": "exact code to replace",
    "new_code": "replacement code",
    "explanation": "one sentence why"
  }}
]

Rules:
- Only fix clear violations, not style preferences
- Changes must be backward compatible
- Each fix must be independently applicable
- Limit to 10 most impactful fixes
"""
    return prompt


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    output_dir = OUTPUT_DIR

    for arg in sys.argv[1:]:
        if arg.startswith("--output-dir="):
            output_dir = Path(arg.split("=", 1)[1])

    output_dir.mkdir(parents=True, exist_ok=True)

    candidates: list[RefactorCandidate] = []

    check_missing_type_hints(candidates)
    check_missing_docstrings(candidates)
    check_large_files(candidates)
    check_bare_excepts(candidates)
    check_todo_comments(candidates)

    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    candidates.sort(key=lambda c: priority_order.get(c.priority, 3))

    report = {
        "total_candidates": len(candidates),
        "by_category": {},
        "by_priority": {"high": 0, "medium": 0, "low": 0},
        "candidates": [c.to_dict() for c in candidates[:100]],
    }

    for c in candidates:
        report["by_category"][c.category] = report["by_category"].get(c.category, 0) + 1
        report["by_priority"][c.priority] = report["by_priority"].get(c.priority, 0) + 1

    output_file = output_dir / "refactor_candidates.json"
    output_file.write_text(json.dumps(report, indent=2))

    # Generate LLM prompt for nightly workflow
    prompt_file = output_dir / "refactor_prompt.txt"
    prompt_file.write_text(generate_llm_prompt(candidates))

    if dry_run:
        print(json.dumps(report, indent=2))
    else:
        print(json.dumps({
            "status": "complete",
            "candidates_found": len(candidates),
            "output_file": str(output_file),
            "prompt_file": str(prompt_file),
            "by_priority": report["by_priority"],
        }, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
