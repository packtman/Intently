"""
False Positive Filter - Multi-iteration LLM-based false positive removal.

Runs multiple validation passes over scan findings to progressively remove
false positives, each pass focusing on a different validation strategy:

  Round 1 - Context Validation:  Are findings already mitigated by existing
            controls visible in the codebase state?
  Round 2 - Specificity Check:   Are findings concrete and specific to this
            PRD/codebase, or generic boilerplate?
  Round 3 - Evidence Grounding:  Can each finding cite a real PRD quote,
            endpoint, or code pattern, or is it speculative?

Additional rounds (up to max_iterations) repeat with increasing strictness.

Usage:
    from context_graph.llm.false_positive_filter import FalsePositiveFilter

    fp_filter = FalsePositiveFilter(
        llm_provider=provider,
        max_iterations=3,
    )
    filtered = await fp_filter.filter_findings(
        findings=raw_findings,
        dimension="security",
        intent=intent_dict,
        state=state_dict,
        delta=delta_dict,
    )
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass, field
from typing import Any

from context_graph.llm.provider import LLMProvider

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Validation strategy prompts – one per iteration round
# ---------------------------------------------------------------------------

VALIDATION_STRATEGIES: list[dict[str, str]] = [
    {
        "name": "context_validation",
        "description": "Check if findings are already mitigated by existing codebase controls",
        "prompt": """\
You are a senior staff engineer performing FALSE-POSITIVE DETECTION on automated
review findings.  Your goal is to REMOVE findings that are already addressed by
the existing codebase.

## Existing Codebase Controls
{state_summary}

## Current PRD Intent
{intent_summary}

## Delta / Changes
{delta_summary}

## Findings to Validate
{findings_json}

For EACH finding, answer:
1. Is this concern ALREADY mitigated by an existing control listed above?
   (e.g., "missing auth" when auth middleware already exists)
2. Does the codebase state contradict the premise of this finding?
3. Is this finding about a component that does NOT appear in the PRD or codebase?

Return ONLY valid JSON:
{{
    "validated_findings": [
        {{
            ... original finding fields ...,
            "fp_verdict": "keep|remove|downgrade",
            "fp_reason": "short explanation of verdict",
            "adjusted_severity": "original or lowered severity",
            "adjusted_confidence": 0.0-1.0
        }}
    ],
    "removal_summary": {{
        "total_input": <int>,
        "kept": <int>,
        "removed": <int>,
        "downgraded": <int>,
        "removal_reasons": ["list of common reasons for removal"]
    }}
}}""",
    },
    {
        "name": "specificity_check",
        "description": "Remove generic/boilerplate findings not specific to this PRD",
        "prompt": """\
You are a senior staff engineer performing a SPECIFICITY CHECK on automated
review findings.  Your goal is to remove generic, boilerplate findings that
could apply to ANY project and are not grounded in THIS specific PRD and
codebase.

## PRD Context
Title: {prd_title}
Features: {prd_features}

## Codebase Characteristics
{state_summary}

## Findings to Validate
{findings_json}

For EACH finding, answer:
1. Does this finding reference SPECIFIC features, endpoints, data entities,
   or patterns from this PRD?  Or could the exact same text appear on any
   review for any product?
2. Is the description concrete (mentions specific APIs, data fields, attack
   vectors relevant here) or vague generalities?
3. Does the finding add value BEYOND what a generic checklist would say?

A finding is a FALSE POSITIVE if it is purely generic boilerplate with no
connection to the actual PRD or codebase being reviewed.

Return ONLY valid JSON:
{{
    "validated_findings": [
        {{
            ... original finding fields ...,
            "fp_verdict": "keep|remove|downgrade",
            "fp_reason": "short explanation of verdict",
            "adjusted_severity": "original or lowered severity",
            "adjusted_confidence": 0.0-1.0
        }}
    ],
    "removal_summary": {{
        "total_input": <int>,
        "kept": <int>,
        "removed": <int>,
        "downgraded": <int>,
        "removal_reasons": ["list of common reasons for removal"]
    }}
}}""",
    },
    {
        "name": "evidence_grounding",
        "description": "Ensure each finding is backed by concrete evidence",
        "prompt": """\
You are a senior staff engineer performing an EVIDENCE GROUNDING check on
automated review findings.  Your goal is to remove findings that lack
concrete evidence and are purely speculative.

