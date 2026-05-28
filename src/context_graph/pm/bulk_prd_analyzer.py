"""
Bulk PRD Analyzer - Analyze multiple PRD files in parallel.

Supports:
- Up to 20 PRD .md files in bulk
- Parallel analysis across selected review dimensions
- Smart codebase defaulting (if a codebase is selected >3 times, it becomes default)
- Up to 20 parallel review workers

Feature Flag: FEATURE_BULK_PRD_ANALYSIS=true
"""

from __future__ import annotations

import asyncio
import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Protocol
from uuid import UUID, uuid4

from context_graph.config.features import get_features
from context_graph.core.models import Intent, State, ReviewDimension, Severity


# ==================== Dependency Injection Protocols ====================


class PRDParserProtocol(Protocol):
    """Protocol for PRD parsers — allows pm/ to consume parsers without importing them."""

    def parse(self, content: str, source: str) -> Intent: ...


class ReviewEngineProtocol(Protocol):
    """Protocol for review engines — allows pm/ to consume security review without importing it."""

    async def review(self, intent: Intent, state: State) -> Any: ...


# Factory type: given keyword config args, returns a review engine
ReviewEngineFactory = Callable[..., ReviewEngineProtocol]
# Factory type: returns a PRD parser instance
PRDParserFactory = Callable[[], PRDParserProtocol]


logger = logging.getLogger(__name__)


# ==================== Data Models ====================


@dataclass
class PRDFile:
    """Represents a single PRD file for bulk analysis."""
    
    id: UUID = field(default_factory=uuid4)
    file_path: str = ""
    file_name: str = ""
    content: str = ""
    codebase_path: str | None = None  # Which codebase to analyze against
    
    # Analysis configuration per PRD
    dimensions: list[ReviewDimension] = field(default_factory=list)
    
    # Status tracking
    status: str = "pending"  # pending, analyzing, completed, failed
    error_message: str = ""
    
    @property
    def display_name(self) -> str:
        """Display name for UI."""
        return self.file_name or Path(self.file_path).name if self.file_path else "Untitled PRD"


@dataclass
class CodebaseSelection:
    """Tracks codebase selection frequency for smart defaulting."""
    
    path: str
    name: str = ""
    selection_count: int = 0
    last_selected_at: datetime = field(default_factory=datetime.now)
    
    @property
    def display_name(self) -> str:
        """Display name for UI."""
        return self.name or Path(self.path).name if self.path else "Unknown"


@dataclass
class SinglePRDResult:
    """Result from analyzing a single PRD."""
    
    prd_id: UUID
    prd_file_name: str
    codebase_path: str | None
    
    # Analysis results
    success: bool = True
    error_message: str = ""
    
    # Findings summary
    total_findings: int = 0
    findings_by_severity: dict[str, int] = field(default_factory=dict)
    findings_by_dimension: dict[str, int] = field(default_factory=dict)
    
    # Full review result (if needed for detailed access)
    review_id: str = ""
    review_result: Any = None  # Full ReviewResult object for storage in main reviews_store
    
    # Timing
    duration_ms: float = 0.0
    completed_at: datetime = field(default_factory=datetime.now)


@dataclass
class BulkAnalysisResult:
    """Combined result from bulk PRD analysis."""
    
    id: UUID = field(default_factory=uuid4)
    
    # Individual results
    prd_results: list[SinglePRDResult] = field(default_factory=list)
    
    # Aggregate stats
    total_prds: int = 0
    successful_prds: int = 0
    failed_prds: int = 0
    total_findings: int = 0
    
    # Aggregated findings
    findings_by_severity: dict[str, int] = field(default_factory=dict)
    findings_by_dimension: dict[str, int] = field(default_factory=dict)
    
    # Codebase insights
    codebases_analyzed: list[str] = field(default_factory=list)
    default_codebase: str | None = None
    codebase_selection_counts: dict[str, int] = field(default_factory=dict)
    
    # Timing
    total_duration_ms: float = 0.0
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    
    # Execution details
    parallel_workers_used: int = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_prds == 0:
            return 0.0
        return (self.successful_prds / self.total_prds) * 100


