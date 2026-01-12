"""
Pattern Learning - Learns from expert responses to improve predictions.

Extracts patterns from expert feedback and applies them to future predictions.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from context_graph.core.models import (
    ExpertResponse,
    LearnedPattern,
    PredictedQuestion,
    CodeEvidence,
)


class PatternLearner:
    """Learns patterns from expert responses."""
    
    def __init__(self):
        self.learned_patterns: list[LearnedPattern] = []
    
    def learn_from_response(
        self,
        question: PredictedQuestion,
        response: ExpertResponse,
    ) -> LearnedPattern | None:
        """
        Learn a pattern from an expert response.
        
        Args:
            question: The original predicted question
            response: Expert's response
            
        Returns:
            LearnedPattern if a pattern was extracted, None otherwise
        """
        if not response.should_learn:
            return None
        
        # Extract pattern based on verdict
        if response.verdict == "wrong":
            # Expert says prediction is wrong - learn correction
            pattern = self._extract_correction_pattern(question, response)
        elif response.verdict == "partially_right":
            # Expert says partially right - learn refinement
            pattern = self._extract_refinement_pattern(question, response)
        else:
            # "correct" - no pattern to learn (prediction was right)
            return None
        
        if pattern:
            self.learned_patterns.append(pattern)
            return pattern
        
        return None
    
    def _extract_correction_pattern(
        self,
        question: PredictedQuestion,
        response: ExpertResponse,
    ) -> LearnedPattern | None:
        """Extract a correction pattern when expert says prediction is wrong."""
        if not response.correct_answer:
            return None
        
        # Extract conditions from code evidence
        conditions = []
        for evidence in question.code_evidence:
            if evidence.file_path:
                conditions.append(f"file:{evidence.file_path}")
            if evidence.context:
                conditions.append(f"context:{evidence.context[:50]}")  # First 50 chars
        
        # Extract key terms from question
        question_terms = self._extract_key_terms(question.question)
        conditions.extend(question_terms)
        
        pattern = LearnedPattern(
            pattern_description=f"Correction for: {question.question}",
            applies_when=" AND ".join(conditions) if conditions else "similar context",
            correction=response.correct_answer,
            learned_from=[question.id],
            times_applied=0,
            accuracy_score=1.0,  # Start with 100% (expert confirmed)
        )
        
        return pattern
    
    def _extract_refinement_pattern(
        self,
        question: PredictedQuestion,
        response: ExpertResponse,
    ) -> LearnedPattern | None:
        """Extract a refinement pattern when expert says partially right."""
        if not response.note:
            return None
        
        # Similar to correction but with refinement note
        conditions = []
        for evidence in question.code_evidence:
            if evidence.file_path:
                conditions.append(f"file:{evidence.file_path}")
        
        pattern = LearnedPattern(
            pattern_description=f"Refinement for: {question.question}",
            applies_when=" AND ".join(conditions) if conditions else "similar context",
            correction=response.note,  # Use note as refinement
            learned_from=[question.id],
            times_applied=0,
            accuracy_score=0.8,  # Start with 80% (partially right)
        )
        
        return pattern
    
    def _extract_key_terms(self, text: str) -> list[str]:
        """Extract key terms from text."""
        # Simple extraction - look for important words
        important_words = [
            "rate limiting", "authentication", "authorization", "encryption",
            "session", "token", "GDPR", "privacy", "compliance", "security",
            "validation", "input", "output", "api", "endpoint",
        ]
        
        terms = []
        text_lower = text.lower()
        for word in important_words:
            if word in text_lower:
                terms.append(f"contains:{word}")
        
        return terms
    
    def apply_patterns(
        self,
        question: PredictedQuestion,
    ) -> PredictedQuestion:
        """
        Apply learned patterns to a predicted question.
        
        Modifies the question if a matching pattern is found.
        """
        for pattern in self.learned_patterns:
            if self._pattern_matches(pattern, question):
                # Apply pattern correction
                if pattern.correction:
                    # Update question reasoning with pattern correction
                    question.reasoning = f"{question.reasoning} [Pattern: {pattern.correction}]"
                
                # Increment pattern usage
                pattern.times_applied += 1
                
                # Update accuracy if we have feedback
                # (In real implementation, this would track expert agreement)
        
        return question
    
    def _pattern_matches(
        self,
        pattern: LearnedPattern,
        question: PredictedQuestion,
    ) -> bool:
        """Check if a pattern matches a question."""
        # Simple matching - check if conditions are met
        conditions = pattern.applies_when.lower()
        
        # Check code evidence
        for evidence in question.code_evidence:
            if evidence.file_path and f"file:{evidence.file_path}" in conditions:
                return True
            if evidence.context and any(term in conditions for term in evidence.context.lower().split()[:5]):
                return True
        
        # Check question text
        question_lower = question.question.lower()
        if any(term in question_lower for term in conditions.split() if ":" not in term):
            return True
        
        return False
    
    def get_pattern_insights(self) -> dict[str, Any]:
        """Get insights about learned patterns."""
        total_patterns = len(self.learned_patterns)
        
        by_type: dict[str, int] = {}
        by_decision: dict[str, int] = {}
        
        for pattern in self.learned_patterns:
            # Categorize by type (correction vs refinement)
            pattern_type = "correction" if pattern.accuracy_score >= 0.9 else "refinement"
            by_type[pattern_type] = by_type.get(pattern_type, 0) + 1
            
            # Categorize by decision (what it corrects)
            decision = "wrong" if pattern.accuracy_score >= 0.9 else "partial"
            by_decision[decision] = by_decision.get(decision, 0) + 1
        
        # Most applied patterns
        most_applied = sorted(
            self.learned_patterns,
            key=lambda p: p.times_applied,
            reverse=True
        )[:5]
        
        return {
            "total_patterns": total_patterns,
            "by_type": by_type,
            "by_decision": by_decision,
            "most_applied_patterns": [
                {
                    "pattern_signature": pattern.pattern_description,
                    "decision": "correction" if pattern.accuracy_score >= 0.9 else "refinement",
                    "times_applied": pattern.times_applied,
                }
                for pattern in most_applied
            ],
        }
