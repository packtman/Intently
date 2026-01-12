"""
Dimension Orchestrator - Orchestrates parallel review across all dimensions.

Runs Security, Privacy, Compliance, Engineering, and Architecture dimensions
concurrently and aggregates results.
"""

from __future__ import annotations

import asyncio
import logging
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
    ReviewDimension,
    ComplianceFramework,
    Severity,
)
from context_graph.security.delta_analyzer import DeltaAnalyzer, DeltaAnalysisResult
from context_graph.security.threat_patterns import ThreatPatternMatcher
from context_graph.security.privacy_analyzer import PrivacyPatternMatcher
from context_graph.security.compliance_analyzer import CompliancePatternMatcher
from context_graph.security.engineering_patterns import EngineeringPatternMatcher
from context_graph.security.architecture_patterns import ArchitecturePatternMatcher
from context_graph.llm.parallel_analyzer import ParallelLLMAnalyzer, ParallelAnalysisResult


logger = logging.getLogger(__name__)


# Type alias for any finding type
Finding = Union[SecurityFinding, PrivacyFinding, ComplianceFinding, EngineeringFinding, ArchitectureFinding]


@dataclass
class DimensionConfig:
    """Configuration for dimension-based review."""
    
    # Which dimensions to run
    dimensions: list[ReviewDimension] = field(default_factory=lambda: [
        ReviewDimension.SECURITY,
        ReviewDimension.PRIVACY,
        ReviewDimension.COMPLIANCE,
    ])
    
    # LLM settings
    use_llm: bool = True
    use_pattern_matching: bool = True
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    
    # Compliance-specific
    compliance_frameworks: list[ComplianceFramework] = field(default_factory=lambda: [
        ComplianceFramework.SOC2,
        ComplianceFramework.HIPAA,
        ComplianceFramework.PCI_DSS,
    ])
    
    # Thresholds
    min_severity: Severity = Severity.LOW
    min_confidence: float = 0.5


@dataclass
class DimensionResult:
    """Result from a single dimension analysis."""
    
    dimension: ReviewDimension
    findings: list[Finding] = field(default_factory=list)
    llm_result: ParallelAnalysisResult | None = None
    pattern_findings: list[Finding] = field(default_factory=list)
    
    # Metadata
    success: bool = True
    error_message: str = ""
    duration_ms: float = 0.0
    
    @property
    def finding_count(self) -> int:
        return len(self.findings)
    
    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.CRITICAL)
    
    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.HIGH)


@dataclass
class OrchestratorResult:
    """Combined result from all dimension analyses."""
    
    id: UUID = field(default_factory=uuid4)
    
    # Results by dimension
    security_result: DimensionResult | None = None
    privacy_result: DimensionResult | None = None
    compliance_result: DimensionResult | None = None
    engineering_result: DimensionResult | None = None
    architecture_result: DimensionResult | None = None
    
    # Delta analysis (shared across dimensions)
    delta_result: DeltaAnalysisResult | None = None
    
    # Aggregated findings
    all_findings: list[Finding] = field(default_factory=list)
    
    # Summary
    executive_summary: str = ""
    overall_risk_rating: str = ""
    
    # Metadata
    dimensions_run: list[ReviewDimension] = field(default_factory=list)
    total_duration_ms: float = 0.0
    completed_at: datetime = field(default_factory=datetime.now)
    
    # Engineering/Architecture metrics (optional)
    engineering_metrics: dict[str, Any] = field(default_factory=dict)
    architecture_metrics: dict[str, Any] = field(default_factory=dict)
    
    @property
    def total_findings(self) -> int:
        return len(self.all_findings)
    
    @property
    def findings_by_dimension(self) -> dict[ReviewDimension, list[Finding]]:
        """Group findings by dimension."""
        result: dict[ReviewDimension, list[Finding]] = {
            ReviewDimension.SECURITY: [],
            ReviewDimension.PRIVACY: [],
            ReviewDimension.COMPLIANCE: [],
            ReviewDimension.ENGINEERING: [],
            ReviewDimension.ARCHITECTURE: [],
        }
        
        if self.security_result:
            result[ReviewDimension.SECURITY] = self.security_result.findings
        if self.privacy_result:
            result[ReviewDimension.PRIVACY] = self.privacy_result.findings
        if self.compliance_result:
            result[ReviewDimension.COMPLIANCE] = self.compliance_result.findings
        if self.engineering_result:
            result[ReviewDimension.ENGINEERING] = self.engineering_result.findings
        if self.architecture_result:
            result[ReviewDimension.ARCHITECTURE] = self.architecture_result.findings
        
        return result
    
    @property
    def findings_by_severity(self) -> dict[Severity, list[Finding]]:
        """Group findings by severity."""
        result: dict[Severity, list[Finding]] = {
            Severity.CRITICAL: [],
            Severity.HIGH: [],
            Severity.MEDIUM: [],
            Severity.LOW: [],
            Severity.INFO: [],
        }
        
        for finding in self.all_findings:
            if finding.severity in result:
                result[finding.severity].append(finding)
        
        return result


