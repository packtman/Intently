"""
Iterative Analyzer - Generic iterative multi-round LLM analysis framework.

This module provides a reusable framework for iterative LLM analysis that:
1. Tracks category coverage across rounds
2. Builds continuation context to find more findings
3. Uses completion signals to determine when to stop
4. Deduplicates findings across rounds
5. Merges results into comprehensive output

Usage:
    from context_graph.llm.iterative_analyzer import IterativeAnalyzer
    from context_graph.llm.analysis_categories import AnalysisTypeCategories
    
    analyzer = IterativeAnalyzer(
        analysis_type=AnalysisTypeCategories.SECURITY,
        llm_call_fn=my_llm_call_function,
    )
    
    results = await analyzer.analyze(context)
"""

from __future__ import annotations

import asyncio
import logging
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable
from datetime import datetime

from context_graph.llm.analysis_categories import (
    AnalysisTypeCategories,
    IterativeAnalysisConfig,
    get_analysis_config,
)


logger = logging.getLogger(__name__)


@dataclass
class GenerationMetadata:
    """Metadata extracted from LLM response for iteration control."""
    
    analysis_complete: bool = False
    continuation_needed: bool = True
    last_finding_id: str = ""
    remaining_categories: list[str] = field(default_factory=list)
    total_findings_in_response: int = 0
    covered_categories: list[str] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GenerationMetadata":
        """Parse generation_metadata from LLM response."""
        return cls(
            analysis_complete=data.get("analysis_complete", False),
            continuation_needed=data.get("continuation_needed", True),
            last_finding_id=data.get("last_finding_id", data.get("last_threat_id", "")),
            remaining_categories=data.get("remaining_categories_to_analyze", []),
            total_findings_in_response=data.get("total_findings_in_response", 0),
            covered_categories=data.get("covered_categories", []),
        )


@dataclass
class IterativeAnalysisResult:
    """Result from iterative analysis."""
    
    # All findings across all rounds
    findings: list[dict[str, Any]] = field(default_factory=list)
    
    # Raw responses from each round
    raw_responses: list[dict[str, Any]] = field(default_factory=list)
    
    # Tracking
    total_rounds: int = 0
    covered_categories: set[str] = field(default_factory=set)
    uncovered_categories: set[str] = field(default_factory=set)
    
    # Timing
    total_latency_ms: float = 0.0
    total_tokens: int = 0
    
    # Summary data (from first round)
    summary: dict[str, Any] = field(default_factory=dict)
    
    # Additional merged data
    merged_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMCallResult:
    """Result from a single LLM call."""
    
    structured_data: dict[str, Any]
    was_truncated: bool = False
    stop_reason: str = ""
    latency_ms: float = 0.0
    tokens_used: int = 0


# Type alias for LLM call function
LLMCallFn = Callable[[str, dict[str, Any]], Awaitable[LLMCallResult]]


