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
    SecurityReview,
    Severity,
    ReviewDimension,
    ComplianceFramework,
)
from context_graph.core.graph import ContextGraph
from context_graph.security.delta_analyzer import DeltaAnalyzer, DeltaAnalysisResult
from context_graph.security.threat_patterns import ThreatPatternMatcher
from context_graph.llm.parallel_analyzer import ParallelLLMAnalyzer, ParallelAnalysisResult


# Type alias for any finding type
Finding = Union[SecurityFinding, PrivacyFinding, ComplianceFinding]


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
    
    # Dimensions that were analyzed
    dimensions_analyzed: list[ReviewDimension] = field(default_factory=list)
    
    # LLM analysis details
    llm_result: ParallelAnalysisResult | None = None
    
    # Multi-dimension LLM results
    privacy_llm_result: ParallelAnalysisResult | None = None
    compliance_llm_result: ParallelAnalysisResult | None = None
    
    # Summary
    executive_summary: str = ""
    risk_rating: str = ""
    reviewed_at: datetime = field(default_factory=datetime.now)
    
    @property
    def all_findings(self) -> list[Finding]:
        """Get all findings from all dimensions."""
        # Prioritize dimension-based findings if available
        if self.security_findings or self.privacy_findings or self.compliance_findings:
            all_findings: list[Finding] = []
            all_findings.extend(self.security_findings)
            all_findings.extend(self.privacy_findings)
            all_findings.extend(self.compliance_findings)
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
    
    def __init__(self, config: ReviewConfig | None = None) -> None:
        self.config = config or ReviewConfig()
        self.delta_analyzer = DeltaAnalyzer()
        self.pattern_matcher = ThreatPatternMatcher()
        self._llm_analyzer: ParallelLLMAnalyzer | None = None
        self._graph = ContextGraph()
        
        # Multi-dimension analyzers (lazy init)
        self._privacy_matcher = None
        self._compliance_matcher = None
    
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
        
        # Step 5: Merge findings (legacy support)
        result.merged_findings = self._merge_findings(result)
        
        # Step 6: Generate summary
        result.executive_summary = self._generate_summary(result)
        result.risk_rating = self._compute_risk_rating(result)
        
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