## PRD Intent
{intent_summary}

## Current Codebase State
{state_summary}

## Delta / Changes
{delta_summary}

## Findings to Validate
{findings_json}

For EACH finding, evaluate:
1. EVIDENCE: Can this finding point to a SPECIFIC PRD quote, code pattern,
   endpoint, or data entity as evidence?  Or is it speculation?
2. EXPLOITABILITY: Is the described risk realistically exploitable given the
   architecture, or is it a theoretical concern with negligible real-world
   risk?
3. ACTIONABILITY: Is the recommendation specific enough that a developer
   could implement it?  Or is it vague ("improve security")?

A finding is a FALSE POSITIVE if:
- It has no concrete evidence from the PRD or codebase
- The risk is purely theoretical with no realistic exploit path
- The recommendation is too vague to act on

Return ONLY valid JSON:
{{
    "validated_findings": [
        {{
            ... original finding fields ...,
            "fp_verdict": "keep|remove|downgrade",
            "fp_reason": "short explanation of verdict",
            "adjusted_severity": "original or lowered severity",
            "adjusted_confidence": 0.0-1.0
        }}
    ],
    "removal_summary": {{
        "total_input": <int>,
        "kept": <int>,
        "removed": <int>,
        "downgraded": <int>,
        "removal_reasons": ["list of common reasons for removal"]
    }}
}}""",
    },
]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class FilterIterationResult:
    """Result from a single filter iteration."""

    round_num: int = 0
    strategy_name: str = ""
    input_count: int = 0
    kept_count: int = 0
    removed_count: int = 0
    downgraded_count: int = 0
    removal_reasons: list[str] = field(default_factory=list)
    latency_ms: float = 0.0
    tokens_used: int = 0


@dataclass
class FalsePositiveFilterResult:
    """Complete result from the false positive filter pipeline."""

    filtered_findings: list[dict[str, Any]] = field(default_factory=list)
    removed_findings: list[dict[str, Any]] = field(default_factory=list)

    # Per-iteration stats
    iteration_results: list[FilterIterationResult] = field(default_factory=list)

    # Aggregate stats
    original_count: int = 0
    final_count: int = 0
    total_removed: int = 0
    total_downgraded: int = 0
    total_iterations: int = 0
    total_latency_ms: float = 0.0
    total_tokens: int = 0

    @property
    def removal_rate(self) -> float:
        if self.original_count == 0:
            return 0.0
        return self.total_removed / self.original_count


# ---------------------------------------------------------------------------
# Core filter
# ---------------------------------------------------------------------------


class FalsePositiveFilter:
    """
    Multi-iteration LLM-based false positive removal for scan findings.

    Each iteration applies a different validation strategy to progressively
    filter out false positives while preserving true findings.
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        max_iterations: int = 3,
        min_findings_to_filter: int = 3,
        verbose: bool = True,
    ) -> None:
        """
        Args:
            llm_provider: LLM provider to use for validation calls.
            max_iterations: Maximum number of filter iterations (1-5).
                            Clamped to the number of available strategies.
            min_findings_to_filter: Skip filtering if fewer than this many
                                     findings (not worth the LLM cost).
            verbose: Print progress to stderr.
        """
        self.provider = llm_provider
        self.max_iterations = min(max_iterations, len(VALIDATION_STRATEGIES))
        self.min_findings_to_filter = min_findings_to_filter
        self.verbose = verbose

    async def filter_findings(
        self,
        findings: list[dict[str, Any]],
        dimension: str,
        intent: dict[str, Any] | None = None,
        state: dict[str, Any] | None = None,
        delta: dict[str, Any] | None = None,
    ) -> FalsePositiveFilterResult:
        """
        Run the multi-iteration false positive filter pipeline.

        Args:
            findings: Raw findings (list of dicts) to validate.
            dimension: Review dimension (security, privacy, compliance, etc.).
            intent: PRD intent dict for context.
            state: Codebase state dict for context.
            delta: Delta dict for context.

        Returns:
            FalsePositiveFilterResult with filtered findings and stats.
        """
        result = FalsePositiveFilterResult(
            original_count=len(findings),
        )

        if len(findings) < self.min_findings_to_filter:
            if self.verbose:
                self._log(
                    f"FP Filter: skipping — only {len(findings)} findings "
                    f"(min {self.min_findings_to_filter})"
                )
            result.filtered_findings = findings
            result.final_count = len(findings)
            return result

        if self.verbose:
            self._log(f"\n{'='*60}")
            self._log(f"FALSE POSITIVE FILTER — {dimension.upper()}")
            self._log(f"Input findings: {len(findings)}")
            self._log(f"Max iterations: {self.max_iterations}")
            self._log(f"{'='*60}")

        # Prepare context summaries (truncated for token budget)
        intent_summary = self._summarise_context(intent, "intent")
        state_summary = self._summarise_context(state, "state")
        delta_summary = self._summarise_context(delta, "delta")
        prd_title = (intent or {}).get("title", "Unknown")
        prd_features = ", ".join((intent or {}).get("features", [])[:10])

        current_findings = findings
        all_removed: list[dict[str, Any]] = []

        for round_num in range(1, self.max_iterations + 1):
            strategy = VALIDATION_STRATEGIES[round_num - 1]

            if self.verbose:
                self._log(
                    f"\n--- Iteration {round_num}/{self.max_iterations}: "
                    f"{strategy['name']} ---"
                )
                self._log(f"  {strategy['description']}")
                self._log(f"  Input: {len(current_findings)} findings")

            iter_result = await self._run_iteration(
                round_num=round_num,
                strategy=strategy,
                findings=current_findings,
                dimension=dimension,
                intent_summary=intent_summary,
                state_summary=state_summary,
                delta_summary=delta_summary,
                prd_title=prd_title,
                prd_features=prd_features,
            )

            result.iteration_results.append(iter_result)
            result.total_latency_ms += iter_result.latency_ms
            result.total_tokens += iter_result.tokens_used

            # Partition into kept vs removed
            kept, removed, downgraded = self._apply_verdicts(current_findings, iter_result)
            all_removed.extend(removed)
            result.total_removed += iter_result.removed_count
            result.total_downgraded += iter_result.downgraded_count

            if self.verbose:
                self._log(
                    f"  Result: kept={len(kept)}, "
                    f"removed={iter_result.removed_count}, "
                    f"downgraded={iter_result.downgraded_count}"
                )

            current_findings = kept

            # Early stop if no findings were removed this round
            if iter_result.removed_count == 0 and iter_result.downgraded_count == 0:
                if self.verbose:
                    self._log("  No changes — stopping early")
                break

            # Early stop if too few findings remain
            if len(current_findings) < self.min_findings_to_filter:
                if self.verbose:
                    self._log(
                        f"  Only {len(current_findings)} findings remain — stopping"
                    )
                break

        result.filtered_findings = current_findings
        result.removed_findings = all_removed
        result.final_count = len(current_findings)
        result.total_iterations = len(result.iteration_results)

        if self.verbose:
            self._log(f"\n{'='*60}")
            self._log(f"FALSE POSITIVE FILTER COMPLETE")
            self._log(f"  {result.original_count} → {result.final_count} findings")
            self._log(
                f"  Removed: {result.total_removed} "
                f"({result.removal_rate:.0%})"
            )
            self._log(f"  Downgraded: {result.total_downgraded}")
            self._log(f"  Iterations: {result.total_iterations}")
            self._log(f"{'='*60}\n")

        return result

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _run_iteration(
        self,
        round_num: int,
        strategy: dict[str, str],
        findings: list[dict[str, Any]],
        dimension: str,
        intent_summary: str,
        state_summary: str,
        delta_summary: str,
        prd_title: str,
        prd_features: str,
    ) -> FilterIterationResult:
        """Execute a single filter iteration against the LLM."""
        from context_graph.llm.provider import AnalysisRequest, AnalysisType

        iter_result = FilterIterationResult(
            round_num=round_num,
            strategy_name=strategy["name"],
            input_count=len(findings),
        )

        # Build the prompt from the strategy template
        findings_json = json.dumps(findings, indent=2, default=str)

        prompt_content = strategy["prompt"].format(
            findings_json=findings_json,
            intent_summary=intent_summary,
            state_summary=state_summary,
            delta_summary=delta_summary,
            prd_title=prd_title,
            prd_features=prd_features,
        )

        system_prompt = (
            f"You are validating {dimension} findings for false positives. "
            f"Iteration {round_num}: {strategy['description']}. "
            f"Return ONLY valid JSON."
        )

        request = AnalysisRequest(
            analysis_type=AnalysisType.SECURITY_REVIEW,
            content=prompt_content,
            context={
                "system_prompt_override": system_prompt,
                "false_positive_filter": True,
                "iteration": round_num,
                "strategy": strategy["name"],
                "dimension": dimension,
            },
        )

        try:
            response = await self.provider.analyze(request)
            iter_result.latency_ms = response.latency_ms
            iter_result.tokens_used = response.tokens_used

            validated = response.structured_data.get("validated_findings", [])
            removal_summary = response.structured_data.get("removal_summary", {})

            # Count verdicts
            for item in validated:
                verdict = item.get("fp_verdict", "keep").lower()
                if verdict == "remove":
                    iter_result.removed_count += 1
                elif verdict == "downgrade":
                    iter_result.downgraded_count += 1

            iter_result.kept_count = (
                iter_result.input_count
                - iter_result.removed_count
            )
            iter_result.removal_reasons = removal_summary.get(
                "removal_reasons", []
            )

            # Stash validated findings on the result for _apply_verdicts
            iter_result._validated = validated  # type: ignore[attr-defined]

        except Exception as exc:
            logger.warning(
                "FP filter iteration %d (%s) failed: %s — keeping all findings",
                round_num,
                strategy["name"],
                exc,
            )
            iter_result.kept_count = iter_result.input_count
            iter_result._validated = []  # type: ignore[attr-defined]

        return iter_result

    def _apply_verdicts(
        self,
        current_findings: list[dict[str, Any]],
        iter_result: FilterIterationResult,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Apply LLM verdicts to partition findings.

        Returns (kept, removed, downgraded) lists.
        """
        validated: list[dict[str, Any]] = getattr(iter_result, "_validated", [])

        if not validated:
            return current_findings, [], []

        # Build a lookup from the validated response.
        # Match by finding id, or by index as fallback.
        verdict_map: dict[str, dict[str, Any]] = {}
        for i, item in enumerate(validated):
            fid = item.get("id", item.get("title", f"__idx_{i}"))
            verdict_map[str(fid)] = item

        kept: list[dict[str, Any]] = []
        removed: list[dict[str, Any]] = []
        downgraded: list[dict[str, Any]] = []

        for i, finding in enumerate(current_findings):
            fid = str(finding.get("id", finding.get("title", f"__idx_{i}")))
            verdict_entry = verdict_map.get(fid, {})
            verdict = verdict_entry.get("fp_verdict", "keep").lower()

            if verdict == "remove":
                annotated = {
                    **finding,
                    "fp_removed_in_round": iter_result.round_num,
                    "fp_strategy": iter_result.strategy_name,
                    "fp_reason": verdict_entry.get("fp_reason", ""),
                }
                removed.append(annotated)
            elif verdict == "downgrade":
                adjusted = {**finding}
                if "adjusted_severity" in verdict_entry:
                    adjusted["severity"] = verdict_entry["adjusted_severity"]
                if "adjusted_confidence" in verdict_entry:
                    adjusted["confidence"] = verdict_entry["adjusted_confidence"]
                adjusted["fp_downgraded_in_round"] = iter_result.round_num
                adjusted["fp_reason"] = verdict_entry.get("fp_reason", "")
                downgraded.append(adjusted)
                kept.append(adjusted)
            else:
                # "keep" — optionally update confidence if the LLM raised it
                adjusted = {**finding}
                if "adjusted_confidence" in verdict_entry:
                    adjusted["confidence"] = max(
                        finding.get("confidence", 0),
                        verdict_entry["adjusted_confidence"],
                    )
                kept.append(adjusted)

        return kept, removed, downgraded

    def _summarise_context(
        self,
        data: dict[str, Any] | None,
        label: str,
    ) -> str:
        """Create a concise text summary of a context dict."""
        if not data:
            return f"No {label} data available."
        try:
            text = json.dumps(data, indent=2, default=str)
            # Truncate to ~4000 chars to stay within token budget
            if len(text) > 4000:
                text = text[:3950] + "\n... (truncated)"
            return text
        except Exception:
            return f"No {label} data available."

    def _log(self, message: str) -> None:
        print(message, file=sys.stderr)