class IterativeAnalyzer:
    """
    Generic iterative multi-round LLM analyzer.
    
    Provides a framework for running multiple rounds of LLM analysis
    to ensure comprehensive coverage of all relevant categories.
    """
    
    def __init__(
        self,
        analysis_type: AnalysisTypeCategories,
        llm_call_fn: LLMCallFn,
        config_override: IterativeAnalysisConfig | None = None,
        finding_key: str = "findings",
        finding_id_field: str = "id",
        finding_category_field: str = "category",
        verbose: bool = True,
    ) -> None:
        """
        Initialize the iterative analyzer.
        
        Args:
            analysis_type: Type of analysis being performed
            llm_call_fn: Async function to call LLM with (context, call_metadata) -> LLMCallResult
            config_override: Optional override for analysis config
            finding_key: Key in response containing findings list
            finding_id_field: Field name for finding ID
            finding_category_field: Field name for finding category
            verbose: Whether to print progress to stderr
        """
        self.analysis_type = analysis_type
        self.llm_call_fn = llm_call_fn
        self.config = config_override or get_analysis_config(analysis_type)
        self.finding_key = finding_key
        self.finding_id_field = finding_id_field
        self.finding_category_field = finding_category_field
        self.verbose = verbose
        
        # Get all category names for tracking
        self.all_categories = set(self.config.get_category_names())
        self.category_keywords = self.config.get_category_keywords()
    
    async def analyze(
        self,
        initial_context: str,
        additional_context: dict[str, Any] | None = None,
    ) -> IterativeAnalysisResult:
        """
        Perform iterative analysis.
        
        Args:
            initial_context: The full context for analysis
            additional_context: Optional additional context passed to LLM calls
            
        Returns:
            IterativeAnalysisResult with all findings and metadata
        """
        result = IterativeAnalysisResult()
        
        all_findings: list[dict[str, Any]] = []
        existing_finding_ids: set[str] = set()
        existing_finding_summaries: list[str] = []
        covered_categories: set[str] = set()
        
        if self.verbose:
            self._log(f"{'='*60}")
            self._log(f"ITERATIVE {self.analysis_type.value.upper()} ANALYSIS ENABLED")
            self._log(f"Max rounds: {self.config.max_rounds}")
            self._log(f"Target categories: {len(self.all_categories)}")
            self._log(f"{'='*60}")
        
        round_num = 0
        
        while round_num < self.config.max_rounds:
            round_num += 1
            
            if self.verbose:
                self._log(f"\n--- Iteration Round {round_num}/{self.config.max_rounds} ---")
            
            # Build context for this round
            if round_num > 1:
                uncovered = list(self.all_categories - covered_categories)
                context = self._build_continuation_context(
                    initial_context=initial_context,
                    existing_ids=list(existing_finding_ids),
                    existing_summaries=existing_finding_summaries,
                    covered_categories=list(covered_categories),
                    uncovered_categories=uncovered,
                    round_num=round_num,
                )
            else:
                context = initial_context
            
            # Call LLM
            call_metadata = {
                "round_num": round_num,
                "is_continuation": round_num > 1,
                "analysis_type": self.analysis_type.value,
                **(additional_context or {}),
            }
            
            try:
                llm_result = await self.llm_call_fn(context, call_metadata)
            except Exception as e:
                logger.error(f"LLM call failed in round {round_num}: {e}")
                if self.verbose:
                    self._log(f"ERROR: LLM call failed: {e}")
                break
            
            result.raw_responses.append({
                f"round_{round_num}": llm_result.structured_data,
                "was_truncated": llm_result.was_truncated,
                "stop_reason": llm_result.stop_reason,
            })
            result.total_latency_ms += llm_result.latency_ms
            result.total_tokens += llm_result.tokens_used
            
            # Extract findings from this round
            round_findings = llm_result.structured_data.get(self.finding_key, [])
            new_findings_count = 0
            
            for finding in round_findings:
                finding_id = finding.get(self.finding_id_field, "")
                
                if finding_id and finding_id not in existing_finding_ids:
                    all_findings.append(finding)
                    existing_finding_ids.add(finding_id)
                    
                    # Build summary for continuation context
                    title = finding.get("title", "")
                    category = finding.get(self.finding_category_field, "")
                    existing_finding_summaries.append(f"{finding_id}: {title} ({category})")
                    new_findings_count += 1
                    
                    # Track covered categories
                    detected_category = self._detect_category(finding)
                    if detected_category:
                        covered_categories.add(detected_category)
            
            if self.verbose:
                self._log(f"Round {round_num}: Found {new_findings_count} NEW findings (total: {len(all_findings)})")
                self._log(f"  Covered categories: {len(covered_categories)}/{len(self.all_categories)}")
            
            # Extract generation metadata
            gen_metadata = GenerationMetadata.from_dict(
                llm_result.structured_data.get("generation_metadata", {})
            )
            
            if self.verbose:
                self._log(f"  Model signals - complete: {gen_metadata.analysis_complete}, continue: {gen_metadata.continuation_needed}")
                self._log(f"  was_truncated: {llm_result.was_truncated}")
            
            # Preserve summary and other data from first round
            if round_num == 1:
                result.summary = llm_result.structured_data.get("summary", {})
                # Preserve other top-level keys
                for key in llm_result.structured_data:
                    if key not in [self.finding_key, "generation_metadata", "summary"]:
                        result.merged_data[key] = llm_result.structured_data[key]
            
            # Check stopping conditions
            uncovered_count = len(self.all_categories - covered_categories)
            
            should_stop = self._should_stop(
                analysis_complete=gen_metadata.analysis_complete,
                new_findings_count=new_findings_count,
                uncovered_count=uncovered_count,
                was_truncated=llm_result.was_truncated,
            )
            
            if should_stop:
                if self.verbose:
                    self._log(f"Stopping: stopping condition met")
                break
            
            # Check if we should continue
            should_continue = self._should_continue(
                continuation_needed=gen_metadata.continuation_needed,
                new_findings_count=new_findings_count,
                uncovered_count=uncovered_count,
                was_truncated=llm_result.was_truncated,
            )
            
            if not should_continue:
                if self.verbose:
                    self._log(f"Stopping: sufficient coverage achieved")
                break
            
            if self.verbose:
                self._log(f"  Continuing to find more findings in {uncovered_count} uncovered categories...")
        
        # Finalize result
        result.findings = all_findings
        result.total_rounds = round_num
        result.covered_categories = covered_categories
        result.uncovered_categories = self.all_categories - covered_categories
        
        if self.verbose:
            self._log(f"\n{'='*60}")
            self._log(f"ITERATIVE GENERATION COMPLETE")
            self._log(f"Total rounds: {round_num}")
            self._log(f"Total findings identified: {len(all_findings)}")
            self._log(f"Categories covered: {len(covered_categories)}/{len(self.all_categories)}")
            self._log(f"{'='*60}\n")
        
        return result
    
    def _build_continuation_context(
        self,
        initial_context: str,
        existing_ids: list[str],
        existing_summaries: list[str],
        covered_categories: list[str],
        uncovered_categories: list[str],
        round_num: int,
    ) -> str:
        """Build aggressive continuation context for subsequent rounds."""
        parts = [
            initial_context,
            "",
            "=" * 80,
            f"## 🚨 CONTINUATION REQUIRED - FIND MORE {self.analysis_type.value.upper()} FINDINGS 🚨",
            "=" * 80,
            "",
            f"This is round {round_num} of {self.analysis_type.value} analysis. You MUST identify ADDITIONAL findings.",
            "",
            "### ❌ ALREADY IDENTIFIED (DO NOT REPEAT THESE)",
            "",
        ]
        
        if existing_summaries:
            for summary in existing_summaries:
                parts.append(f"- {summary}")
        else:
            for finding_id in existing_ids:
                parts.append(f"- {finding_id}")
        
        parts.append("")
        parts.append(f"**Start numbering NEW findings from F{len(existing_ids) + 1}**")
        parts.append("")
        
        if covered_categories:
            parts.append("### ✅ Categories Already Covered")
            parts.append("")
            for cat in covered_categories:
                parts.append(f"- {cat}")
            parts.append("")
        
        if uncovered_categories:
            parts.append("### 🎯 CATEGORIES YOU MUST NOW ANALYZE")
            parts.append("")
            parts.append("You have NOT YET covered these categories. Find findings in these areas:")
            parts.append("")
            for cat in uncovered_categories[:6]:  # Focus on top 6 uncovered
                parts.append(f"- **{cat}** - Find at least ONE finding in this category")
            parts.append("")
        
        parts.extend([
            "### INSTRUCTIONS",
            "",
            "1. **DO NOT** repeat any finding already identified above",
            "2. **FOCUS ON** the uncovered categories listed above",
            f"3. **FIND NEW** {self.analysis_type.value} concerns, even if they seem less obvious",
            "4. **BE SPECIFIC** - Reference PRD quotes and code if available",
            f"5. **Generate at least {self.config.min_findings_per_round} NEW findings** in this round",
            "",
            "Think creatively about:",
        ])
        
        # Add category-specific hints
        for cat in uncovered_categories[:4]:
            config = next((c for c in self.config.categories if c.name == cat), None)
            if config:
                parts.append(f"- {cat}: {config.description}")
        
        parts.extend([
            "",
            "### OUTPUT FORMAT",
            "",
            "Return ONLY the new findings in the same JSON format as before.",
            "Include generation_metadata with:",
            "- analysis_complete: true ONLY if you've exhausted ALL realistic findings",
            "- continuation_needed: true if more findings could be found",
            "- remaining_categories_to_analyze: list of categories still to explore",
            "",
        ])
        
        return "\n".join(parts)
    
    def _detect_category(self, finding: dict[str, Any]) -> str | None:
        """Detect which category a finding belongs to based on keywords."""
        # First try the explicit category field
        category = finding.get(self.finding_category_field, "").lower()
        
        # Try to match to our categories
        for cat_name, keywords in self.category_keywords.items():
            cat_lower = cat_name.lower()
            if category and (cat_lower in category or any(kw in category for kw in keywords)):
                return cat_name
        
        # Fall back to checking title and description
        title = finding.get("title", "").lower()
        description = finding.get("description", "").lower()
        combined = f"{category} {title} {description}"
        
        for cat_name, keywords in self.category_keywords.items():
            if any(kw in combined for kw in keywords):
                return cat_name
        
        return None
    
    def _should_stop(
        self,
        analysis_complete: bool,
        new_findings_count: int,
        uncovered_count: int,
        was_truncated: bool,
    ) -> bool:
        """Determine if we should stop iteration."""
        # Model explicitly says complete AND we got no new findings
        if analysis_complete and new_findings_count == 0:
            return True
        
        # We've covered most categories and model says complete
        if analysis_complete and uncovered_count <= self.config.max_uncovered_categories_to_stop:
            return True
        
        # Response was truncated but no new findings (probably parsing issue)
        if was_truncated and new_findings_count == 0 and self.config.stop_on_no_new_findings:
            return True
        
        return False
    
    def _should_continue(
        self,
        continuation_needed: bool,
        new_findings_count: int,
        uncovered_count: int,
        was_truncated: bool,
    ) -> bool:
        """Determine if we should continue iteration."""
        # Still have significant categories to cover
        if uncovered_count > self.config.max_uncovered_categories_to_stop:
            return True
        
        # Model signals continuation needed
        if continuation_needed:
            return True
        
        # Response was truncated (might have more)
        if was_truncated:
            return True
        
        # Found new findings (momentum)
        if new_findings_count > 0:
            return True
        
        return False
    
    def _log(self, message: str) -> None:
        """Log message to stderr."""
        print(message, file=sys.stderr)