@dataclass
class BulkAnalysisRequest:
    """Request to analyze multiple PRDs in bulk."""
    
    prds: list[PRDFile] = field(default_factory=list)
    
    # Default settings (can be overridden per PRD)
    default_codebase_path: str | None = None
    default_dimensions: list[ReviewDimension] = field(default_factory=lambda: [
        ReviewDimension.SECURITY,
        ReviewDimension.PRIVACY,
        ReviewDimension.COMPLIANCE,
        ReviewDimension.ENGINEERING,
        ReviewDimension.ARCHITECTURE,
    ])
    
    # Execution settings
    max_parallel_reviews: int | None = None  # None = use feature flag default
    
    # Options
    use_llm: bool = True
    use_pattern_matching: bool = True


# ==================== Codebase Selection Tracker ====================


class CodebaseSelectionTracker:
    """
    Tracks codebase selection frequency across bulk analyses.
    
    When a codebase is selected more than the threshold times,
    it becomes the default for future analyses (with option to change).
    """
    
    def __init__(self) -> None:
        self._selections: dict[str, CodebaseSelection] = {}
        self._threshold = get_features().bulk_prd_codebase_auto_default_threshold
        self._current_default: str | None = None
    
    @property
    def threshold(self) -> int:
        """Get the auto-default threshold."""
        return self._threshold
    
    @property
    def current_default(self) -> str | None:
        """Get the current default codebase path."""
        return self._current_default
    
    def record_selection(self, codebase_path: str, name: str = "") -> CodebaseSelection:
        """
        Record a codebase selection and return the selection info.
        
        If this codebase exceeds the threshold, it becomes the new default.
        """
        if codebase_path not in self._selections:
            self._selections[codebase_path] = CodebaseSelection(
                path=codebase_path,
                name=name or Path(codebase_path).name,
            )
        
        selection = self._selections[codebase_path]
        selection.selection_count += 1
        selection.last_selected_at = datetime.now()
        
        # Check if this should become the default
        if selection.selection_count >= self._threshold:
            self._current_default = codebase_path
            logger.info(
                f"Codebase '{selection.display_name}' selected {selection.selection_count} times, "
                f"now set as default (threshold: {self._threshold})"
            )
        
        return selection
    
    def get_selection(self, codebase_path: str) -> CodebaseSelection | None:
        """Get selection info for a codebase."""
        return self._selections.get(codebase_path)
    
    def get_all_selections(self) -> list[CodebaseSelection]:
        """Get all codebase selections, sorted by count descending."""
        return sorted(
            self._selections.values(),
            key=lambda s: s.selection_count,
            reverse=True,
        )
    
    def set_default(self, codebase_path: str | None) -> None:
        """Manually set or clear the default codebase."""
        self._current_default = codebase_path
        if codebase_path:
            logger.info(f"Default codebase manually set to: {codebase_path}")
        else:
            logger.info("Default codebase cleared")
    
    def should_suggest_default(self, codebase_path: str) -> bool:
        """Check if a codebase should be suggested as default based on usage."""
        features = get_features()
        if not features.enable_bulk_prd_smart_codebase_default:
            return False
        
        selection = self._selections.get(codebase_path)
        if not selection:
            return False
        
        return selection.selection_count >= self._threshold
    
    def get_default_suggestion(self) -> CodebaseSelection | None:
        """
        Get the suggested default codebase based on usage patterns.
        
        Returns the most frequently used codebase that exceeds the threshold.
        """
        features = get_features()
        if not features.enable_bulk_prd_smart_codebase_default:
            return None
        
        candidates = [
            s for s in self._selections.values()
            if s.selection_count >= self._threshold
        ]
        
        if not candidates:
            return None
        
        # Return most frequently selected
        return max(candidates, key=lambda s: s.selection_count)
    
    def reset(self) -> None:
        """Reset all tracking data."""
        self._selections.clear()
        self._current_default = None


