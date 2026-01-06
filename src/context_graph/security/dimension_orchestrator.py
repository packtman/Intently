"""
Dimension Orchestrator - Orchestrates parallel review across Security, Privacy, and Compliance.

Runs all three review dimensions concurrently and aggregates results.
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
    ReviewDimension,
    ComplianceFramework,
    Severity,
)
from context_graph.security.delta_analyzer import DeltaAnalyzer, DeltaAnalysisResult
from context_graph.security.threat_patterns import ThreatPatternMatcher
from context_graph.security.privacy_analyzer import PrivacyPatternMatcher
from context_graph.security.compliance_analyzer import CompliancePatternMatcher
from context_graph.llm.parallel_analyzer import ParallelLLMAnalyzer, ParallelAnalysisResult


logger = logging.getLogger(__name__)


# Type alias for any finding type
Finding = Union[SecurityFinding, PrivacyFinding, ComplianceFinding]


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
        }
        
        if self.security_result:
            result[ReviewDimension.SECURITY] = self.security_result.findings
        if self.privacy_result:
            result[ReviewDimension.PRIVACY] = self.privacy_result.findings
        if self.compliance_result:
            result[ReviewDimension.COMPLIANCE] = self.compliance_result.findings
        
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
        
        # LLM analyzer (lazy init)
        self._llm_analyzer: ParallelLLMAnalyzer | None = None
    
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