# ==================== Convenience Functions ====================


async def run_iterative_analysis(
    analysis_type: AnalysisTypeCategories,
    initial_context: str,
    llm_call_fn: LLMCallFn,
    config_override: IterativeAnalysisConfig | None = None,
    finding_key: str = "findings",
    verbose: bool = True,
) -> IterativeAnalysisResult:
    """
    Convenience function to run iterative analysis.
    
    Args:
        analysis_type: Type of analysis
        initial_context: Full context for analysis
        llm_call_fn: Function to call LLM
        config_override: Optional config override
        finding_key: Key in response containing findings
        verbose: Whether to print progress
        
    Returns:
        IterativeAnalysisResult
    """
    analyzer = IterativeAnalyzer(
        analysis_type=analysis_type,
        llm_call_fn=llm_call_fn,
        config_override=config_override,
        finding_key=finding_key,
        verbose=verbose,
    )
    return await analyzer.analyze(initial_context)


def create_generation_metadata_prompt_section() -> str:
    """
    Create the prompt section instructing LLM to include generation metadata.
    
    Add this to your prompts to enable iterative generation.
    """
    return """

## OUTPUT COMPLETION SIGNALS

To ensure comprehensive analysis without truncation, include these completion signals in your response:

1. **If you have identified ALL findings** - Include in your response:
   ```json
   "generation_metadata": {
       "analysis_complete": true,
       "continuation_needed": false,
       "total_findings_in_response": <number of findings in this response>,
       "covered_categories": ["list of categories covered"]
   }
   ```

2. **If you have MORE findings to identify but are running out of space** - Include:
   ```json
   "generation_metadata": {
       "analysis_complete": false,
       "continuation_needed": true,
       "last_finding_id": "F<N>",
       "remaining_categories_to_analyze": ["list of categories not yet covered"],
       "total_findings_in_response": <number of findings in this response>
   }
   ```

This allows the system to request continuation if your response was truncated. Always include the `generation_metadata` object at the end of your JSON response."""