# Global tracker instance
_codebase_tracker: CodebaseSelectionTracker | None = None


def get_codebase_tracker() -> CodebaseSelectionTracker:
    """Get the global codebase selection tracker."""
    global _codebase_tracker
    if _codebase_tracker is None:
        _codebase_tracker = CodebaseSelectionTracker()
    return _codebase_tracker


def reset_codebase_tracker() -> None:
    """Reset the global codebase tracker."""
    global _codebase_tracker
    _codebase_tracker = None


# ==================== Bulk PRD Analyzer ====================


class BulkPRDAnalyzer:
    """
    Orchestrates parallel analysis of multiple PRD files.
    
    Features:
    - Analyzes up to 20 PRD files in parallel
    - Supports up to 20 parallel review workers
    - Smart codebase defaulting based on usage frequency
    - Per-PRD configuration of dimensions and codebase
    """
    
    def __init__(
        self,
        openai_api_key: str | None = None,
        anthropic_api_key: str | None = None,
        trace_collector: Any | None = None,
        parser_factory: PRDParserFactory | None = None,
        review_engine_factory: ReviewEngineFactory | None = None,
    ) -> None:
        self.openai_api_key = openai_api_key
        self.anthropic_api_key = anthropic_api_key
        self._trace_collector = trace_collector
        self._codebase_tracker = get_codebase_tracker()
        self._parser_factory = parser_factory
        self._review_engine_factory = review_engine_factory
    
    async def analyze(self, request: BulkAnalysisRequest) -> BulkAnalysisResult:
        """
        Analyze multiple PRDs in parallel.
        
        Args:
            request: BulkAnalysisRequest with PRD files and configuration
            
        Returns:
            BulkAnalysisResult with individual and aggregate results
        """
        import time
        
        features = get_features()
        
        # Validate feature flag
        if not features.enable_bulk_prd_analysis:
            raise ValueError(
                "Bulk PRD analysis is not enabled. "
                "Set FEATURE_BULK_PRD_ANALYSIS=true to enable."
            )
        
        # Validate PRD count
        max_files = min(features.bulk_prd_max_files, 20)  # Hard cap at 20
        if len(request.prds) > max_files:
            raise ValueError(
                f"Too many PRD files. Maximum allowed: {max_files}, "
                f"provided: {len(request.prds)}"
            )
        
        if len(request.prds) == 0:
            raise ValueError("No PRD files provided for analysis")
        
        start_time = time.time()
        
        result = BulkAnalysisResult(
            total_prds=len(request.prds),
            started_at=datetime.now(),
        )
        
        # Determine max parallel workers
        max_parallel = request.max_parallel_reviews
        if max_parallel is None:
            max_parallel = features.bulk_prd_max_parallel_reviews
        max_parallel = min(max_parallel, 20)  # Hard cap at 20
        result.parallel_workers_used = max_parallel
        
        logger.info(
            f"Starting bulk PRD analysis: {len(request.prds)} PRDs, "
            f"{max_parallel} parallel workers"
        )
        
        # Track codebase selections
        codebase_counts: Counter[str] = Counter()
        
        # Apply default codebase if not set per PRD
        for prd in request.prds:
            if prd.codebase_path is None:
                # Check for smart default
                if features.enable_bulk_prd_smart_codebase_default:
                    default_suggestion = self._codebase_tracker.get_default_suggestion()
                    if default_suggestion:
                        prd.codebase_path = default_suggestion.path
                        logger.debug(
                            f"Using smart default codebase for {prd.display_name}: "
                            f"{default_suggestion.display_name}"
                        )
                
                # Fall back to request default
                if prd.codebase_path is None and request.default_codebase_path:
                    prd.codebase_path = request.default_codebase_path
            
            # Apply default dimensions if not set
            if not prd.dimensions:
                prd.dimensions = request.default_dimensions.copy()
            
            # Track codebase selection
            if prd.codebase_path:
                codebase_counts[prd.codebase_path] += 1
                self._codebase_tracker.record_selection(prd.codebase_path)
        
        # Create semaphore for parallel execution
        semaphore = asyncio.Semaphore(max_parallel)
        
        # Create analysis tasks
        async def analyze_with_semaphore(prd: PRDFile) -> SinglePRDResult:
            async with semaphore:
                return await self._analyze_single_prd(prd, request)
        
        tasks = [analyze_with_semaphore(prd) for prd in request.prds]
        
        # Execute all analyses in parallel (limited by semaphore)
        prd_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, prd_result in enumerate(prd_results):
            if isinstance(prd_result, Exception):
                # Handle failed analysis
                prd = request.prds[i]
                failed_result = SinglePRDResult(
                    prd_id=prd.id,
                    prd_file_name=prd.display_name,
                    codebase_path=prd.codebase_path,
                    success=False,
                    error_message=str(prd_result),
                )
                result.prd_results.append(failed_result)
                result.failed_prds += 1
                logger.error(f"PRD analysis failed for {prd.display_name}: {prd_result}")
            else:
                result.prd_results.append(prd_result)
                if prd_result.success:
                    result.successful_prds += 1
                    result.total_findings += prd_result.total_findings
                    
                    # Aggregate by severity
                    for severity, count in prd_result.findings_by_severity.items():
                        result.findings_by_severity[severity] = (
                            result.findings_by_severity.get(severity, 0) + count
                        )
                    
                    # Aggregate by dimension
                    for dimension, count in prd_result.findings_by_dimension.items():
                        result.findings_by_dimension[dimension] = (
                            result.findings_by_dimension.get(dimension, 0) + count
                        )
                else:
                    result.failed_prds += 1
        
        # Set codebase insights
        result.codebases_analyzed = list(codebase_counts.keys())
        result.codebase_selection_counts = dict(codebase_counts)
        result.default_codebase = self._codebase_tracker.current_default
        
        result.total_duration_ms = (time.time() - start_time) * 1000
        result.completed_at = datetime.now()
        
        logger.info(
            f"Bulk PRD analysis complete: {result.successful_prds}/{result.total_prds} successful, "
            f"{result.total_findings} total findings, "
            f"{result.total_duration_ms:.0f}ms"
        )
        
        return result
    
    async def _analyze_single_prd(
        self,
        prd: PRDFile,
        request: BulkAnalysisRequest,
    ) -> SinglePRDResult:
        """Analyze a single PRD file."""
        import time
        
        tc = self._trace_collector
        tag = prd.display_name
        start_time = time.time()
        prd.status = "analyzing"
        
        try:
            # Parse PRD content
            if tc:
                tc.emit("info", "prd_parse", f"[{tag}] Parsing PRD...", prd=tag)
            if self._parser_factory is None:
                raise ValueError(
                    "No parser_factory provided to BulkPRDAnalyzer. "
                    "Pass a PRDParserFactory (e.g., MarkdownPRDParser) at construction time."
                )
            parser = self._parser_factory()
            intent = parser.parse(prd.content, prd.file_name)
            intent.raw_content = prd.content
            intent.source_document = prd.file_path
            
            # Use file name as title if parser couldn't extract one
            if not intent.title or intent.title == "Untitled PRD":
                # Clean up file name for display (remove .md extension, replace dashes/underscores)
                clean_name = prd.display_name
                if clean_name.endswith('.md'):
                    clean_name = clean_name[:-3]
                clean_name = clean_name.replace('-', ' ').replace('_', ' ')
                # Title case it for better display
                intent.title = clean_name.title() if clean_name else prd.display_name
            
            if tc:
                tc.emit("info", "prd_parse",
                        f"[{tag}] Extracted {len(intent.features)} features, "
                        f"{len(intent.user_stories)} user stories",
                        prd=tag, features=len(intent.features))
            
            # Build codebase state
            if tc:
                tc.emit("info", "codebase_analysis", f"[{tag}] Analyzing codebase...", prd=tag)
            state = await self._build_codebase_state(prd.codebase_path)
            if tc:
                tc.emit("info", "codebase_analysis",
                        f"[{tag}] {state.files_analyzed} files, "
                        f"{len(state.api_endpoints)} endpoints, "
                        f"{len(state.data_models)} models",
                        prd=tag, files=state.files_analyzed)
            
            # Configure review engine via injected factory
            if self._review_engine_factory is None:
                raise ValueError(
                    "No review_engine_factory provided to BulkPRDAnalyzer. "
                    "Pass a ReviewEngineFactory at construction time."
                )
            
            # Determine if LLM analysis is available
            llm_enabled = request.use_llm and bool(self.openai_api_key or self.anthropic_api_key)
            
            dim_names = [d.value for d in prd.dimensions]
            if tc:
                tc.emit("info", "llm_dispatch",
                        f"[{tag}] Running {'AI-powered' if llm_enabled else 'pattern-based'} "
                        f"{', '.join(dim_names)} analysis...",
                        prd=tag, llm=llm_enabled, dimensions=dim_names)
            
            engine = self._review_engine_factory(
                dimensions=prd.dimensions,
                use_llm=llm_enabled,
                llm_only=llm_enabled,
                use_pattern_matching=not llm_enabled,
                use_graph_analysis=not llm_enabled,
                openai_api_key=self.openai_api_key,
                anthropic_api_key=self.anthropic_api_key,
                trace_collector=tc,
            )
            review_result = await engine.review(intent, state)
            
            # Extract findings summary
            findings_by_severity: dict[str, int] = {}
            findings_by_dimension: dict[str, int] = {}
            
            for finding in review_result.all_findings:
                # By severity
                severity_key = finding.severity.value if hasattr(finding.severity, 'value') else str(finding.severity)
                findings_by_severity[severity_key] = findings_by_severity.get(severity_key, 0) + 1
                
                # By dimension
                dimension_key = finding.dimension.value if hasattr(finding.dimension, 'value') else str(finding.dimension)
                findings_by_dimension[dimension_key] = findings_by_dimension.get(dimension_key, 0) + 1
            
            prd.status = "completed"
            duration_ms = (time.time() - start_time) * 1000
            
            if tc:
                tc.emit("info", "report_gen",
                        f"[{tag}] Complete — {len(review_result.all_findings)} findings "
                        f"in {duration_ms:.0f}ms",
                        prd=tag, findings=len(review_result.all_findings),
                        duration_ms=duration_ms)
            
            return SinglePRDResult(
                prd_id=prd.id,
                prd_file_name=prd.display_name,
                codebase_path=prd.codebase_path,
                success=True,
                total_findings=len(review_result.all_findings),
                findings_by_severity=findings_by_severity,
                findings_by_dimension=findings_by_dimension,
                review_id=str(review_result.review_id),
                review_result=review_result,
                duration_ms=duration_ms,
                completed_at=datetime.now(),
            )
            
        except Exception as e:
            prd.status = "failed"
            prd.error_message = str(e)
            logger.error(f"Failed to analyze PRD {prd.display_name}: {e}")
            if tc:
                tc.emit("error", "report_gen", f"[{tag}] Failed: {e}", prd=tag)
            
            return SinglePRDResult(
                prd_id=prd.id,
                prd_file_name=prd.display_name,
                codebase_path=prd.codebase_path,
                success=False,
                error_message=str(e),
                duration_ms=(time.time() - start_time) * 1000,
            )
    
    async def _build_codebase_state(self, codebase_path: str | None) -> State:
        """Build codebase state from path."""
        import asyncio
        from pathlib import Path
        from context_graph.core.models import State
        
        if not codebase_path:
            # Return empty state
            return State(
                api_endpoints=[],
                data_models=[],
                auth_patterns=[],
                existing_controls=[],
                entities=[],
            )
        
        # Analyze codebase using MultiLanguageAnalyzer with language-specific analyzers
        from context_graph.analyzers import (
            MultiLanguageAnalyzer,
            PythonAnalyzer,
            TypeScriptAnalyzer,
            KotlinAnalyzer,
            YAMLAnalyzer,
            JSONAnalyzer,
        )
        
        analyzer = MultiLanguageAnalyzer()
        analyzer.add_analyzer(PythonAnalyzer())
        analyzer.add_analyzer(TypeScriptAnalyzer())
        analyzer.add_analyzer(KotlinAnalyzer())
        analyzer.add_analyzer(YAMLAnalyzer())
        analyzer.add_analyzer(JSONAnalyzer())
        
        try:
            # Run synchronous analyze_codebase in thread pool
            state = await asyncio.to_thread(
                analyzer.analyze_codebase, 
                Path(codebase_path)
            )
            return state
        except Exception as e:
            logger.warning(f"Failed to analyze codebase {codebase_path}: {e}")
            return State(
                api_endpoints=[],
                data_models=[],
                auth_patterns=[],
                existing_controls=[],
                entities=[],
            )
    
    def get_codebase_suggestions(self) -> list[CodebaseSelection]:
        """
        Get codebase suggestions based on usage patterns.
        
        Returns codebases sorted by selection count, with indication
        of which ones exceed the auto-default threshold.
        """
        return self._codebase_tracker.get_all_selections()
    
    def set_default_codebase(self, codebase_path: str | None) -> None:
        """Manually set or clear the default codebase."""
        self._codebase_tracker.set_default(codebase_path)
    
    def get_default_codebase(self) -> str | None:
        """Get the current default codebase."""
        return self._codebase_tracker.current_default


