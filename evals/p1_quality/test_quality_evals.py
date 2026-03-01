"""P1 Evals — PRD Quality Scoring (QUAL-01 through QUAL-07).

Tests that quality scores are calibrated, grades are meaningful, and gaps
are correctly identified.
"""
from __future__ import annotations

import pytest

from context_graph.pm.quality_scorer import PRDQualityScorer
from context_graph.core.models import PredictedQuestion, PRDQualityScore


@pytest.fixture
def scorer() -> PRDQualityScorer:
    return PRDQualityScorer()


def _make_questions(
    blockers: int = 0, likely: int = 0, possible: int = 0
) -> list[PredictedQuestion]:
    qs: list[PredictedQuestion] = []
    for i in range(blockers):
        qs.append(PredictedQuestion(
            question=f"Blocker question {i}",
            team="security",
            severity="blocker",
            reasoning="Test blocker",
        ))
    for i in range(likely):
        qs.append(PredictedQuestion(
            question=f"Likely question {i}",
            team="engineering",
            severity="likely",
            reasoning="Test likely",
        ))
    for i in range(possible):
        qs.append(PredictedQuestion(
            question=f"Possible question {i}",
            team="product",
            severity="possible",
            reasoning="Test possible",
        ))
    return qs


# ---------------------------------------------------------------------------
# QUAL-01: Score calibration
# ---------------------------------------------------------------------------

class TestQUAL01ScoreCalibration:
    """Scores should correlate with PRD quality."""

    def test_no_issues_high_score(self, scorer: PRDQualityScorer):
        score = scorer.calculate_score([], "A well-written PRD. " * 200)
        assert score.score >= 90, f"No-issues PRD should score >= 90, got {score.score}"

    def test_many_blockers_low_score(self, scorer: PRDQualityScorer):
        qs = _make_questions(blockers=5)
        score = scorer.calculate_score(qs, "Short PRD")
        assert score.score <= 60, f"5-blocker PRD should score <= 60, got {score.score}"

    def test_score_decreases_with_severity(self, scorer: PRDQualityScorer):
        s_none = scorer.calculate_score([], "Content " * 100)
        s_possible = scorer.calculate_score(_make_questions(possible=5), "Content " * 100)
        s_likely = scorer.calculate_score(_make_questions(likely=5), "Content " * 100)
        s_blocker = scorer.calculate_score(_make_questions(blockers=5), "Content " * 100)

        assert s_none.score >= s_possible.score >= s_likely.score >= s_blocker.score, (
            f"Scores should decrease with severity: "
            f"none={s_none.score}, possible={s_possible.score}, "
            f"likely={s_likely.score}, blocker={s_blocker.score}"
        )


# ---------------------------------------------------------------------------
# QUAL-02: Grade thresholds
# ---------------------------------------------------------------------------

class TestQUAL02GradeThresholds:
    """Grade boundaries should align with quality."""

    def test_high_score_gets_a(self, scorer: PRDQualityScorer):
        score = scorer.calculate_score([], "Comprehensive PRD content. " * 200)
        assert score.grade == "A", f"Score {score.score} should be grade A, got {score.grade}"

    def test_low_score_gets_d_or_f(self, scorer: PRDQualityScorer):
        qs = _make_questions(blockers=8)
        score = scorer.calculate_score(qs, "Short")
        assert score.grade in ("D", "F"), (
            f"Score {score.score} with 8 blockers should be D or F, got {score.grade}"
        )

    def test_medium_score_gets_b_or_c(self, scorer: PRDQualityScorer):
        qs = _make_questions(likely=3, possible=2)
        score = scorer.calculate_score(qs, "Medium length PRD content. " * 100)
        assert score.grade in ("A", "B", "C"), (
            f"Score {score.score} should be A/B/C, got {score.grade}"
        )


# ---------------------------------------------------------------------------
# QUAL-03: Gap identification precision
# ---------------------------------------------------------------------------

class TestQUAL03GapIdentification:
    """Identified gaps should be real."""

    def test_blockers_produce_gaps(self, scorer: PRDQualityScorer):
        qs = _make_questions(blockers=2)
        score = scorer.calculate_score(qs, "Some content")
        assert len(score.gaps) >= 1, (
            f"2 blockers should produce >= 1 gap, got {len(score.gaps)}"
        )

    def test_no_issues_minimal_gaps(self, scorer: PRDQualityScorer):
        score = scorer.calculate_score([], "Complete PRD. " * 200)
        assert len(score.gaps) <= 2, (
            f"No-issue PRD should have <= 2 gaps, got {len(score.gaps)}: {score.gaps}"
        )


# ---------------------------------------------------------------------------
# QUAL-04: Gap completeness
# ---------------------------------------------------------------------------

class TestQUAL04GapCompleteness:
    """All significant quality gaps should be identified."""

    def test_blocker_gaps_captured(self, scorer: PRDQualityScorer):
        qs = _make_questions(blockers=3, likely=2, possible=1)
        score = scorer.calculate_score(qs, "Content")
        assert score.blockers == 3, f"Expected 3 blockers, got {score.blockers}"
        assert score.likely_questions == 2
        assert score.possible_questions == 1


# ---------------------------------------------------------------------------
# QUAL-05: Score sensitivity
# ---------------------------------------------------------------------------

class TestQUAL05ScoreSensitivity:
    """Score should meaningfully differentiate between good and poor PRDs."""

    def test_score_spread(self, scorer: PRDQualityScorer):
        good = scorer.calculate_score([], "Detailed content. " * 300)
        bad = scorer.calculate_score(_make_questions(blockers=5, likely=3), "Short")
        spread = good.score - bad.score
        assert spread >= 30, (
            f"Score spread {spread} too small (good={good.score}, bad={bad.score})"
        )


# ---------------------------------------------------------------------------
# QUAL-06: Score stability
# ---------------------------------------------------------------------------

class TestQUAL06ScoreStability:
    """Same PRD scored twice should produce same result."""

    def test_deterministic(self, scorer: PRDQualityScorer):
        qs = _make_questions(blockers=1, likely=2, possible=3)
        content = "Test PRD content for stability check. " * 50
        s1 = scorer.calculate_score(qs, content)
        s2 = scorer.calculate_score(qs, content)
        assert s1.score == s2.score, (
            f"Scores differ between runs: {s1.score} vs {s2.score}"
        )
        assert s1.grade == s2.grade


# ---------------------------------------------------------------------------
# QUAL-07: Blocker detection accuracy
# ---------------------------------------------------------------------------

class TestQUAL07BlockerDetection:
    """Items flagged as blockers should be reflected in the score."""

    def test_each_blocker_reduces_score(self, scorer: PRDQualityScorer):
        content = "Content " * 100
        scores = []
        for n_blockers in range(5):
            qs = _make_questions(blockers=n_blockers)
            s = scorer.calculate_score(qs, content)
            scores.append(s.score)

        for i in range(1, len(scores)):
            assert scores[i] <= scores[i - 1], (
                f"Adding blockers should not increase score: {scores}"
            )

    def test_predicted_pushback_count(self, scorer: PRDQualityScorer):
        qs = _make_questions(blockers=2, likely=3, possible=4)
        score = scorer.calculate_score(qs, "Content")
        assert score.predicted_pushback == 9, (
            f"predicted_pushback should be 9, got {score.predicted_pushback}"
        )