class DimensionOrchestrator:
    """
    Orchestrates parallel security, privacy, and compliance reviews.
    
    Workflow:
    1. Compute delta (shared)
    2. Run pattern matching for each dimension (parallel)
    3. Run LLM analysis for each dimension (parallel)
    4. Merge and deduplicate findings
    5. Generate aggregated summary
    """
    
    def __init__(self, config: DimensionConfig | None = None) -> None:
        self.config = config or DimensionConfig()
        
        # Initialize analyzers
        self.delta_analyzer = DeltaAnalyzer()
        self.security_matcher = ThreatPatternMatcher()
        self.privacy_matcher = PrivacyPatternMatcher()
        self.compliance_matcher = CompliancePatternMatcher(
            frameworks=self.config.compliance_frameworks
        )
        self.engineering_matcher = EngineeringPatternMatcher()
        self.architecture_matcher = ArchitecturePatternMatcher()
        
        # LLM analyzer (lazy init)
        self._llm_analyzer: ParallelLLMAnalyzer | None = None
        
        # Metrics from analyzers (populated during review)
        self._engineering_metrics: dict[str, Any] = {}
        self._architecture_metrics: dict[str, Any] = {}
    
    @property
    def llm_analyzer(self) -> ParallelLLMAnalyzer | None:
        """Lazy-initialize LLM analyzer."""
        if self._llm_analyzer is None and self.config.use_llm:
            if self.config.openai_api_key or self.config.anthropic_api_key:
                self._llm_analyzer = ParallelLLMAnalyzer(
                    openai_api_key=self.config.openai_api_key,
                    anthropic_api_key=self.config.anthropic_api_key,
                )
        return self._llm_analyzer
    
    async def review(
        self,
        intent: Intent,
        state: State,
    ) -> OrchestratorResult:
        """
        Perform parallel multi-dimension review.
        
        Args:
            intent: Extracted intent from PRD
            state: Current codebase state
            
        Returns:
            OrchestratorResult with findings from all dimensions
        """
        import time
        start_time = time.time()
        
        result = OrchestratorResult(
            dimensions_run=self.config.dimensions.copy(),
        )
        
        # Step 1: Compute delta (shared across all dimensions)
        result.delta_result = self.delta_analyzer.analyze(intent, state)
        
        # Step 2: Prepare data for LLM
        intent_dict = self._prepare_intent_dict(intent)
        state_dict = self._prepare_state_dict(state)
        delta_dict = self._prepare_delta_dict(result.delta_result)
        
        # Step 3: Run dimension analyses in parallel
        tasks = []
        task_dimensions = []
        
        if ReviewDimension.SECURITY in self.config.dimensions:
            tasks.append(self._run_security_analysis(
                intent_dict, state_dict, delta_dict, result.delta_result
            ))
            task_dimensions.append(ReviewDimension.SECURITY)
        
        if ReviewDimension.PRIVACY in self.config.dimensions:
            tasks.append(self._run_privacy_analysis(
                intent_dict, state_dict, delta_dict, result.delta_result
            ))
            task_dimensions.append(ReviewDimension.PRIVACY)
        
        if ReviewDimension.COMPLIANCE in self.config.dimensions:
            tasks.append(self._run_compliance_analysis(
                intent_dict, state_dict, delta_dict, result.delta_result
            ))
            task_dimensions.append(ReviewDimension.COMPLIANCE)
        
        if ReviewDimension.ENGINEERING in self.config.dimensions:
            tasks.append(self._run_engineering_analysis(
                intent_dict, state_dict, delta_dict, result.delta_result, state
            ))
            task_dimensions.append(ReviewDimension.ENGINEERING)
        
        if ReviewDimension.ARCHITECTURE in self.config.dimensions:
            tasks.append(self._run_architecture_analysis(
                intent_dict, state_dict, delta_dict, result.delta_result, state, intent
            ))
            task_dimensions.append(ReviewDimension.ARCHITECTURE)
        
        # Execute all dimensions in parallel
        if tasks:
            dimension_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, dim_result in enumerate(dimension_results):
                dimension = task_dimensions[i]
                
                if isinstance(dim_result, Exception):
                    logger.error(f"{dimension.value} analysis failed: {dim_result}")
                    error_result = DimensionResult(
                        dimension=dimension,
                        success=False,
                        error_message=str(dim_result),
                    )
                    self._set_dimension_result(result, dimension, error_result)
                elif isinstance(dim_result, DimensionResult):
                    self._set_dimension_result(result, dimension, dim_result)
        
        # Step 4: Aggregate all findings
        result.all_findings = self._aggregate_findings(result)
        
        # Step 5: Filter by thresholds
        result.all_findings = self._filter_findings(result.all_findings)
        
        # Step 6: Generate summary
        result.executive_summary = self._generate_summary(result, intent)
        result.overall_risk_rating = self._compute_risk_rating(result)
        
        # Store metrics for frontend
        result.engineering_metrics = self._engineering_metrics
        result.architecture_metrics = self._architecture_metrics
        
        result.total_duration_ms = (time.time() - start_time) * 1000
        result.completed_at = datetime.now()
        
        return result
    
    def _set_dimension_result(
        self,
        result: OrchestratorResult,
        dimension: ReviewDimension,
        dim_result: DimensionResult,
    ) -> None:
        """Set the dimension result on the orchestrator result."""
        if dimension == ReviewDimension.SECURITY:
            result.security_result = dim_result
        elif dimension == ReviewDimension.PRIVACY:
            result.privacy_result = dim_result
        elif dimension == ReviewDimension.COMPLIANCE:
            result.compliance_result = dim_result
        elif dimension == ReviewDimension.ENGINEERING:
            result.engineering_result = dim_result
        elif dimension == ReviewDimension.ARCHITECTURE:
            result.architecture_result = dim_result
    
    async def _run_security_analysis(
        self,
        intent_dict: dict[str, Any],
        state_dict: dict[str, Any],
        delta_dict: dict[str, Any],
        delta_result: DeltaAnalysisResult,
    ) -> DimensionResult:
        """Run security analysis (STRIDE + OWASP)."""
        import time
        start_time = time.time()
        
        result = DimensionResult(dimension=ReviewDimension.SECURITY)
        
        try:
            # Pattern matching
            if self.config.use_pattern_matching:
                pattern_findings = self.security_matcher.match(delta_result)
                result.pattern_findings = pattern_findings
            
            # LLM analysis
            if self.config.use_llm and self.llm_analyzer:
                llm_result = await self.llm_analyzer.security_review(
                    intent_dict, state_dict, delta_dict
                )
                result.llm_result = llm_result
                
                # Convert LLM findings to SecurityFinding objects
                llm_findings = self._convert_llm_security_findings(llm_result)
                
                # Merge pattern and LLM findings
                result.findings = self._merge_security_findings(
                    result.pattern_findings,
                    llm_findings,
                )
            else:
                result.findings = list(result.pattern_findings)
            
            result.success = True
            
        except Exception as e:
            logger.error(f"Security analysis error: {e}")
            result.success = False
            result.error_message = str(e)
        
        result.duration_ms = (time.time() - start_time) * 1000
        return result
    
    async def _run_privacy_analysis(
        self,
        intent_dict: dict[str, Any],
        state_dict: dict[str, Any],
        delta_dict: dict[str, Any],
        delta_result: DeltaAnalysisResult,
    ) -> DimensionResult:
        """Run privacy analysis (LINDDUN + GDPR)."""
        import time
        start_time = time.time()
        
        result = DimensionResult(dimension=ReviewDimension.PRIVACY)
        
        try:
            # Pattern matching
            if self.config.use_pattern_matching:
                pattern_findings = self.privacy_matcher.match(delta_result)
                result.pattern_findings = pattern_findings
            
            # LLM analysis
            if self.config.use_llm and self.llm_analyzer:
                llm_result = await self.llm_analyzer.privacy_review(
                    intent_dict, state_dict, delta_dict
                )
                result.llm_result = llm_result
                
                # Convert LLM findings to PrivacyFinding objects
                llm_findings = self._convert_llm_privacy_findings(llm_result)
                
                # Merge pattern and LLM findings
                result.findings = self._merge_privacy_findings(
                    result.pattern_findings,
                    llm_findings,
                )
            else:
                result.findings = list(result.pattern_findings)
            
            result.success = True
            
        except Exception as e:
            logger.error(f"Privacy analysis error: {e}")
            result.success = False
            result.error_message = str(e)
        
        result.duration_ms = (time.time() - start_time) * 1000
        return result
    
    async def _run_compliance_analysis(
        self,
        intent_dict: dict[str, Any],
        state_dict: dict[str, Any],
        delta_dict: dict[str, Any],
        delta_result: DeltaAnalysisResult,
    ) -> DimensionResult:
        """Run compliance analysis (SOC2, HIPAA, PCI-DSS)."""
        import time
        start_time = time.time()
        
        result = DimensionResult(dimension=ReviewDimension.COMPLIANCE)
        
        try:
            # Pattern matching
            if self.config.use_pattern_matching:
                pattern_findings = self.compliance_matcher.match(delta_result)
                result.pattern_findings = pattern_findings
            
            # LLM analysis
            if self.config.use_llm and self.llm_analyzer:
                frameworks = [f.value for f in self.config.compliance_frameworks]
                llm_result = await self.llm_analyzer.compliance_review(
                    intent_dict, state_dict, delta_dict, frameworks
                )
                result.llm_result = llm_result
                
                # Convert LLM findings to ComplianceFinding objects
                llm_findings = self._convert_llm_compliance_findings(llm_result)
                
                # Merge pattern and LLM findings
                result.findings = self._merge_compliance_findings(
                    result.pattern_findings,
                    llm_findings,
                )
            else:
                result.findings = list(result.pattern_findings)
            
            result.success = True
            
        except Exception as e:
            logger.error(f"Compliance analysis error: {e}")
            result.success = False
            result.error_message = str(e)
        
        result.duration_ms = (time.time() - start_time) * 1000
        return result
    
    async def _run_engineering_analysis(
        self,
        intent_dict: dict[str, Any],
        state_dict: dict[str, Any],
        delta_dict: dict[str, Any],
        delta_result: DeltaAnalysisResult,
        state: State,
    ) -> DimensionResult:
        """Run engineering feasibility and effort analysis.
        
        This analysis focuses on:
        1. Understanding current codebase context (complexity, patterns, debt)
        2. Assessing PRD feature feasibility based on existing code
        3. Providing detailed time estimates based on actual metrics
        """
        import time
        start_time = time.time()
        
        result = DimensionResult(dimension=ReviewDimension.ENGINEERING)
        
        try:
            # Build comprehensive engineering metrics from state
            engineering_metrics = self._build_engineering_metrics(state)
            self._engineering_metrics = engineering_metrics
            logger.info(f"Built engineering metrics: {engineering_metrics.get('source_files', 0)} files, "
                       f"{engineering_metrics.get('total_lines', 0)} lines")
            
            # Pattern matching for quick heuristic findings
            if self.config.use_pattern_matching:
                pattern_findings = self.engineering_matcher.match(
                    delta_result,
                    state=state,
                    engineering_metrics=engineering_metrics,
                )
                result.pattern_findings = pattern_findings
                logger.info(f"Pattern matching found {len(pattern_findings)} engineering findings")
            
            # LLM analysis for detailed feasibility and time estimation
            if self.config.use_llm and self.llm_analyzer:
                logger.info("Running LLM engineering feasibility analysis")
                try:
                    llm_result = await self.llm_analyzer.engineering_review(
                        intent_dict,
                        state_dict,
                        delta_dict,
                        engineering_metrics,  # Pass metrics to LLM for context-aware analysis
                    )
                    result.llm_result = llm_result
                    logger.info(f"LLM returned {len(llm_result.merged_findings)} engineering findings")
                    
                    # Convert LLM findings to EngineeringFinding objects
                    llm_findings = self._convert_llm_engineering_findings(llm_result)
                    
                    # Combine pattern and LLM findings, preferring LLM when available
                    if llm_findings:
                        result.findings = llm_findings
                    else:
                        result.findings = list(result.pattern_findings)
                except Exception as e:
                    logger.error(f"LLM engineering analysis failed: {e}", exc_info=True)
                    result.findings = list(result.pattern_findings)
            else:
                result.findings = list(result.pattern_findings)
            
            result.success = True
            
        except Exception as e:
            logger.error(f"Engineering analysis error: {e}", exc_info=True)
            result.success = False
            result.error_message = str(e)
        
        result.duration_ms = (time.time() - start_time) * 1000
        return result
    
    async def _run_architecture_analysis(
        self,
        intent_dict: dict[str, Any],
        state_dict: dict[str, Any],
        delta_dict: dict[str, Any],
        delta_result: DeltaAnalysisResult,
        state: State,
        intent: Intent,
    ) -> DimensionResult:
        """Run architecture analysis (API design, dependencies, resilience)."""
        import time
        start_time = time.time()
        
        result = DimensionResult(dimension=ReviewDimension.ARCHITECTURE)
        
        try:
            # Build architecture metrics from state
            architecture_metrics = self._build_architecture_metrics(state)
            self._architecture_metrics = architecture_metrics
            
            # Pattern matching
            if self.config.use_pattern_matching:
                pattern_findings = self.architecture_matcher.match(
                    delta_result,
                    state=state,
                    intent=intent,
                    architecture_metrics=architecture_metrics,
                )
                result.pattern_findings = pattern_findings
            
            # LLM analysis for architecture (optional enhancement)
            if self.config.use_llm and self.llm_analyzer:
                # Can add LLM-based architecture analysis here if needed
                pass
            
            result.findings = list(result.pattern_findings)
            result.success = True
            
        except Exception as e:
            logger.error(f"Architecture analysis error: {e}")
            result.success = False
            result.error_message = str(e)
        
        result.duration_ms = (time.time() - start_time) * 1000
        return result
    
    def _build_engineering_metrics(self, state: State) -> dict[str, Any]:
        """Build comprehensive engineering metrics from codebase state.
        
        These metrics provide the LLM with detailed context about the current codebase
        to make accurate feasibility assessments and time estimates.
        """
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
        total_complexity = 0
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
                total_complexity += complexity_score
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
        metrics["high_complexity_files"] = high_complexity_files[:10]  # Top 10
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
        
        # Codebase size categorization (for LLM context)
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
    
    def _build_architecture_metrics(self, state: State) -> dict[str, Any]:
        """Build architecture metrics from codebase state."""
        metrics: dict[str, Any] = {
            "api_contracts": 0,
            "services_identified": 0,
            "external_dependencies": 0,
            "internal_dependencies": 0,
            "has_dependency_lock": "dependency_lock" in state.existing_controls,
            "adrs_found": 0,
            "architectural_patterns": [],
            "discovered_services": [],
        }
        
        # Count from entities
        for entity in state.entities:
            props = entity.properties or {}
            
            # API contracts
            if props.get("contract_type") in ["openapi", "asyncapi", "graphql"]:
                metrics["api_contracts"] += 1
            
            # Services
            if entity.entity_type.value == "service":
                metrics["services_identified"] += 1
                if entity.name:
                    metrics["discovered_services"].append(entity.name)
            
            # ADRs
            if props.get("doc_type") == "adr":
                metrics["adrs_found"] += 1
            
            # Dependencies
            if props.get("dependency_count"):
                metrics["external_dependencies"] += props["dependency_count"]
            
            # Architectural patterns
            if props.get("patterns"):
                for p in props["patterns"]:
                    if p not in metrics["architectural_patterns"]:
                        metrics["architectural_patterns"].append(p)
        
        return metrics
    
    def _prepare_intent_dict(self, intent: Intent) -> dict[str, Any]:
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
    
    def _prepare_state_dict(self, state: State) -> dict[str, Any]:
        """Prepare state data for LLM."""
        return {
            "api_endpoints": state.api_endpoints[:20],
            "data_models": state.data_models[:20],
            "auth_patterns": state.auth_patterns,
            "existing_controls": state.existing_controls,
        }
    
    def _prepare_delta_dict(self, delta: DeltaAnalysisResult) -> dict[str, Any]:
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
    
    def _convert_llm_security_findings(
        self,
        llm_result: ParallelAnalysisResult,
    ) -> list[SecurityFinding]:
        """Convert LLM results to SecurityFinding objects."""
        from context_graph.core.models import ThreatCategory
        
        findings: list[SecurityFinding] = []
        
        severity_map = {
            "critical": Severity.CRITICAL,
            "high": Severity.HIGH,
            "medium": Severity.MEDIUM,
            "low": Severity.LOW,
            "info": Severity.INFO,
        }
        
        for finding_data in llm_result.merged_findings:
            severity_str = finding_data.get("severity", "medium").lower()
            
            finding = SecurityFinding(
                id=uuid4(),
                title=finding_data.get("title", "Security Finding"),
                description=finding_data.get("description", ""),
                severity=severity_map.get(severity_str, Severity.MEDIUM),
                category=ThreatCategory.INFO_DISCLOSURE,  # Default
                dimension=ReviewDimension.SECURITY,
                recommendation=finding_data.get("recommendation", ""),
                confidence=finding_data.get("confidence", 0.7),
                source_type="llm",
                source_reference=", ".join(finding_data.get("providers", [])),
            )
            findings.append(finding)
        
        return findings
    
    def _convert_llm_privacy_findings(
        self,
        llm_result: ParallelAnalysisResult,
    ) -> list[PrivacyFinding]:
        """Convert LLM results to PrivacyFinding objects."""
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
                category=PrivacyCategory.DATA_DISCLOSURE,  # Default
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
        """Convert LLM results to ComplianceFinding objects."""
        from context_graph.core.models import ComplianceCategory, ComplianceFramework
        
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
                category=ComplianceCategory.REGULATORY_VIOLATION,  # Default
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
        """Convert LLM results to EngineeringFinding objects.
        
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
            "feasibility_blocker": EngineeringCategory.HIGH_COMPLEXITY,
            "high_complexity": EngineeringCategory.HIGH_COMPLEXITY,
            "missing_foundation": EngineeringCategory.MISSING_TESTS,
            "tech_debt_impact": EngineeringCategory.TECH_DEBT,
            "test_gap": EngineeringCategory.MISSING_TESTS,
            "integration_risk": EngineeringCategory.TIGHT_COUPLING,
            "dependency_issue": EngineeringCategory.TIGHT_COUPLING,
            "skill_gap": EngineeringCategory.MISSING_DOCS,
            "timeline_risk": EngineeringCategory.HIGH_COMPLEXITY,
            "deep_nesting": EngineeringCategory.DEEP_NESTING,
            "long_functions": EngineeringCategory.LONG_FUNCTIONS,
            "missing_tests": EngineeringCategory.MISSING_TESTS,
            "missing_docs": EngineeringCategory.MISSING_DOCS,
            "missing_error_handling": EngineeringCategory.MISSING_ERROR_HANDLING,
            "missing_logging": EngineeringCategory.MISSING_LOGGING,
            "missing_metrics": EngineeringCategory.MISSING_METRICS,
            "tech_debt": EngineeringCategory.TECH_DEBT,
            "code_duplication": EngineeringCategory.CODE_DUPLICATION,
            "poor_naming": EngineeringCategory.POOR_NAMING,
            "magic_numbers": EngineeringCategory.MAGIC_NUMBERS,
            "missing_type_hints": EngineeringCategory.MISSING_TYPE_HINTS,
            "missing_validation": EngineeringCategory.MISSING_VALIDATION,
            "tight_coupling": EngineeringCategory.TIGHT_COUPLING,
            "missing_ci_cd": EngineeringCategory.MISSING_CI_CD,
        }
        
        for finding_data in llm_result.merged_findings:
            severity_str = finding_data.get("severity", "medium").lower()
            category_str = finding_data.get("category", "high_complexity").lower()
            
            finding = EngineeringFinding(
                id=uuid4(),
                title=finding_data.get("title", "Engineering Finding"),
                description=finding_data.get("description", ""),
                severity=severity_map.get(severity_str, Severity.MEDIUM),
                category=category_map.get(category_str, EngineeringCategory.HIGH_COMPLEXITY),
                dimension=ReviewDimension.ENGINEERING,
                estimated_effort=finding_data.get("estimated_effort", "medium"),
                estimated_days=finding_data.get("estimated_days", finding_data.get("impact_on_timeline", "")),
                affected_files=finding_data.get("affected_files", []),
                affected_functions=finding_data.get("affected_functions", []),
                recommendation=finding_data.get("recommendation", ""),
                confidence=finding_data.get("confidence", 0.7),
                source_type="llm",
                source_reference=", ".join(finding_data.get("providers", [])),
            )
            findings.append(finding)
        
        # Also extract top-level feasibility and time estimate info if available
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
    
    def _merge_security_findings(
        self,
        pattern_findings: list[Finding],
        llm_findings: list[SecurityFinding],
    ) -> list[Finding]:
        """Merge and deduplicate security findings."""
        all_findings = list(pattern_findings) + llm_findings
        return self._deduplicate_findings(all_findings)
    
    def _merge_privacy_findings(
        self,
        pattern_findings: list[Finding],
        llm_findings: list[PrivacyFinding],
    ) -> list[Finding]:
        """Merge and deduplicate privacy findings."""
        all_findings = list(pattern_findings) + llm_findings
        return self._deduplicate_findings(all_findings)
    
    def _merge_compliance_findings(
        self,
        pattern_findings: list[Finding],
        llm_findings: list[ComplianceFinding],
    ) -> list[Finding]:
        """Merge and deduplicate compliance findings."""
        all_findings = list(pattern_findings) + llm_findings
        return self._deduplicate_findings(all_findings)
    
    def _deduplicate_findings(self, findings: list[Finding]) -> list[Finding]:
        """Remove duplicate findings based on title similarity."""
        seen_titles: set[str] = set()
        unique_findings: list[Finding] = []
        
        for finding in findings:
            title_key = finding.title.lower()[:40]
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_findings.append(finding)
        
        return unique_findings
    
    def _aggregate_findings(self, result: OrchestratorResult) -> list[Finding]:
        """Aggregate findings from all dimensions."""
        all_findings: list[Finding] = []
        
        if result.security_result:
            all_findings.extend(result.security_result.findings)
        if result.privacy_result:
            all_findings.extend(result.privacy_result.findings)
        if result.compliance_result:
            all_findings.extend(result.compliance_result.findings)
        if result.engineering_result:
            all_findings.extend(result.engineering_result.findings)
        if result.architecture_result:
            all_findings.extend(result.architecture_result.findings)
        
        # Sort by severity
        severity_order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
            Severity.INFO: 4,
        }
        all_findings.sort(key=lambda f: severity_order.get(f.severity, 5))
        
        return all_findings
    
    def _filter_findings(self, findings: list[Finding]) -> list[Finding]:
        """Filter findings by severity and confidence thresholds."""
        severity_order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
            Severity.INFO: 4,
        }
        
        min_severity_order = severity_order.get(self.config.min_severity, 3)
        
        return [
            f for f in findings
            if severity_order.get(f.severity, 5) <= min_severity_order
            and f.confidence >= self.config.min_confidence
        ]
    
    def _generate_summary(
        self,
        result: OrchestratorResult,
        intent: Intent,
    ) -> str:
        """Generate executive summary across all dimensions."""
        findings = result.all_findings
        
        # Count by severity
        critical = sum(1 for f in findings if f.severity == Severity.CRITICAL)
        high = sum(1 for f in findings if f.severity == Severity.HIGH)
        medium = sum(1 for f in findings if f.severity == Severity.MEDIUM)
        low = sum(1 for f in findings if f.severity == Severity.LOW)
        
        # Count by dimension
        security_count = len(result.security_result.findings) if result.security_result else 0
        privacy_count = len(result.privacy_result.findings) if result.privacy_result else 0
        compliance_count = len(result.compliance_result.findings) if result.compliance_result else 0
        engineering_count = len(result.engineering_result.findings) if result.engineering_result else 0
        architecture_count = len(result.architecture_result.findings) if result.architecture_result else 0
        
        parts = [
            f"# Multi-Dimension Review: {intent.title}",
            "",
            "## Summary",
            "",
            f"**Total Findings:** {len(findings)}",
            f"- Critical: {critical}",
            f"- High: {high}",
            f"- Medium: {medium}",
            f"- Low: {low}",
            "",
            "## By Dimension",
            "",
            f"- **Security (STRIDE/OWASP):** {security_count} findings",
            f"- **Privacy (LINDDUN/GDPR):** {privacy_count} findings",
            f"- **Compliance (SOC2/HIPAA/PCI-DSS):** {compliance_count} findings",
            f"- **Engineering (Quality/Testing):** {engineering_count} findings",
            f"- **Architecture (Design/Dependencies):** {architecture_count} findings",
            "",
        ]
        
        if result.delta_result:
            parts.extend([
                f"**Change Summary:** {result.delta_result.delta.summary}",
                f"**Risk Score:** {result.delta_result.delta.risk_score:.0f}/100",
                "",
            ])
        
        if critical > 0:
            parts.append("## Critical Issues Require Immediate Attention")
            parts.append("")
            for f in findings:
                if f.severity == Severity.CRITICAL:
                    dimension = getattr(f, 'dimension', ReviewDimension.SECURITY)
                    parts.append(f"- [{dimension.value.upper()}] {f.title}")
            parts.append("")
        
        return "\n".join(parts)
    
    def _compute_risk_rating(self, result: OrchestratorResult) -> str:
        """Compute overall risk rating across all dimensions."""
        findings = result.all_findings
        
        critical = sum(1 for f in findings if f.severity == Severity.CRITICAL)
        high = sum(1 for f in findings if f.severity == Severity.HIGH)
        
        if critical > 0:
            return "CRITICAL"
        elif high > 3:
            return "HIGH"
        elif high > 0:
            return "MEDIUM"
        elif len(findings) > 10:
            return "MEDIUM"
        elif len(findings) > 0:
            return "LOW"
        else:
            return "MINIMAL"