# ==================== Convenience Functions ====================


async def analyze_bulk_prds(
    prd_files: list[dict[str, Any]],
    default_codebase: str | None = None,
    dimensions: list[str] | None = None,
    openai_api_key: str | None = None,
    anthropic_api_key: str | None = None,
    parser_factory: PRDParserFactory | None = None,
    review_engine_factory: ReviewEngineFactory | None = None,
) -> BulkAnalysisResult:
    """
    Convenience function to analyze multiple PRDs.
    
    Args:
        prd_files: List of dicts with 'file_path', 'content', 'codebase_path' (optional)
        default_codebase: Default codebase path for PRDs without one
        dimensions: List of dimension names to analyze
        openai_api_key: OpenAI API key for LLM analysis
        anthropic_api_key: Anthropic API key for LLM analysis
        parser_factory: Factory that creates a PRD parser instance
        review_engine_factory: Factory that creates a configured review engine
        
    Returns:
        BulkAnalysisResult with all results
    """
    # Convert dimension strings to enums
    dimension_enums = []
    if dimensions:
        dimension_map = {
            "security": ReviewDimension.SECURITY,
            "privacy": ReviewDimension.PRIVACY,
            "compliance": ReviewDimension.COMPLIANCE,
            "engineering": ReviewDimension.ENGINEERING,
            "architecture": ReviewDimension.ARCHITECTURE,
        }
        for d in dimensions:
            if d.lower() in dimension_map:
                dimension_enums.append(dimension_map[d.lower()])
    
    # Create PRD file objects
    prds = []
    for prd_data in prd_files:
        prd = PRDFile(
            file_path=prd_data.get("file_path", ""),
            file_name=prd_data.get("file_name", ""),
            content=prd_data.get("content", ""),
            codebase_path=prd_data.get("codebase_path"),
            dimensions=dimension_enums.copy() if dimension_enums else [],
        )
        prds.append(prd)
    
    # Create request
    request = BulkAnalysisRequest(
        prds=prds,
        default_codebase_path=default_codebase,
        default_dimensions=dimension_enums if dimension_enums else [
            ReviewDimension.SECURITY,
            ReviewDimension.PRIVACY,
            ReviewDimension.COMPLIANCE,
            ReviewDimension.ENGINEERING,
            ReviewDimension.ARCHITECTURE,
        ],
    )
    
    # Run analysis
    analyzer = BulkPRDAnalyzer(
        openai_api_key=openai_api_key,
        anthropic_api_key=anthropic_api_key,
        parser_factory=parser_factory,
        review_engine_factory=review_engine_factory,
    )
    
    return await analyzer.analyze(request)
