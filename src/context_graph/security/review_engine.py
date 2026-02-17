"""
Security Review Engine - Orchestrates the complete security review process.

Combines:
- Pattern-based threat matching
- LLM-powered semantic analysis
- Context graph analysis
- Multi-dimension review (Security, Privacy, Compliance)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Union
from uuid import UUID, uuid4

from context_graph.core.models import (
    Intent,
    State,
    SecurityFinding,
    PrivacyFinding,
    ComplianceFinding,
    EngineeringFinding,
    ArchitectureFinding,
    SecurityReview,
    Severity,
    ReviewDimension,
    ComplianceFramework,
    PredictedQuestion,
    PRDQualityScore,
    EffortEstimation,
    FalsePositiveFilterStats,
)
from context_graph.core.graph import ContextGraph
from context_graph.security.delta_analyzer import DeltaAnalyzer, DeltaAnalysisResult
from context_graph.security.threat_patterns import ThreatPatternMatcher
from context_graph.llm.parallel_analyzer import ParallelLLMAnalyzer, ParallelAnalysisResult
from context_graph.tracing.collector import TraceCollector


# Type alias for any finding type
Finding = Union[SecurityFinding, PrivacyFinding, ComplianceFinding, EngineeringFinding, ArchitectureFinding]


@dataclass
class ReviewConfig:
    """Configuration for security review."""
    
    # Analysis options
    use_llm: bool = True
    use_pattern_matching: bool = True
    use_graph_analysis: bool = True
    llm_only: bool = False  # When True, only use LLM findings (ignore pattern/graph)
    
    # Multi-dimension options
    dimensions: list[ReviewDimension] = field(default_factory=lambda: [ReviewDimension.SECURITY])
    compliance_frameworks: list[ComplianceFramework] = field(default_factory=lambda: [
        ComplianceFramework.SOC2,
        ComplianceFramework.HIPAA,
        ComplianceFramework.PCI_DSS,
    ])
    
    # LLM settings
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    model_override: str | None = None  # Per-request LLM model override
    
    # Thresholds
    min_severity: Severity = Severity.LOW
    min_confidence: float = 0.5
    
    # Output options
    include_recommendations: bool = True
    include_mitigations: bool = True


@dataclass
class ReviewResult:
    """Complete security review result."""
    
    review_id: UUID = field(default_factory=uuid4)
    
    # Core components
    intent: Intent = field(default_factory=Intent)
    state: State = field(default_factory=State)
    delta_result: DeltaAnalysisResult | None = None
    
    # Findings by source (legacy)
    pattern_findings: list[SecurityFinding] = field(default_factory=list)
    llm_findings: list[SecurityFinding] = field(default_factory=list)
    graph_findings: list[SecurityFinding] = field(default_factory=list)
    merged_findings: list[SecurityFinding] = field(default_factory=list)
    
    # Findings by dimension (new multi-dimension support)
    security_findings: list[SecurityFinding] = field(default_factory=list)
    privacy_findings: list[PrivacyFinding] = field(default_factory=list)
    compliance_findings: list[ComplianceFinding] = field(default_factory=list)
    engineering_findings: list[EngineeringFinding] = field(default_factory=list)
    architecture_findings: list[ArchitectureFinding] = field(default_factory=list)
    
    # Dimensions that were analyzed
    dimensions_analyzed: list[ReviewDimension] = field(default_factory=list)
    
    # LLM analysis details
    llm_result: ParallelAnalysisResult | None = None
    
    # Multi-dimension LLM results
    privacy_llm_result: ParallelAnalysisResult | None = None
    compliance_llm_result: ParallelAnalysisResult | None = None
    engineering_llm_result: ParallelAnalysisResult | None = None
    architecture_llm_result: ParallelAnalysisResult | None = None
    
    # Summary
    executive_summary: str = ""
    risk_rating: str = ""
    reviewed_at: datetime = field(default_factory=datetime.now)
    
    # False positive filter stats (per dimension)
    fp_filter_stats: list[FalsePositiveFilterStats] = field(default_factory=list)
    
    # PM-focused features (Unified PM Tool)
    predicted_questions: list[PredictedQuestion] = field(default_factory=list)
    prd_quality_score: PRDQualityScore | None = None
    effort_estimation: EffortEstimation | None = None
    original_prd_content: str = ""  # Store original PRD for diff generation
    
    @property
    def all_findings(self) -> list[Finding]:
        """Get all findings from all dimensions."""
        # Prioritize dimension-based findings if available
        if (self.security_findings or self.privacy_findings or self.compliance_findings 
            or self.engineering_findings or self.architecture_findings):
            all_findings: list[Finding] = []
            all_findings.extend(self.security_findings)
            all_findings.extend(self.privacy_findings)
            all_findings.extend(self.compliance_findings)
            all_findings.extend(self.engineering_findings)
            all_findings.extend(self.architecture_findings)
            return all_findings
        
        # Fall back to legacy merged findings
        return self.merged_findings or (
            self.pattern_findings + self.llm_findings + self.graph_findings
        )
    
    @property
    def findings_by_dimension(self) -> dict[ReviewDimension, list[Finding]]:
        """Get findings grouped by dimension."""
        return {
            ReviewDimension.SECURITY: self.security_findings,
            ReviewDimension.PRIVACY: self.privacy_findings,
            ReviewDimension.COMPLIANCE: self.compliance_findings,
            ReviewDimension.ENGINEERING: self.engineering_findings,
            ReviewDimension.ARCHITECTURE: self.architecture_findings,
        }
    
    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.all_findings if f.severity == Severity.CRITICAL)
    
    @property
    def high_count(self) -> int:
        return sum(1 for f in self.all_findings if f.severity == Severity.HIGH)


class SecurityReviewEngine:
    """
    Main orchestrator for security reviews.
    
    Workflow:
    1. Parse PRD to extract Intent
    2. Analyze codebase to build State
    3. Compute Delta (Intent - State)
    4. Run pattern matching on Delta
    5. Run LLM analysis (if configured)
    6. Analyze context graph
    7. Run multi-dimension analysis (Security, Privacy, Compliance) in parallel
    8. Merge and deduplicate findings
    9. Generate report
    """
    
    def __init__(
        self,
        config: ReviewConfig | None = None,
        trace_collector: TraceCollector | None = None,
    ) -> None:
        self.config = config or ReviewConfig()
        self.delta_analyzer = DeltaAnalyzer()
        self.pattern_matcher = ThreatPatternMatcher()
        self._llm_analyzer: ParallelLLMAnalyzer | None = None
        self._graph = ContextGraph()
        self._trace_collector = trace_collector
        
        # Multi-dimension analyzers (lazy init)
        self._privacy_matcher = None
        self._compliance_matcher = None
    
    @property
    def llm_analyzer(self) -> ParallelLLMAnalyzer | None:
        """Lazy-initialize LLM analyzer."""
        if self._llm_analyzer is None and self.config.use_llm:
            if self.config.openai_api_key or self.config.anthropic_api_key:
                kwargs: dict = {
                    "openai_api_key": self.config.openai_api_key,
                    "anthropic_api_key": self.config.anthropic_api_key,
                    "trace_collector": self._trace_collector,
                }
                if self.config.model_override:
                    kwargs["openai_model"] = self.config.model_override
                    kwargs["anthropic_model"] = self.config.model_override
                self._llm_analyzer = ParallelLLMAnalyzer(**kwargs)
        return self._llm_analyzer
    
    @property
    def privacy_matcher(self):
        """Lazy-initialize privacy pattern matcher."""
        if self._privacy_matcher is None:
            from context_graph.security.privacy_analyzer import PrivacyPatternMatcher
            self._privacy_matcher = PrivacyPatternMatcher()
        return self._privacy_matcher
    
    @property
    def compliance_matcher(self):
        """Lazy-initialize compliance pattern matcher."""
        if self._compliance_matcher is None:
            from context_graph.security.compliance_analyzer import CompliancePatternMatcher
            self._compliance_matcher = CompliancePatternMatcher(
                frameworks=self.config.compliance_frameworks
            )
        return self._compliance_matcher
    
    async def review(
        self, 
        intent: Intent, 
        state: State
    ) -> ReviewResult:
        """
        Perform complete security review.
        
        Args:
            intent: Extracted intent from PRD
            state: Current codebase state
            
        Returns:
            ReviewResult with all findings and analysis
        """
        result = ReviewResult(
            intent=intent,
            state=state,
            dimensions_analyzed=self.config.dimensions.copy(),
        )
        
        # Step 1: Compute delta
        result.delta_result = self.delta_analyzer.analyze(intent, state)
        
        # Step 2: Build context graph
        self._build_graph(intent, state, result.delta_result)
        
        # Step 3: Run multi-dimension analyses in parallel
        await self._run_multi_dimension_analysis(result, intent, state)
        
        # Step 4: Also run legacy analysis for backward compatibility
        if self.config.use_graph_analysis and ReviewDimension.SECURITY in self.config.dimensions:
            result.graph_findings = self._analyze_graph()
        
        # Step 5: Collect false positive filter stats
        if self.llm_analyzer:
            for dim_name, fp_result in self.llm_analyzer.fp_filter_results.items():
                result.fp_filter_stats.append(FalsePositiveFilterStats(
                    dimension=dim_name,
                    original_count=fp_result.original_count,
                    final_count=fp_result.final_count,
                    total_removed=fp_result.total_removed,
                    total_downgraded=fp_result.total_downgraded,
                    total_iterations=fp_result.total_iterations,
                    removal_rate=fp_result.removal_rate,
                    execution_mode=fp_result.execution_mode,
                    iteration_details=[
                        {
                            "round": ir.round_num,
                            "strategy": ir.strategy_name,
                            "input": ir.input_count,
                            "kept": ir.kept_count,
                            "removed": ir.removed_count,
                            "downgraded": ir.downgraded_count,
                            "reasons": ir.removal_reasons,
                        }
                        for ir in fp_result.iteration_results
                    ],
                    removed_findings=fp_result.removed_findings,
                ))
        
        # Step 6: Merge findings (legacy support)
        result.merged_findings = self._merge_findings(result)
        
        # Step 7: Generate summary
        result.executive_summary = self._generate_summary(result)
        result.risk_rating = self._compute_risk_rating(result)
        
        # Step 8: Generate PM-focused features (Unified PM Tool) - Feature-flagged
        from context_graph.config.features import get_features
        features = get_features()
        
        if (features.enable_prd_changes or 
            features.enable_prd_quality_scoring or 
            features.enable_effort_estimation):
            result.original_prd_content = intent.raw_content
            await self._generate_pm_features(result, intent, state, features)
        
        return result
    
    async def _run_multi_dimension_analysis(
        self,
        result: ReviewResult,
        intent: Intent,
        state: State,
    ) -> None:
        """Run parallel analysis across all configured dimensions."""
        tasks = []
        task_dimensions = []
        
        # Prepare data dicts for LLM
        intent_dict = self._prepare_intent_dict(intent)
        state_dict = self._prepare_state_dict(state)
        delta_dict = self._prepare_delta_dict(result.delta_result)
        
        # Queue up dimension analyses
        if ReviewDimension.SECURITY in self.config.dimensions:
            tasks.append(self._run_security_dimension(
                result.delta_result, intent_dict, state_dict, delta_dict
            ))
            task_dimensions.append(ReviewDimension.SECURITY)
        
        if ReviewDimension.PRIVACY in self.config.dimensions:
            tasks.append(self._run_privacy_dimension(
                result.delta_result, intent_dict, state_dict, delta_dict
            ))
            task_dimensions.append(ReviewDimension.PRIVACY)
        
        if ReviewDimension.COMPLIANCE in self.config.dimensions:
            tasks.append(self._run_compliance_dimension(
                result.delta_result, intent_dict, state_dict, delta_dict
            ))
            task_dimensions.append(ReviewDimension.COMPLIANCE)
        
        if ReviewDimension.ENGINEERING in self.config.dimensions:
            tasks.append(self._run_engineering_dimension(
                result.delta_result, state, intent_dict, state_dict, delta_dict
            ))
            task_dimensions.append(ReviewDimension.ENGINEERING)
        
        if ReviewDimension.ARCHITECTURE in self.config.dimensions:
            tasks.append(self._run_architecture_dimension(
                result.delta_result, state, intent, intent_dict, state_dict, delta_dict
            ))
            task_dimensions.append(ReviewDimension.ARCHITECTURE)
        
        # Execute all dimensions in parallel
        if tasks:
            dimension_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, dim_result in enumerate(dimension_results):
                dimension = task_dimensions[i]
                
                if isinstance(dim_result, Exception):
                    import logging
                    logging.error(f"{dimension.value} analysis failed: {dim_result}")
                    continue
                
                if dimension == ReviewDimension.SECURITY:
                    findings, llm_result = dim_result
                    result.security_findings = findings
                    result.llm_result = llm_result
                    # Also populate legacy fields
                    result.pattern_findings = [f for f in findings if f.source_type == "pattern"]
                    result.llm_findings = [f for f in findings if f.source_type == "llm"]
                
                elif dimension == ReviewDimension.PRIVACY:
                    findings, llm_result = dim_result
                    result.privacy_findings = findings
                    result.privacy_llm_result = llm_result
                
                elif dimension == ReviewDimension.COMPLIANCE:
                    findings, llm_result = dim_result
                    result.compliance_findings = findings
                    result.compliance_llm_result = llm_result
                
                elif dimension == ReviewDimension.ENGINEERING:
                    findings, llm_result = dim_result
                    result.engineering_findings = findings
                    result.engineering_llm_result = llm_result
                
                elif dimension == ReviewDimension.ARCHITECTURE:
                    findings, llm_result = dim_result
                    result.architecture_findings = findings
                    result.architecture_llm_result = llm_result
    
    async def _run_security_dimension(
        self,
        delta_result: DeltaAnalysisResult,
        intent_dict: dict,
        state_dict: dict,
        delta_dict: dict,
    ) -> tuple[list[SecurityFinding], ParallelAnalysisResult | None]:
        """Run security analysis (STRIDE + OWASP)."""
        findings: list[SecurityFinding] = []
        llm_result = None
        
        # Pattern matching
        if self.config.use_pattern_matching:
            pattern_findings = self.pattern_matcher.match(delta_result)
            findings.extend(pattern_findings)
        
        # LLM analysis
        if self.config.use_llm and self.llm_analyzer:
            llm_result = await self.llm_analyzer.security_review(
                intent_dict, state_dict, delta_dict
            )
            llm_findings = self._convert_llm_findings(llm_result)
            
            if self.config.llm_only:
                findings = llm_findings
            else:
                findings.extend(llm_findings)
        
        # Deduplicate
        findings = self._deduplicate_security_findings(findings)
        
        return findings, llm_result
    
    async def _run_privacy_dimension(
        self,
        delta_result: DeltaAnalysisResult,
        intent_dict: dict,
        state_dict: dict,
        delta_dict: dict,
    ) -> tuple[list[PrivacyFinding], ParallelAnalysisResult | None]:
        """Run privacy analysis (LINDDUN + GDPR)."""
        findings: list[PrivacyFinding] = []
        llm_result = None
        
        # Pattern matching
        if self.config.use_pattern_matching:
            pattern_findings = self.privacy_matcher.match(delta_result)
            findings.extend(pattern_findings)
        
        # LLM analysis
        if self.config.use_llm and self.llm_analyzer:
            llm_result = await self.llm_analyzer.privacy_review(
                intent_dict, state_dict, delta_dict
            )
            llm_findings = self._convert_llm_privacy_findings(llm_result)
            
            if self.config.llm_only:
                findings = llm_findings
            else:
                findings.extend(llm_findings)
        
        # Deduplicate
        findings = self._deduplicate_privacy_findings(findings)
        
        return findings, llm_result
    
    async def _run_compliance_dimension(
        self,
        delta_result: DeltaAnalysisResult,
        intent_dict: dict,
        state_dict: dict,
        delta_dict: dict,
    ) -> tuple[list[ComplianceFinding], ParallelAnalysisResult | None]:
        """Run compliance analysis (SOC2, HIPAA, PCI-DSS)."""
        findings: list[ComplianceFinding] = []
        llm_result = None
        
        # Pattern matching
        if self.config.use_pattern_matching:
            pattern_findings = self.compliance_matcher.match(delta_result)
            findings.extend(pattern_findings)
        
        # LLM analysis
        if self.config.use_llm and self.llm_analyzer:
            frameworks = [f.value for f in self.config.compliance_frameworks]
            llm_result = await self.llm_analyzer.compliance_review(
                intent_dict, state_dict, delta_dict, frameworks
            )
            llm_findings = self._convert_llm_compliance_findings(llm_result)
            
            if self.config.llm_only:
                findings = llm_findings
            else:
                findings.extend(llm_findings)
        
        # Deduplicate
        findings = self._deduplicate_compliance_findings(findings)
        
        return findings, llm_result
    
    async def _run_engineering_dimension(
        self,
        delta_result: DeltaAnalysisResult,
        state: State,
        intent_dict: dict,
        state_dict: dict,
        delta_dict: dict,
    ) -> tuple[list[EngineeringFinding], ParallelAnalysisResult | None]:
        """Run engineering feasibility and effort analysis.
        
        This analysis focuses on:
        1. Understanding current codebase context (complexity, patterns, debt)
        2. Assessing PRD feature feasibility based on existing code
        3. Providing detailed time estimates based on actual metrics
        """
        import logging
        from context_graph.security.engineering_patterns import EngineeringPatternMatcher
        
        logging.info("Starting engineering dimension analysis")
        findings: list[EngineeringFinding] = []
        llm_result: ParallelAnalysisResult | None = None
        
        # Build comprehensive engineering metrics from state
        engineering_metrics = self._build_engineering_metrics(state)
        logging.info(f"Engineering metrics: {engineering_metrics.get('source_files', 0)} files, "
                    f"{engineering_metrics.get('total_lines', 0)} lines, "
                    f"health: {engineering_metrics.get('codebase_health', 'unknown')}")
        
        # Pattern matching for quick heuristic findings
        if self.config.use_pattern_matching:
            logging.info("Running engineering pattern matching")
            matcher = EngineeringPatternMatcher()
            pattern_findings = matcher.match(
                delta_result,
                state=state,
                engineering_metrics=engineering_metrics,
            )
            logging.info(f"Pattern matching found {len(pattern_findings)} findings")
            findings.extend(pattern_findings)
        
        # LLM analysis for detailed feasibility and time estimation
        if self.config.use_llm and self.llm_analyzer:
            logging.info("Running engineering LLM feasibility analysis")
            try:
                # Pass engineering metrics to LLM for context-aware analysis
                llm_result = await self.llm_analyzer.engineering_review(
                    intent_dict, state_dict, delta_dict, engineering_metrics
                )
                logging.info(f"LLM returned {len(llm_result.merged_findings)} merged findings")
                llm_findings = self._convert_llm_engineering_findings(llm_result)
                logging.info(f"Converted to {len(llm_findings)} EngineeringFinding objects")
                
                if self.config.llm_only:
                    findings = llm_findings
                else:
                    findings.extend(llm_findings)
            except Exception as e:
                logging.error(f"Engineering LLM analysis failed: {e}", exc_info=True)
        else:
            logging.warning(f"LLM analysis skipped: use_llm={self.config.use_llm}, llm_analyzer={self.llm_analyzer is not None}")
        
        # Deduplicate by title
        seen_titles: set[str] = set()
        unique_findings: list[EngineeringFinding] = []
        for f in findings:
            key = f.title.lower()[:40]
            if key not in seen_titles:
                seen_titles.add(key)
                unique_findings.append(f)
        
        logging.info(f"Engineering analysis complete: {len(unique_findings)} unique findings")
        return unique_findings, llm_result
    
    async def _run_architecture_dimension(
        self,
        delta_result: DeltaAnalysisResult,
        state: State,
        intent: Intent,
        intent_dict: dict,
        state_dict: dict,
        delta_dict: dict,
    ) -> tuple[list[ArchitectureFinding], ParallelAnalysisResult | None]:
        """Run architecture analysis (API design, dependencies, resilience)."""
        from context_graph.security.architecture_patterns import ArchitecturePatternMatcher
        
        findings: list[ArchitectureFinding] = []
        llm_result: ParallelAnalysisResult | None = None
        
        # Build architecture metrics from state
        architecture_metrics = self._build_architecture_metrics(state)
        
        # Pattern matching
        if self.config.use_pattern_matching:
            matcher = ArchitecturePatternMatcher()
            pattern_findings = matcher.match(
                delta_result,
                state=state,
                intent=intent,
                architecture_metrics=architecture_metrics,
            )
            findings.extend(pattern_findings)
        
        # LLM analysis
        if self.config.use_llm and self.llm_analyzer:
            llm_result = await self.llm_analyzer.architecture_review(
                intent_dict, state_dict, delta_dict
            )
            llm_findings = self._convert_llm_architecture_findings(llm_result)
            
            if self.config.llm_only:
                findings = llm_findings
            else:
                findings.extend(llm_findings)
        
        # Deduplicate by title
        seen_titles: set[str] = set()
        unique_findings: list[ArchitectureFinding] = []
        for f in findings:
            key = f.title.lower()[:40]
            if key not in seen_titles:
                seen_titles.add(key)
                unique_findings.append(f)
        
        return unique_findings, llm_result
    
    def _build_engineering_metrics(self, state: State) -> dict:
        """Build comprehensive engineering metrics from codebase state.
        
        These metrics provide the LLM with detailed context about the current codebase
        to make accurate feasibility assessments and time estimates.
        """
        from typing import Any
        
        # Base metrics from state
        metrics: dict[str, Any] = {
            "source_files": state.files_analyzed,
            "total_lines": state.lines_of_code,
            "existing_controls": state.existing_controls,
            "has_ci_cd": "automated_testing" in state.existing_controls or "linting" in state.existing_controls,
            "has_linting_config": "linting" in state.existing_controls,
            "has_dependency_lock": "dependency_lock" in state.existing_controls,
            "has_type_safety": "type_safety" in state.existing_controls,
            "has_error_handling": "error_handling" in state.existing_controls,
            "has_logging": "logging" in state.existing_controls,
        }
        
        # File type breakdown
        test_files = 0
        source_files = 0
        config_files = 0
        doc_files = 0
        
        # Complexity tracking
        high_complexity_files: list[str] = []
        complexity_scores: list[int] = []
        
        # Tech debt indicators
        total_todos = 0
        total_fixmes = 0
        total_tech_debt = 0
        
        # Language breakdown
        languages: dict[str, int] = {}
        
        # Module/class/function counts
        total_functions = 0
        total_classes = 0
        
        for entity in state.entities:
            props = entity.properties or {}
            
            # File type tracking
            if props.get("file_type") == "test":
                test_files += 1
            elif entity.entity_type.value == "module":
                source_files += 1
            
            if props.get("is_config"):
                config_files += 1
            if props.get("is_documentation"):
                doc_files += 1
            
            # Complexity tracking
            complexity_score = props.get("complexity_score", 0)
            if complexity_score > 0:
                complexity_scores.append(complexity_score)
                if complexity_score > 70:
                    high_complexity_files.append(entity.source or entity.name)
            
            # Tech debt indicators
            technical_debt = props.get("technical_debt", 0)
            total_tech_debt += technical_debt
            total_todos += props.get("todo_count", 0)
            total_fixmes += props.get("fixme_count", 0)
            
            # Function/class counts
            total_functions += props.get("function_count", 0)
            total_classes += props.get("class_count", 0)
            
            # Language tracking
            lang = props.get("language")
            if lang:
                languages[lang] = languages.get(lang, 0) + 1
        
        # Calculate aggregates
        metrics["test_files"] = test_files
        metrics["source_files"] = max(source_files, state.files_analyzed)
        metrics["config_files"] = config_files
        metrics["documentation_files"] = doc_files
        
        # Test coverage ratio
        if metrics["source_files"] > 0:
            metrics["test_to_code_ratio"] = round(test_files / metrics["source_files"], 2)
        else:
            metrics["test_to_code_ratio"] = 0.0
        
        # Complexity metrics
        metrics["high_complexity_files"] = high_complexity_files[:10]
        metrics["high_complexity_count"] = len(high_complexity_files)
        if complexity_scores:
            metrics["avg_complexity_score"] = round(sum(complexity_scores) / len(complexity_scores), 1)
            metrics["max_complexity_score"] = max(complexity_scores)
        else:
            metrics["avg_complexity_score"] = 0
            metrics["max_complexity_score"] = 0
        
        # Tech debt summary
        metrics["total_todos"] = total_todos
        metrics["total_fixmes"] = total_fixmes
        metrics["total_tech_debt_items"] = total_tech_debt
        
        # Code structure
        metrics["total_functions"] = total_functions
        metrics["total_classes"] = total_classes
        metrics["languages"] = languages
        metrics["primary_language"] = max(languages.items(), key=lambda x: x[1])[0] if languages else "unknown"
        
        # Codebase size categorization
        total_lines = metrics["total_lines"]
        if total_lines < 5000:
            metrics["codebase_size_category"] = "small"
        elif total_lines < 50000:
            metrics["codebase_size_category"] = "medium"
        elif total_lines < 200000:
            metrics["codebase_size_category"] = "large"
        else:
            metrics["codebase_size_category"] = "very_large"
        
        # Overall health assessment
        health_score = 100
        if metrics["test_to_code_ratio"] < 0.3:
            health_score -= 20
        if metrics["high_complexity_count"] > 5:
            health_score -= 15
        if metrics["avg_complexity_score"] > 50:
            health_score -= 15
        if total_tech_debt > 20:
            health_score -= 10
        if not metrics["has_ci_cd"]:
            health_score -= 10
        if not metrics["has_linting_config"]:
            health_score -= 5
        
        metrics["codebase_health_score"] = max(0, health_score)
        if health_score >= 80:
            metrics["codebase_health"] = "healthy"
        elif health_score >= 60:
            metrics["codebase_health"] = "moderate_debt"
        elif health_score >= 40:
            metrics["codebase_health"] = "high_debt"
        else:
            metrics["codebase_health"] = "critical_debt"
        
        return metrics
    
    def _build_architecture_metrics(self, state: State) -> dict:
        """Build architecture metrics from codebase state."""
        metrics = {
            "api_contracts": 0,
            "services_identified": 0,
            "external_dependencies": 0,
            "internal_dependencies": 0,
            "has_dependency_lock": "dependency_lock" in state.existing_controls,
            "adrs_found": 0,
            "architectural_patterns": [],
            "discovered_services": [],
        }
        
        for entity in state.entities:
            props = entity.properties or {}
            
            if props.get("contract_type") in ["openapi", "asyncapi", "graphql"]:
                metrics["api_contracts"] += 1
            
            if entity.entity_type.value == "service":
                metrics["services_identified"] += 1
                if entity.name:
                    metrics["discovered_services"].append(entity.name)
            
            if props.get("doc_type") == "adr":
                metrics["adrs_found"] += 1
            
            if props.get("dependency_count"):
                metrics["external_dependencies"] += props["dependency_count"]
            
            if props.get("patterns"):
                for p in props["patterns"]:
                    if p not in metrics["architectural_patterns"]:
                        metrics["architectural_patterns"].append(p)
        
        return metrics
    
    def _prepare_intent_dict(self, intent: Intent) -> dict:
        """Prepare intent data for LLM."""
        return {
            "title": intent.title,
            "summary": intent.summary,
            "features": intent.features,
            "api_changes": intent.api_changes,
            "auth_requirements": intent.auth_requirements,
            "data_sensitivity": intent.data_sensitivity,
            "external_integrations": intent.external_integrations,
        }
    
    def _prepare_state_dict(self, state: State) -> dict:
        """Prepare state data for LLM."""
        return {
            "api_endpoints": state.api_endpoints[:20],
            "data_models": state.data_models[:20],
            "auth_patterns": state.auth_patterns,
            "existing_controls": state.existing_controls,
        }
    
    def _prepare_delta_dict(self, delta: DeltaAnalysisResult) -> dict:
        """Prepare delta data for LLM."""
        return {
            "new_endpoints": delta.new_endpoints,
            "modified_endpoints": delta.modified_endpoints,
            "new_data_models": delta.new_data_models,
            "attack_surface_changes": delta.attack_surface_changes,
            "auth_requirement_changes": delta.auth_requirement_changes,
            "introduces_pii": delta.introduces_pii,
            "trust_boundary_impacts": delta.trust_boundary_impacts,
            "summary": delta.delta.summary,
        }
    
    def _convert_llm_privacy_findings(
        self,
        llm_result: ParallelAnalysisResult,
    ) -> list[PrivacyFinding]:
        """Convert LLM privacy analysis results to PrivacyFinding objects."""
        from context_graph.core.models import PrivacyCategory
        
        findings: list[PrivacyFinding] = []
        
        severity_map = {
            "critical": Severity.CRITICAL,
            "high": Severity.HIGH,
            "medium": Severity.MEDIUM,
            "low": Severity.LOW,
            "info": Severity.INFO,
        }
        
        for finding_data in llm_result.merged_findings:
            severity_str = finding_data.get("severity", "medium").lower()
            
            finding = PrivacyFinding(
                id=uuid4(),
                title=finding_data.get("title", "Privacy Finding"),
                description=finding_data.get("description", ""),
                severity=severity_map.get(severity_str, Severity.MEDIUM),
                category=PrivacyCategory.DATA_DISCLOSURE,
                dimension=ReviewDimension.PRIVACY,
                data_subjects=finding_data.get("data_subjects", ["users"]),
                personal_data_types=finding_data.get("personal_data_types", []),
                processing_activities=finding_data.get("processing_activities", []),
                applicable_regulations=finding_data.get("applicable_regulations", []),
                legal_basis_required=finding_data.get("legal_basis_required", False),
                consent_required=finding_data.get("consent_required", False),
                recommendation=finding_data.get("recommendation", ""),
                confidence=finding_data.get("confidence", 0.7),
                source_type="llm",
                source_reference=", ".join(finding_data.get("providers", [])),
            )
            findings.append(finding)
        
        return findings
    
    def _convert_llm_compliance_findings(
        self,
        llm_result: ParallelAnalysisResult,
    ) -> list[ComplianceFinding]:
        """Convert LLM compliance analysis results to ComplianceFinding objects."""
        from context_graph.core.models import ComplianceCategory
        
        findings: list[ComplianceFinding] = []
        
        severity_map = {
            "critical": Severity.CRITICAL,
            "high": Severity.HIGH,
            "medium": Severity.MEDIUM,
            "low": Severity.LOW,
            "info": Severity.INFO,
        }
        
        framework_map = {
            "soc2": ComplianceFramework.SOC2,
            "hipaa": ComplianceFramework.HIPAA,
            "pci_dss": ComplianceFramework.PCI_DSS,
            "iso_27001": ComplianceFramework.ISO_27001,
            "gdpr": ComplianceFramework.GDPR,
            "ccpa": ComplianceFramework.CCPA,
        }
        
        for finding_data in llm_result.merged_findings:
            severity_str = finding_data.get("severity", "medium").lower()
            framework_str = finding_data.get("framework", "soc2").lower()
            
            finding = ComplianceFinding(
                id=uuid4(),
                title=finding_data.get("title", "Compliance Finding"),
                description=finding_data.get("description", ""),
                severity=severity_map.get(severity_str, Severity.MEDIUM),
                category=ComplianceCategory.REGULATORY_VIOLATION,
                dimension=ReviewDimension.COMPLIANCE,
                framework=framework_map.get(framework_str, ComplianceFramework.SOC2),
                control_id=finding_data.get("control_id", ""),
                control_description=finding_data.get("control_description", ""),
                requirement_text=finding_data.get("requirement_text", ""),
                current_state=finding_data.get("current_state", ""),
                required_state=finding_data.get("required_state", ""),
                gap_description=finding_data.get("gap_description", ""),
                recommendation=finding_data.get("recommendation", ""),
                remediation_effort=finding_data.get("remediation_effort", "medium"),
                confidence=finding_data.get("confidence", 0.7),
                source_type="llm",
                source_reference=", ".join(finding_data.get("providers", [])),
            )
            findings.append(finding)
        
        return findings
    
    def _convert_llm_engineering_findings(
        self,
        llm_result: ParallelAnalysisResult,
    ) -> list[EngineeringFinding]:
        """Convert LLM engineering analysis results to EngineeringFinding objects.
        
        The new prompt format includes feasibility assessment and time estimates,
        which are extracted and included in the findings.
        """
        from context_graph.core.models import EngineeringCategory
        
        findings: list[EngineeringFinding] = []
        
        severity_map = {
            "critical": Severity.CRITICAL,
            "high": Severity.HIGH,
            "medium": Severity.MEDIUM,
            "low": Severity.LOW,
            "info": Severity.INFO,
        }
        
        category_map = {
            # New categories from updated prompt
            "feasibility_blocker": EngineeringCategory.HIGH_COMPLEXITY,
            "missing_foundation": EngineeringCategory.MISSING_TESTS,
            "tech_debt_impact": EngineeringCategory.TODO_FIXME,
            "test_gap": EngineeringCategory.MISSING_TESTS,
            "integration_risk": EngineeringCategory.TIGHT_COUPLING,
            "dependency_issue": EngineeringCategory.TIGHT_COUPLING,
            "skill_gap": EngineeringCategory.MISSING_DOCUMENTATION,
            "timeline_risk": EngineeringCategory.HIGH_COMPLEXITY,
            # Existing categories
            "high_complexity": EngineeringCategory.HIGH_COMPLEXITY,
            "deep_nesting": EngineeringCategory.DEEP_NESTING,
            "long_functions": EngineeringCategory.LONG_FUNCTIONS,
            "large_files": EngineeringCategory.LARGE_FILES,
            "missing_tests": EngineeringCategory.MISSING_TESTS,
            "low_test_coverage": EngineeringCategory.LOW_TEST_COVERAGE,
            "flaky_tests": EngineeringCategory.FLAKY_TESTS,
            "missing_documentation": EngineeringCategory.MISSING_DOCUMENTATION,
            "outdated_documentation": EngineeringCategory.OUTDATED_DOCUMENTATION,
            "missing_docs": EngineeringCategory.MISSING_DOCUMENTATION,
            "missing_error_handling": EngineeringCategory.MISSING_ERROR_HANDLING,
            "insufficient_logging": EngineeringCategory.INSUFFICIENT_LOGGING,
            "missing_logging": EngineeringCategory.INSUFFICIENT_LOGGING,
            "missing_metrics": EngineeringCategory.MISSING_METRICS,
            "no_health_checks": EngineeringCategory.NO_HEALTH_CHECKS,
            "todo_fixme": EngineeringCategory.TODO_FIXME,
            "tech_debt": EngineeringCategory.TODO_FIXME,
            "deprecated_code": EngineeringCategory.DEPRECATED_CODE,
            "code_duplication": EngineeringCategory.CODE_DUPLICATION,
            "magic_numbers": EngineeringCategory.MAGIC_NUMBERS,
            "missing_type_hints": EngineeringCategory.MISSING_TYPE_HINTS,
            "tight_coupling": EngineeringCategory.TIGHT_COUPLING,
            "circular_dependencies": EngineeringCategory.CIRCULAR_DEPENDENCIES,
            "no_ci_cd": EngineeringCategory.NO_CI_CD,
            "missing_ci_cd": EngineeringCategory.NO_CI_CD,
            "no_linting": EngineeringCategory.NO_LINTING,
            "no_automated_tests": EngineeringCategory.NO_AUTOMATED_TESTS,
        }
        
        for finding_data in llm_result.merged_findings:
            severity_str = finding_data.get("severity", "medium").lower()
            category_str = finding_data.get("category", "high_complexity").lower().replace(" ", "_").replace("-", "_")
            
            finding = EngineeringFinding(
                id=uuid4(),
                title=finding_data.get("title", "Engineering Finding"),
                description=finding_data.get("description", ""),
                severity=severity_map.get(severity_str, Severity.MEDIUM),
                category=category_map.get(category_str, EngineeringCategory.HIGH_COMPLEXITY),
                dimension=ReviewDimension.ENGINEERING,
                affected_files=finding_data.get("affected_files", []),
                affected_functions=finding_data.get("affected_functions", []),
                estimated_effort=finding_data.get("estimated_effort", "medium"),
                estimated_days=finding_data.get("estimated_days", finding_data.get("impact_on_timeline", "")),
                recommendation=finding_data.get("recommendation", ""),
                confidence=finding_data.get("confidence", 0.7),
                source_type="llm",
                source_reference=", ".join(finding_data.get("providers", [])),
            )
            findings.append(finding)
        
        # Extract top-level feasibility and time estimate info if available
        for response in llm_result.responses:
            data = response.structured_data
            
            # Extract implementation time estimate as a high-level finding
            time_estimate = data.get("implementation_time_estimate", {})
            if time_estimate and time_estimate.get("total_estimate"):
                total = time_estimate["total_estimate"]
                realistic_days = total.get("realistic_days", 0)
                confidence = total.get("confidence_level", "medium")
                
                estimate_finding = EngineeringFinding(
                    id=uuid4(),
                    title="Implementation Time Estimate",
                    description=(
                        f"Based on codebase analysis, estimated implementation time is "
                        f"{total.get('optimistic_days', 'N/A')}-{total.get('pessimistic_days', 'N/A')} days "
                        f"(realistic: {realistic_days} days). "
                        f"Confidence: {confidence}."
                    ),
                    severity=Severity.INFO,
                    category=EngineeringCategory.HIGH_COMPLEXITY,
                    dimension=ReviewDimension.ENGINEERING,
                    estimated_effort="info",
                    estimated_days=f"{realistic_days} days (realistic)",
                    recommendation="Review breakdown by phase for detailed planning.",
                    confidence=0.8 if confidence == "high" else 0.6 if confidence == "medium" else 0.4,
                    source_type="llm",
                    source_reference=response.provider,
                )
                findings.insert(0, estimate_finding)  # Put estimate at top
            
            # Extract feasibility assessment as a finding
            feasibility = data.get("feasibility_assessment", {})
            if feasibility and feasibility.get("overall_feasibility"):
                feasibility_finding = EngineeringFinding(
                    id=uuid4(),
                    title=f"Feasibility Assessment: {feasibility.get('overall_feasibility', 'Unknown').title()}",
                    description=(
                        f"{feasibility.get('executive_summary', '')} "
                        f"Architectural fit: {feasibility.get('architectural_fit', 'Unknown')}. "
                        f"Refactoring needed: {feasibility.get('refactoring_needed', 'Unknown')}."
                    ),
                    severity=Severity.INFO,
                    category=EngineeringCategory.HIGH_COMPLEXITY,
                    dimension=ReviewDimension.ENGINEERING,
                    estimated_effort=feasibility.get("overall_feasibility", "unknown"),
                    confidence=float(feasibility.get("feasibility_score", 5)) / 10,
                    source_type="llm",
                    source_reference=response.provider,
                )
                findings.insert(0, feasibility_finding)  # Put feasibility at top
            
            # Only process first response's summary findings
            break
        
        return findings
    
    def _convert_llm_architecture_findings(
        self,
        llm_result: ParallelAnalysisResult,
    ) -> list[ArchitectureFinding]:
        """Convert LLM architecture analysis results to ArchitectureFinding objects."""
        from context_graph.core.models import ArchitectureCategory
        
        findings: list[ArchitectureFinding] = []
        
        severity_map = {
            "critical": Severity.CRITICAL,
            "high": Severity.HIGH,
            "medium": Severity.MEDIUM,
            "low": Severity.LOW,
            "info": Severity.INFO,
        }
        
        category_map = {
            # API Design
            "missing_api_contract": ArchitectureCategory.MISSING_API_CONTRACT,
            "inconsistent_api": ArchitectureCategory.INCONSISTENT_API,
            "no_api_versioning": ArchitectureCategory.NO_API_VERSIONING,
            "missing_versioning": ArchitectureCategory.NO_API_VERSIONING,
            "breaking_change": ArchitectureCategory.BREAKING_CHANGE,
            # Service Design
            "missing_service_boundary": ArchitectureCategory.MISSING_SERVICE_BOUNDARY,
            "poor_service_boundary": ArchitectureCategory.MISSING_SERVICE_BOUNDARY,
            "monolith_coupling": ArchitectureCategory.MONOLITH_COUPLING,
            "distributed_monolith": ArchitectureCategory.DISTRIBUTED_MONOLITH,
            "no_service_mesh": ArchitectureCategory.NO_SERVICE_MESH,
            # Data Architecture
            "missing_data_model": ArchitectureCategory.MISSING_DATA_MODEL,
            "poor_data_model": ArchitectureCategory.MISSING_DATA_MODEL,
            "data_inconsistency": ArchitectureCategory.DATA_INCONSISTENCY,
            "no_data_validation": ArchitectureCategory.NO_DATA_VALIDATION,
            "schema_drift": ArchitectureCategory.SCHEMA_DRIFT,
            # Dependencies
            "circular_dependency": ArchitectureCategory.CIRCULAR_DEPENDENCY,
            "missing_dependency_lock": ArchitectureCategory.MISSING_DEPENDENCY_LOCK,
            "outdated_dependencies": ArchitectureCategory.OUTDATED_DEPENDENCIES,
            "too_many_dependencies": ArchitectureCategory.TOO_MANY_DEPENDENCIES,
            # Communication
            "no_retry_logic": ArchitectureCategory.NO_RETRY_LOGIC,
            "missing_resilience": ArchitectureCategory.NO_RETRY_LOGIC,
            "missing_circuit_breaker": ArchitectureCategory.MISSING_CIRCUIT_BREAKER,
            "sync_over_async": ArchitectureCategory.SYNC_OVER_ASYNC,
            "no_idempotency": ArchitectureCategory.NO_IDEMPOTENCY,
            # Documentation
            "missing_adr": ArchitectureCategory.MISSING_ADR,
            "missing_documentation": ArchitectureCategory.MISSING_ADR,
            "outdated_architecture_docs": ArchitectureCategory.OUTDATED_ARCHITECTURE_DOCS,
            "no_system_diagram": ArchitectureCategory.NO_SYSTEM_DIAGRAM,
            # Scalability
            "single_point_of_failure": ArchitectureCategory.SINGLE_POINT_OF_FAILURE,
            "no_horizontal_scaling": ArchitectureCategory.NO_HORIZONTAL_SCALING,
        }
        
        for finding_data in llm_result.merged_findings:
            severity_str = finding_data.get("severity", "medium").lower()
            category_str = finding_data.get("category", "missing_api_contract").lower().replace(" ", "_").replace("-", "_")
            
            finding = ArchitectureFinding(
                id=uuid4(),
                title=finding_data.get("title", "Architecture Finding"),
                description=finding_data.get("description", ""),
                severity=severity_map.get(severity_str, Severity.MEDIUM),
                category=category_map.get(category_str, ArchitectureCategory.MISSING_API_CONTRACT),
                dimension=ReviewDimension.ARCHITECTURE,
                affected_services=finding_data.get("affected_services", []),
                affected_apis=finding_data.get("affected_apis", []),
                architectural_pattern=finding_data.get("architectural_pattern", ""),
                breaking_change=finding_data.get("breaking_change", False),
                backward_compatible=finding_data.get("backward_compatible", True),
                migration_required=finding_data.get("migration_required", False),
                recommendation=finding_data.get("recommendation", ""),
                confidence=finding_data.get("confidence", 0.7),
                source_type="llm",
                source_reference=", ".join(finding_data.get("providers", [])),
            )
            findings.append(finding)
        
        return findings
    
    def _deduplicate_security_findings(
        self,
        findings: list[SecurityFinding],
    ) -> list[SecurityFinding]:
        """Deduplicate security findings."""
        seen_titles: set[str] = set()
        unique: list[SecurityFinding] = []
        
        for finding in findings:
            key = finding.title.lower()[:40]
            if key not in seen_titles:
                seen_titles.add(key)
                unique.append(finding)
        
        return unique
    
    def _deduplicate_privacy_findings(
        self,
        findings: list[PrivacyFinding],
    ) -> list[PrivacyFinding]:
        """Deduplicate privacy findings."""
        seen_titles: set[str] = set()
        unique: list[PrivacyFinding] = []
        
        for finding in findings:
            key = finding.title.lower()[:40]
            if key not in seen_titles:
                seen_titles.add(key)
                unique.append(finding)
        
        return unique
    
    def _deduplicate_compliance_findings(
        self,
        findings: list[ComplianceFinding],
    ) -> list[ComplianceFinding]:
        """Deduplicate compliance findings."""
        seen_keys: set[str] = set()
        unique: list[ComplianceFinding] = []
        
        for finding in findings:
            key = f"{finding.framework.value}:{finding.control_id}:{finding.title.lower()[:30]}"
            if key not in seen_keys:
                seen_keys.add(key)
                unique.append(finding)
        
        return unique
    
    def _build_graph(
        self, 
        intent: Intent, 
        state: State, 
        delta: DeltaAnalysisResult
    ) -> None:
        """Build context graph from intent and state."""
        self._graph = ContextGraph()
        
        # Add state entities
        for entity in state.entities:
            self._graph.add_entity(entity)
        
        # Add state relationships
        for relationship in state.relationships:
            self._graph.add_relationship(relationship)
        
        # Add intent entities
        for entity in intent.data_entities:
            self._graph.add_entity(entity)
        
        # Add delta entities
        for entity in delta.delta.new_entities:
            self._graph.add_entity(entity)
    
    async def _run_llm_analysis(
        self,
        intent: Intent,
        state: State,
        delta: DeltaAnalysisResult,
    ) -> tuple[ParallelAnalysisResult, list[SecurityFinding]]:
        """Run LLM-based security analysis."""
        if not self.llm_analyzer:
            return ParallelAnalysisResult(), []
        
        # Prepare data for LLM
        intent_dict = {
            "title": intent.title,
            "summary": intent.summary,
            "features": intent.features,
            "api_changes": intent.api_changes,
            "auth_requirements": intent.auth_requirements,
            "data_sensitivity": intent.data_sensitivity,
            "external_integrations": intent.external_integrations,
        }
        
        state_dict = {
            "api_endpoints": state.api_endpoints[:20],  # Limit for context
            "data_models": state.data_models[:20],
            "auth_patterns": state.auth_patterns,
            "existing_controls": state.existing_controls,
        }
        
        delta_dict = {
            "new_endpoints": delta.new_endpoints,
            "modified_endpoints": delta.modified_endpoints,
            "new_data_models": delta.new_data_models,
            "attack_surface_changes": delta.attack_surface_changes,
            "auth_requirement_changes": delta.auth_requirement_changes,
            "introduces_pii": delta.introduces_pii,
            "summary": delta.delta.summary,
        }
        
        # Run parallel LLM analysis
        llm_result = await self.llm_analyzer.security_review(
            intent_dict, 
            state_dict, 
            delta_dict
        )
        
        # Convert LLM findings to SecurityFinding objects
        findings = self._convert_llm_findings(llm_result)
        
        return llm_result, findings
    
    def _convert_llm_findings(
        self, 
        llm_result: ParallelAnalysisResult
    ) -> list[SecurityFinding]:
        """Convert LLM analysis results to SecurityFinding objects."""
        from context_graph.core.models import ThreatCategory
        
        findings: list[SecurityFinding] = []
        
        # Map severity strings to enum
        severity_map = {
            "critical": Severity.CRITICAL,
            "high": Severity.HIGH,
            "medium": Severity.MEDIUM,
            "low": Severity.LOW,
            "info": Severity.INFO,
        }
        
        # Map category strings to ThreatCategory enum
        category_map = {
            # STRIDE categories
            "spoofing": ThreatCategory.SPOOFING,
            "tampering": ThreatCategory.TAMPERING,
            "repudiation": ThreatCategory.REPUDIATION,
            "information disclosure": ThreatCategory.INFO_DISCLOSURE,
            "information_disclosure": ThreatCategory.INFO_DISCLOSURE,
            "denial of service": ThreatCategory.DENIAL_OF_SERVICE,
            "denial_of_service": ThreatCategory.DENIAL_OF_SERVICE,
            "dos": ThreatCategory.DENIAL_OF_SERVICE,
            "elevation of privilege": ThreatCategory.ELEVATION_OF_PRIVILEGE,
            "elevation_of_privilege": ThreatCategory.ELEVATION_OF_PRIVILEGE,
            "privilege escalation": ThreatCategory.ELEVATION_OF_PRIVILEGE,
            # OWASP categories
            "injection": ThreatCategory.INJECTION,
            "a03": ThreatCategory.INJECTION,
            "a03: injection": ThreatCategory.INJECTION,
            "broken authentication": ThreatCategory.BROKEN_AUTH,
            "broken_authentication": ThreatCategory.BROKEN_AUTH,
            "authentication failures": ThreatCategory.BROKEN_AUTH,
            "a07": ThreatCategory.BROKEN_AUTH,
            "a07: authentication failures": ThreatCategory.BROKEN_AUTH,
            "sensitive data exposure": ThreatCategory.SENSITIVE_DATA_EXPOSURE,
            "sensitive_data_exposure": ThreatCategory.SENSITIVE_DATA_EXPOSURE,
            "cryptographic failures": ThreatCategory.SENSITIVE_DATA_EXPOSURE,
            "a02": ThreatCategory.SENSITIVE_DATA_EXPOSURE,
            "a02: cryptographic failures": ThreatCategory.SENSITIVE_DATA_EXPOSURE,
            "broken access control": ThreatCategory.BROKEN_ACCESS_CONTROL,
            "broken_access_control": ThreatCategory.BROKEN_ACCESS_CONTROL,
            "a01": ThreatCategory.BROKEN_ACCESS_CONTROL,
            "a01: broken access control": ThreatCategory.BROKEN_ACCESS_CONTROL,
            "security misconfiguration": ThreatCategory.SECURITY_MISCONFIGURATION,
            "security_misconfiguration": ThreatCategory.SECURITY_MISCONFIGURATION,
            "a05": ThreatCategory.SECURITY_MISCONFIGURATION,
            "a05: security misconfiguration": ThreatCategory.SECURITY_MISCONFIGURATION,
            "insecure deserialization": ThreatCategory.INSECURE_DESERIALIZATION,
            "insecure_deserialization": ThreatCategory.INSECURE_DESERIALIZATION,
            "a08": ThreatCategory.INSECURE_DESERIALIZATION,
            "a08: data integrity failures": ThreatCategory.INSECURE_DESERIALIZATION,
            "insufficient logging": ThreatCategory.INSUFFICIENT_LOGGING,
            "insufficient_logging": ThreatCategory.INSUFFICIENT_LOGGING,
            "logging failures": ThreatCategory.INSUFFICIENT_LOGGING,
            "a09": ThreatCategory.INSUFFICIENT_LOGGING,
            "a09: logging failures": ThreatCategory.INSUFFICIENT_LOGGING,
            # Additional mappings
            "insecure design": ThreatCategory.SECURITY_MISCONFIGURATION,
            "a04": ThreatCategory.SECURITY_MISCONFIGURATION,
            "a04: insecure design": ThreatCategory.SECURITY_MISCONFIGURATION,
            "ssrf": ThreatCategory.INJECTION,
            "a10": ThreatCategory.INJECTION,
            "a10: ssrf": ThreatCategory.INJECTION,
        }
        
        for finding_data in llm_result.merged_findings:
            severity_str = finding_data.get("severity", "medium").lower()
            category_str = finding_data.get("category", "").lower().strip()
            
            # Try to match category
            category = category_map.get(category_str)
            if not category:
                # Try partial matching
                for key, val in category_map.items():
                    if key in category_str or category_str in key:
                        category = val
                        break
                if not category:
                    category = ThreatCategory.INFO_DISCLOSURE  # Default fallback
            
            finding = SecurityFinding(
                id=finding_data.get("id", None) or uuid4(),
                title=finding_data.get("title", "LLM Finding"),
                description=finding_data.get("description", ""),
                severity=severity_map.get(severity_str, Severity.MEDIUM),
                category=category,
                recommendation=finding_data.get("recommendation", ""),
                confidence=finding_data.get("confidence", 0.7),
                source_type="llm",
                source_reference=", ".join(finding_data.get("providers", [])),
            )
            findings.append(finding)
        
        return findings
    
    def _analyze_graph(self) -> list[SecurityFinding]:
        """Analyze context graph for security issues."""
        findings: list[SecurityFinding] = []
        
        # Find unauthenticated paths to sensitive data
        unauth_paths = self._graph.find_unauthenticated_paths()
        for entry, path, sensitive in unauth_paths:
            findings.append(SecurityFinding(
                title=f"Unauthenticated path to {sensitive.name}",
                description=(
                    f"Found a path from {entry.name} to sensitive data {sensitive.name} "
                    "that doesn't require authentication."
                ),
                severity=Severity.HIGH,
                source_type="graph",
                source_reference=f"{entry.id} -> {sensitive.id}",
                recommendation="Add authentication requirement to this path",
            ))
        
        # Find trust boundary crossings
        crossings = self._graph.find_trust_boundary_crossings()
        for rel in crossings[:10]:  # Limit findings
            source = self._graph.get_entity(rel.source_id)
            target = self._graph.get_entity(rel.target_id)
            if source and target:
                findings.append(SecurityFinding(
                    title=f"Trust boundary crossing: {source.name} -> {target.name}",
                    description="Data flows across a trust boundary without explicit validation",
                    severity=Severity.MEDIUM,
                    source_type="graph",
                    source_reference=str(rel.id),
                    recommendation="Add validation at trust boundary crossing",
                ))
        
        # Find high-risk entities
        for entity in self._graph.iter_entities():
            risk_score = self._graph.compute_risk_score(entity.id)
            if risk_score > 70:
                findings.append(SecurityFinding(
                    title=f"High-risk entity: {entity.name}",
                    description=f"Entity has risk score of {risk_score:.0f}/100",
                    severity=Severity.MEDIUM,
                    source_type="graph",
                    source_reference=str(entity.id),
                    recommendation="Review security controls for this entity",
                ))
        
        return findings
    
    def _merge_findings(self, result: ReviewResult) -> list[SecurityFinding]:
        """Merge and deduplicate findings from all sources."""
        # If LLM-only mode and we have LLM findings, use only those
        if self.config.llm_only and result.llm_findings:
            all_findings = result.llm_findings
        else:
            all_findings = (
                result.pattern_findings + 
                result.llm_findings + 
                result.graph_findings
            )
        
        # Filter by minimum severity and confidence
        severity_order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
            Severity.INFO: 4,
        }
        
        min_severity_order = severity_order.get(self.config.min_severity, 3)
        
        filtered = [
            f for f in all_findings
            if severity_order.get(f.severity, 5) <= min_severity_order
            and f.confidence >= self.config.min_confidence
        ]
        
        # Deduplicate by title similarity
        seen_titles: set[str] = set()
        unique_findings: list[SecurityFinding] = []
        
        for finding in filtered:
            title_key = finding.title.lower()[:40]
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_findings.append(finding)
        
        # Sort by severity
        unique_findings.sort(key=lambda f: severity_order.get(f.severity, 5))
        
        return unique_findings
    
    def _generate_summary(self, result: ReviewResult) -> str:
        """Generate executive summary including all dimensions."""
        findings = result.all_findings
        
        critical = sum(1 for f in findings if f.severity == Severity.CRITICAL)
        high = sum(1 for f in findings if f.severity == Severity.HIGH)
        medium = sum(1 for f in findings if f.severity == Severity.MEDIUM)
        low = sum(1 for f in findings if f.severity == Severity.LOW)
        
        # Determine review type based on dimensions
        if len(result.dimensions_analyzed) > 1:
            review_type = "Multi-Dimension Review"
        else:
            review_type = "Security Review"
        
        parts = [
            f"{review_type} completed for: {result.intent.title}",
            "",
            f"**Total Findings:** {len(findings)}",
            f"- Critical: {critical}",
            f"- High: {high}",
            f"- Medium: {medium}",
            f"- Low: {low}",
            "",
        ]
        
        # Add dimension breakdown if multi-dimension
        if len(result.dimensions_analyzed) > 1:
            parts.append("**By Dimension:**")
            if ReviewDimension.SECURITY in result.dimensions_analyzed:
                parts.append(f"- Security (STRIDE/OWASP): {len(result.security_findings)} findings")
            if ReviewDimension.PRIVACY in result.dimensions_analyzed:
                parts.append(f"- Privacy (LINDDUN/GDPR): {len(result.privacy_findings)} findings")
            if ReviewDimension.COMPLIANCE in result.dimensions_analyzed:
                parts.append(f"- Compliance: {len(result.compliance_findings)} findings")
            if ReviewDimension.ENGINEERING in result.dimensions_analyzed:
                parts.append(f"- Engineering (Quality/Testing): {len(result.engineering_findings)} findings")
            if ReviewDimension.ARCHITECTURE in result.dimensions_analyzed:
                parts.append(f"- Architecture (Design/Dependencies): {len(result.architecture_findings)} findings")
            parts.append("")
        
        # Add FP filter stats if any filtering was done
        if result.fp_filter_stats:
            total_original = sum(s.original_count for s in result.fp_filter_stats)
            total_removed = sum(s.total_removed for s in result.fp_filter_stats)
            total_downgraded = sum(s.total_downgraded for s in result.fp_filter_stats)
            if total_removed > 0 or total_downgraded > 0:
                parts.append("**False Positive Filtering:**")
                for stat in result.fp_filter_stats:
                    if stat.total_removed > 0 or stat.total_downgraded > 0:
                        parts.append(
                            f"- {stat.dimension.title()}: {stat.original_count} → "
                            f"{stat.final_count} findings "
                            f"(removed {stat.total_removed}, downgraded {stat.total_downgraded}, "
                            f"{stat.total_iterations} iterations)"
                        )
                parts.append("")
        
        if result.delta_result:
            parts.append(f"**Change Summary:** {result.delta_result.delta.summary}")
            parts.append(f"**Risk Score:** {result.delta_result.delta.risk_score:.0f}/100")
        
        if critical > 0:
            parts.append("")
            parts.append("⚠️ **Critical Issues Require Immediate Attention**")
            for f in findings:
                if f.severity == Severity.CRITICAL:
                    dimension = getattr(f, 'dimension', ReviewDimension.SECURITY)
                    parts.append(f"- [{dimension.value.upper()}] {f.title}")
        
        return "\n".join(parts)
    
    def _compute_risk_rating(self, result: ReviewResult) -> str:
        """Compute overall risk rating."""
        findings = result.all_findings
        
        critical = sum(1 for f in findings if f.severity == Severity.CRITICAL)
        high = sum(1 for f in findings if f.severity == Severity.HIGH)
        
        if critical > 0:
            return "CRITICAL"
        elif high > 2:
            return "HIGH"
        elif high > 0:
            return "MEDIUM"
        elif len(findings) > 5:
            return "MEDIUM"
        elif len(findings) > 0:
            return "LOW"
        else:
            return "MINIMAL"
    
    async def _generate_pm_features(
        self,
        result: ReviewResult,
        intent: Intent,
        state: State,
        features: Any,  # FeatureFlags type
    ) -> None:
        """Generate PM-focused features: PRD changes, quality score, effort estimation."""
        from context_graph.pm import PRDChangeGenerator, PRDQualityScorer, EffortEstimator
        
        # Get all findings
        all_findings = result.all_findings
        
        if not all_findings:
            return
        
        prd_content = intent.raw_content or ""
        
        # Generate PRD changes from findings (if enabled)
        if features.enable_prd_changes:
            change_generator = PRDChangeGenerator()
            
            # Prepare codebase state dict for evidence extraction
            codebase_state = {
                "api_endpoints": state.api_endpoints,
                "data_models": state.data_models,
                "auth_patterns": state.auth_patterns,
                "existing_controls": state.existing_controls,
            }
            
            # Generate predicted questions with PRD changes
            predicted_questions = change_generator.generate_changes(
                findings=all_findings,
                prd_content=prd_content,
                codebase_state=codebase_state,
            )
            
            result.predicted_questions = predicted_questions
        else:
            # Still create empty list for API compatibility
            result.predicted_questions = []
        
        # Calculate PRD quality score (if enabled)
        if features.enable_prd_quality_scoring:
            quality_scorer = PRDQualityScorer()
            predicted_questions = result.predicted_questions if result.predicted_questions else []
            result.prd_quality_score = quality_scorer.calculate_score(
                predicted_questions=predicted_questions,
                prd_content=prd_content,
            )
        
        # Estimate effort (if enabled)
        if features.enable_effort_estimation:
            effort_estimator = EffortEstimator()
            result.effort_estimation = effort_estimator.estimate(
                findings=all_findings,
                codebase_state=state,
            )

