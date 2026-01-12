"""
PRD Quality Scorer - Assesses PRD readiness and completeness.

Calculates quality score based on:
- Coverage of security/privacy/compliance requirements
- Clarity of technical specifications
- Completeness of edge cases
- Alignment with codebase patterns
"""

from __future__ import annotations

from context_graph.core.models import (
    PRDQualityScore,
    PredictedQuestion,
    ReviewDimension,
)


class PRDQualityScorer:
    """Calculates PRD quality scores."""
    
    def calculate_score(
        self,
        predicted_questions: list[PredictedQuestion],
        prd_content: str,
    ) -> PRDQualityScore:
        """
        Calculate PRD quality score.
        
        Args:
            predicted_questions: List of predicted questions/issues
            prd_content: Current PRD content
            
        Returns:
            PRDQualityScore with score, grade, and breakdown
        """
        # Count questions by severity
        blockers = sum(1 for q in predicted_questions if q.severity == "blocker")
        likely = sum(1 for q in predicted_questions if q.severity == "likely")
        possible = sum(1 for q in predicted_questions if q.severity == "possible")
        
        total_questions = len(predicted_questions)
        
        # Calculate base score (100 - penalty for each question)
        # Blockers: -10 points each
        # Likely: -5 points each
        # Possible: -2 points each
        penalty = (blockers * 10) + (likely * 5) + (possible * 2)
        base_score = max(0, 100 - penalty)
        
        # Bonus for PRD length/completeness (simple heuristic)
        word_count = len(prd_content.split())
        if word_count > 1000:
            base_score += 5
        elif word_count > 500:
            base_score += 2
        
        # Cap at 100
        final_score = min(100, base_score)
        
        # Calculate grade
        grade = self._score_to_grade(final_score)
        
        # Generate gaps list
        gaps = self._identify_gaps(predicted_questions)
        
        return PRDQualityScore(
            score=final_score,
            grade=grade,
            gaps=gaps,
            predicted_pushback=total_questions,
            blockers=blockers,
            likely_questions=likely,
            possible_questions=possible,
        )
    
    def _score_to_grade(self, score: float) -> str:
        """Convert numeric score to letter grade."""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    def _identify_gaps(self, predicted_questions: list[PredictedQuestion]) -> list[str]:
        """Identify key gaps in the PRD."""
        gaps = []
        
        # Group by team to identify patterns
        by_team: dict[str, list[PredictedQuestion]] = {}
        for q in predicted_questions:
            if q.team not in by_team:
                by_team[q.team] = []
            by_team[q.team].append(q)
        
        # Generate gap descriptions
        for team, questions in by_team.items():
            if len(questions) >= 2:
                gaps.append(f"{team.capitalize()} concerns: {len(questions)} potential questions")
        
        # Add blocker-specific gaps
        blockers = [q for q in predicted_questions if q.severity == "blocker"]
        if blockers:
            gaps.append(f"{len(blockers)} blocker-level issues need attention")
        
        return gaps
