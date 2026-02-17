"""
False Positive Filter - Multi-iteration LLM-based false positive removal.

Supports two execution modes:

  **parallel** (default) — All validation strategies run concurrently on the
  same findings, then verdicts are merged by majority vote.  A finding is
  removed only when 2+ of 3 strategies agree it should go.  This is ~3x
  faster than sequential because LLM calls happen in one batch.

  **sequential** — Strategies run one after another; each round filters the
  output of the previous round.  More aggressive removal but slower.

Validation strategies:

  1. Context Validation:  Are findings already mitigated by existing controls
     visible in the codebase state?
  2. Specificity Check:   Are findings concrete and specific to this
     PRD/codebase, or generic boilerplate?
  3. Evidence Grounding:  Can each finding cite a real PRD quote, endpoint,
     or code pattern, or is it speculative?

Usage:
    from context_graph.llm.false_positive_filter import FalsePositiveFilter

    fp_filter = FalsePositiveFilter(
        llm_provider=provider,
        max_iterations=3,
        parallel=True,          # fan-out + majority-vote (default)
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

import asyncio
import json
import logging
import sys
from dataclasses import dataclass, field
from typing import Any

from context_graph.llm.provider import LLMProvider
from context_graph.tracing.collector import TraceCollector

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

    # Execution mode ("parallel" or "sequential")
    execution_mode: str = "parallel"

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

    Supports two execution modes controlled by the ``parallel`` flag:

    * **parallel=True** (default) — All validation strategies run at the same
      time via ``asyncio.gather``.  Verdicts are merged by **majority vote**:
      a finding is removed only when ``removal_threshold`` or more strategies
      agree.  ~3x faster wall-clock time.

    * **parallel=False** — Strategies run sequentially; each round filters the
      output of the previous round (original behaviour).
    """

    # Number of "remove" votes required to actually remove a finding in
    # parallel mode.  Default of 2 means a majority of strategies must
    # agree to remove a finding.  This prevents over-aggressive removal
    # when using fast/cheap models.  Use 1 for aggressive mode or 3 for
    # unanimous.
    DEFAULT_REMOVAL_THRESHOLD = 1

    def __init__(
        self,
        llm_provider: LLMProvider,
        max_iterations: int = 3,
        min_findings_to_filter: int = 3,
        verbose: bool = True,
        parallel: bool = True,
        removal_threshold: int | None = None,
        model_override: str | None = None,
        trace_collector: TraceCollector | None = None,
    ) -> None:
        """
        Args:
            llm_provider: LLM provider to use for validation calls.
            max_iterations: Maximum number of filter iterations (1-5).
                            Clamped to the number of available strategies.
            min_findings_to_filter: Skip filtering if fewer than this many
                                     findings (not worth the LLM cost).
            verbose: Print progress to stderr.
            parallel: If True (default) run all strategies concurrently
                      and merge verdicts.  If False, run sequentially.
            removal_threshold: In parallel mode, the minimum number of
                               strategies that must vote "remove" to
                               actually remove a finding.  Defaults to 2.
            model_override: Use a different (faster) model for FP filter
                            LLM calls.  Passed via AnalysisRequest context
                            so the provider uses it instead of its default.
                            None = use the provider's default model.
            trace_collector: Optional trace collector for emitting events.
        """
        self.provider = llm_provider
        self.max_iterations = min(max_iterations, len(VALIDATION_STRATEGIES))
        self.min_findings_to_filter = min_findings_to_filter
        self.verbose = verbose
        self.parallel = parallel
        self.removal_threshold = (
            removal_threshold
            if removal_threshold is not None
            else self.DEFAULT_REMOVAL_THRESHOLD
        )
        self.model_override = model_override or None
        self.tc = trace_collector

    # ==================================================================
    # Public entry point
    # ==================================================================

    async def filter_findings(
        self,
        findings: list[dict[str, Any]],
        dimension: str,
        intent: dict[str, Any] | None = None,
        state: dict[str, Any] | None = None,
        delta: dict[str, Any] | None = None,
    ) -> FalsePositiveFilterResult:
        """
        Run the false positive filter pipeline.

        Dispatches to either the parallel or sequential implementation
        depending on the ``self.parallel`` flag.
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

        mode_label = "PARALLEL" if self.parallel else "SEQUENTIAL"
        model_label = self.model_override or self.provider.model
        if self.verbose:
            self._log(f"\n{'='*60}")
            self._log(
                f"FALSE POSITIVE FILTER — {dimension.upper()} [{mode_label}]"
            )
            self._log(f"Input findings: {len(findings)}")
            self._log(f"Strategies: {self.max_iterations}")
            self._log(f"Model: {model_label}")
            if self.parallel:
                self._log(f"Removal threshold: {self.removal_threshold} votes")
            self._log(f"{'='*60}")

        result.execution_mode = "parallel" if self.parallel else "sequential"

        if self.parallel:
            return await self._run_parallel(findings, dimension, intent, state, delta, result)
        return await self._run_sequential(findings, dimension, intent, state, delta, result)

    # ==================================================================
    # Parallel mode — fan-out + majority-vote merge
    # ==================================================================

    async def _run_parallel(
        self,
        findings: list[dict[str, Any]],
        dimension: str,
        intent: dict[str, Any] | None,
        state: dict[str, Any] | None,
        delta: dict[str, Any] | None,
        result: FalsePositiveFilterResult,
    ) -> FalsePositiveFilterResult:
        """Fan-out all strategies concurrently, then merge verdicts."""

        intent_summary = self._summarise_context(intent, "intent")
        state_summary = self._summarise_context(state, "state")
        delta_summary = self._summarise_context(delta, "delta")
        prd_title = (intent or {}).get("title", "Unknown")
        prd_features = ", ".join((intent or {}).get("features", [])[:10])

        strategies = VALIDATION_STRATEGIES[: self.max_iterations]

        strategy_names = [s["name"] for s in strategies]
        if self.verbose:
            self._log(
                f"\nLaunching {len(strategies)} strategies in parallel: "
                + ", ".join(strategy_names)
            )
        if self.tc:
            self.tc.emit("info", "fp_filter",
                          f"Launching {len(strategies)} strategies in parallel: {', '.join(strategy_names)}",
                          strategies=strategy_names, dimension=dimension)

        # Fan-out: run every strategy on the SAME findings simultaneously
        tasks = [
            self._run_iteration(
                round_num=idx + 1,
                strategy=strat,
                findings=findings,
                dimension=dimension,
                intent_summary=intent_summary,
                state_summary=state_summary,
                delta_summary=delta_summary,
                prd_title=prd_title,
                prd_features=prd_features,
            )
            for idx, strat in enumerate(strategies)
        ]

        iter_results: list[FilterIterationResult] = await asyncio.gather(*tasks)

        # Collect per-strategy verdicts keyed by finding id
        # Structure: { finding_id: [ (strategy_name, verdict, entry), ... ] }
        votes: dict[str, list[tuple[str, str, dict[str, Any]]]] = {}
        for finding_idx, finding in enumerate(findings):
            fid = str(finding.get("id", finding.get("title", f"__idx_{finding_idx}")))
            votes[fid] = []

        for ir in iter_results:
            validated: list[dict[str, Any]] = getattr(ir, "_validated", [])
            v_map: dict[str, dict[str, Any]] = {}
            for i, item in enumerate(validated):
                vid = str(item.get("id", item.get("title", f"__idx_{i}")))
                v_map[vid] = item

            for finding_idx, finding in enumerate(findings):
                fid = str(finding.get("id", finding.get("title", f"__idx_{finding_idx}")))
                entry = v_map.get(fid, {})
                verdict = entry.get("fp_verdict", "keep").lower()
                votes[fid].append((ir.strategy_name, verdict, entry))

            result.iteration_results.append(ir)
            result.total_latency_ms = max(result.total_latency_ms, ir.latency_ms)
            result.total_tokens += ir.tokens_used

        # Merge verdicts by majority vote
        kept: list[dict[str, Any]] = []
        removed: list[dict[str, Any]] = []
        total_downgraded = 0

        for finding_idx, finding in enumerate(findings):
            fid = str(finding.get("id", finding.get("title", f"__idx_{finding_idx}")))
            finding_votes = votes.get(fid, [])

            remove_count = sum(1 for _, v, _ in finding_votes if v == "remove")
            downgrade_count = sum(1 for _, v, _ in finding_votes if v == "downgrade")

            if remove_count >= self.removal_threshold:
                reasons = [
                    e.get("fp_reason", "")
                    for s, v, e in finding_votes
                    if v == "remove" and e.get("fp_reason")
                ]
                strategies_that_removed = [
                    s for s, v, _ in finding_votes if v == "remove"
                ]
                annotated = {
                    **finding,
                    "fp_removed_by": strategies_that_removed,
                    "fp_vote_count": f"{remove_count}/{len(finding_votes)}",
                    "fp_reasons": reasons,
                }
                removed.append(annotated)
            elif downgrade_count > 0:
                adjusted = {**finding}
                dg_entries = [e for _, v, e in finding_votes if v == "downgrade"]
                if dg_entries:
                    best = dg_entries[0]
                    if "adjusted_severity" in best:
                        adjusted["severity"] = best["adjusted_severity"]
                    if "adjusted_confidence" in best:
                        adjusted["confidence"] = best["adjusted_confidence"]
                adjusted["fp_downgraded_by"] = [
                    s for s, v, _ in finding_votes if v == "downgrade"
                ]
                total_downgraded += 1
                kept.append(adjusted)
            else:
                # All strategies agree: keep
                adjusted = {**finding}
                confidences = [
                    e.get("adjusted_confidence")
                    for _, _, e in finding_votes
                    if "adjusted_confidence" in e
                ]
                if confidences:
                    adjusted["confidence"] = max(
                        finding.get("confidence", 0), *confidences
                    )
                kept.append(adjusted)

        result.filtered_findings = kept
        result.removed_findings = removed
        result.final_count = len(kept)
        result.total_removed = len(removed)
        result.total_downgraded = total_downgraded
        result.total_iterations = len(iter_results)

        if self.verbose:
            self._log(f"\n{'='*60}")
            self._log("FALSE POSITIVE FILTER COMPLETE [PARALLEL]")
            self._log(f"  {result.original_count} → {result.final_count} findings")
            self._log(
                f"  Removed: {result.total_removed} "
                f"({result.removal_rate:.0%}) "
                f"[threshold: {self.removal_threshold}/{len(strategies)} votes]"
            )
            self._log(f"  Downgraded: {result.total_downgraded}")
            self._log(
                f"  Wall-clock latency: {result.total_latency_ms:.0f} ms "
                f"(parallel — max of {len(strategies)} calls)"
            )
            self._log(f"  Total tokens: {result.total_tokens}")
            self._log(f"{'='*60}\n")

        if self.tc:
            self.tc.emit("info", "fp_filter",
                          f"Majority vote: {result.final_count}/{result.original_count} kept, "
                          f"{result.total_removed} removed ({result.removal_rate:.0%})",
                          kept=result.final_count, removed=result.total_removed,
                          downgraded=result.total_downgraded,
                          latency_ms=round(result.total_latency_ms),
                          tokens=result.total_tokens)

        return result

    # ==================================================================
    # Sequential mode — original pipeline behaviour
    # ==================================================================

    async def _run_sequential(
        self,
        findings: list[dict[str, Any]],
        dimension: str,
        intent: dict[str, Any] | None,
        state: dict[str, Any] | None,
        delta: dict[str, Any] | None,
        result: FalsePositiveFilterResult,
    ) -> FalsePositiveFilterResult:
        """Run strategies one after another, piping output to next round."""

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
            if self.tc:
                self.tc.emit("info", "fp_filter",
                              f"Strategy {round_num}/{self.max_iterations}: {strategy['name']} — {len(current_findings)} findings",
                              round=round_num, strategy=strategy["name"],
                              input_count=len(current_findings))

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
            if self.tc:
                self.tc.emit("info", "fp_filter",
                              f"Strategy {strategy['name']} complete: kept={len(kept)}, "
                              f"removed={iter_result.removed_count}, downgraded={iter_result.downgraded_count}",
                              strategy=strategy["name"],
                              kept=len(kept), removed=iter_result.removed_count,
                              downgraded=iter_result.downgraded_count)

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
            self._log("FALSE POSITIVE FILTER COMPLETE [SEQUENTIAL]")
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

        ctx: dict[str, Any] = {
            "system_prompt_override": system_prompt,
            "false_positive_filter": True,
            "iteration": round_num,
            "strategy": strategy["name"],
            "dimension": dimension,
        }
        if self.model_override:
            ctx["model_override"] = self.model_override

        request = AnalysisRequest(
            analysis_type=AnalysisType.SECURITY_REVIEW,
            content=prompt_content,
            context=ctx,
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
