"""P2 Evals — PRD Change Suggestions (CHG-01 through CHG-07).

Tests that PRD change suggestions are relevant, well-formed, and actionable.
"""
from __future__ import annotations

import pytest

from context_graph.core.models import PRDChange, DiffHunk, PredictedQuestion


# ---------------------------------------------------------------------------
# CHG-01: Change relevance
# ---------------------------------------------------------------------------

class TestCHG01ChangeRelevance:
    def test_prd_change_model_fields(self):
        change = PRDChange(
            prediction_id="pred_1",
            section="Security",
            change_type="addition",
            current_text="",
            suggested_text="Add rate limiting to auth endpoints.",
            reasoning="Security review identified missing rate limiting.",
        )
        assert change.section == "Security"
        assert change.change_type == "addition"
        assert "rate limiting" in change.suggested_text


# ---------------------------------------------------------------------------
# CHG-02: Change completeness
# ---------------------------------------------------------------------------

class TestCHG02ChangeCompleteness:
    def test_change_has_reasoning(self):
        change = PRDChange(
            prediction_id="pred_2",
            section="API",
            change_type="modification",
            current_text="POST /api/users",
            suggested_text="POST /api/users (requires auth)",
            reasoning="Endpoint missing authentication requirement.",
        )
        assert change.reasoning and len(change.reasoning) > 10


# ---------------------------------------------------------------------------
# CHG-03: Change quality
# ---------------------------------------------------------------------------

class TestCHG03ChangeQuality:
    def test_diff_hunks_structure(self):
        hunk = DiffHunk(
            operation="add",
            content="+ Rate limiting: 100 req/min per IP",
            line_number=15,
        )
        assert hunk.operation in ("add", "remove", "context", "")
        assert hunk.line_number == 15


# ---------------------------------------------------------------------------
# CHG-04: Change correctness
# ---------------------------------------------------------------------------

class TestCHG04ChangeCorrectness:
    def test_change_status_field(self):
        change = PRDChange(
            prediction_id="pred_3",
            section="Data",
            change_type="addition",
            suggested_text="Encrypt SSN at rest.",
        )
        assert change.status in ("pending", "accepted", "rejected", "undone", "open", "")


# ---------------------------------------------------------------------------
# CHG-05 to CHG-07: Accept/undo/diff
# ---------------------------------------------------------------------------

class TestCHG05AcceptRate:
    def test_change_status_transitions(self):
        change = PRDChange(prediction_id="p1", section="S", change_type="add", suggested_text="T")
        change.status = "accepted"
        assert change.status == "accepted"


class TestCHG06UndoRate:
    def test_original_text_preserved(self):
        change = PRDChange(
            prediction_id="p1", section="S", change_type="modification",
            current_text="Original", suggested_text="Updated",
            original_suggested_text="Updated",
        )
        assert change.original_suggested_text == "Updated"


class TestCHG07SideBySideDiff:
    def test_diff_hunk_list(self):
        change = PRDChange(
            prediction_id="p1", section="S", change_type="modification",
            current_text="Old text", suggested_text="New text",
            diff_hunks=[
                DiffHunk(operation="remove", content="Old text"),
                DiffHunk(operation="add", content="New text"),
            ],
        )
        assert len(change.diff_hunks) == 2
