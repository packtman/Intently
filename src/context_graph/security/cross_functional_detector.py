"""
Cross-Functional Detector - Identifies findings that span multiple review dimensions.

This module analyzes findings across security, privacy, compliance, engineering,
and architecture dimensions to identify cross-cutting concerns that require
coordination across teams.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Union
from uuid import UUID, uuid4

from context_graph.core.models import (
    SecurityFinding,
    PrivacyFinding,
    ComplianceFinding,
    EngineeringFinding,
    ArchitectureFinding,
    ReviewDimension,
    Severity,
)


# Type alias for any finding type
Finding = Union[SecurityFinding, PrivacyFinding, ComplianceFinding, EngineeringFinding, ArchitectureFinding]


@dataclass
class CrossFunctionalConcern:
    """A concern that spans multiple review dimensions."""
    
    id: UUID = field(default_factory=uuid4)
    title: str = ""
    description: str = ""
    
    # Dimensions involved
    dimensions: list[ReviewDimension] = field(default_factory=list)
    
    # Related findings from each dimension
    related_findings: list[Finding] = field(default_factory=list)
    
    # Impact assessment
    severity: Severity = Severity.MEDIUM
    impact_score: float = 0.0
    
    # Coordination requirements
    teams_involved: list[str] = field(default_factory=list)
    requires_architecture_review: bool = False
    requires_security_review: bool = False
    requires_compliance_review: bool = False
    
    # Recommendations
    recommendations: list[str] = field(default_factory=list)
    coordination_notes: str = ""
    
    @property
    def dimension_count(self) -> int:
        """Number of dimensions involved."""
        return len(self.dimensions)
    
    @property
    def is_critical_path(self) -> bool:
        """Check if this concern is on the critical path."""
        return (
            self.severity in (Severity.CRITICAL, Severity.HIGH) and
            self.dimension_count >= 3
        )


@dataclass
class CrossFunctionalAnalysisResult:
    """Result of cross-functional analysis."""
    
    concerns: list[CrossFunctionalConcern] = field(default_factory=list)
    
    # Statistics
    total_findings_analyzed: int = 0
    cross_functional_findings: int = 0
    dimensions_with_overlap: list[tuple[ReviewDimension, ReviewDimension]] = field(default_factory=list)
    
    # Recommendations
    coordination_recommendations: list[str] = field(default_factory=list)
    priority_concerns: list[CrossFunctionalConcern] = field(default_factory=list)
    
    @property
    def has_critical_concerns(self) -> bool:
        """Check if there are critical cross-functional concerns."""
        return any(c.severity == Severity.CRITICAL for c in self.concerns)


class CrossFunctionalDetector:
    """
    Detects cross-functional concerns across review dimensions.
    
    This detector analyzes findings from multiple dimensions to identify:
    1. Overlapping concerns (same issue flagged by multiple dimensions)
    2. Cascading impacts (finding in one dimension affects others)
    3. Coordination requirements (changes needing multiple team involvement)
    4. Integration risks (architectural changes with security implications)
    """
    
    def __init__(self) -> None:
        # Patterns for detecting cross-functional concerns
        self._overlap_patterns = self._build_overlap_patterns()
        self._cascade_patterns = self._build_cascade_patterns()
    
    def analyze(
        self,
        security_findings: list[SecurityFinding],
        privacy_findings: list[PrivacyFinding],
        compliance_findings: list[ComplianceFinding],
        engineering_findings: list[EngineeringFinding],
        architecture_findings: list[ArchitectureFinding],
    ) -> CrossFunctionalAnalysisResult:
        """
        Analyze findings across all dimensions for cross-functional concerns.
        
        Args:
            security_findings: Findings from security analysis
            privacy_findings: Findings from privacy analysis
            compliance_findings: Findings from compliance analysis
            engineering_findings: Findings from engineering analysis
            architecture_findings: Findings from architecture analysis
            
        Returns:
            CrossFunctionalAnalysisResult with identified concerns
        """
        result = CrossFunctionalAnalysisResult()
        
        # Count total findings
        all_findings: list[Finding] = []
        all_findings.extend(security_findings)
        all_findings.extend(privacy_findings)
        all_findings.extend(compliance_findings)
        all_findings.extend(engineering_findings)
        all_findings.extend(architecture_findings)
        
        result.total_findings_analyzed = len(all_findings)
        
        if not all_findings:
            return result
        
        # Detect overlapping concerns
        overlaps = self._detect_overlaps(
            security_findings,
            privacy_findings,
            compliance_findings,
            engineering_findings,
            architecture_findings,
        )
        result.concerns.extend(overlaps)
        
        # Detect cascading impacts
        cascades = self._detect_cascading_impacts(
            security_findings,
            privacy_findings,
            compliance_findings,
            engineering_findings,
            architecture_findings,
        )
        result.concerns.extend(cascades)
        
        # Detect coordination requirements
        coordination = self._detect_coordination_requirements(
            security_findings,
            privacy_findings,
            compliance_findings,
            engineering_findings,
            architecture_findings,
        )
        result.concerns.extend(coordination)
        
        # Calculate statistics
        result.cross_functional_findings = sum(
            len(c.related_findings) for c in result.concerns
        )
        
        # Identify dimension overlaps
        dimension_pairs: set[tuple[ReviewDimension, ReviewDimension]] = set()
        for concern in result.concerns:
            dims = sorted(concern.dimensions, key=lambda d: d.value)
            for i in range(len(dims)):
                for j in range(i + 1, len(dims)):
                    dimension_pairs.add((dims[i], dims[j]))
        result.dimensions_with_overlap = list(dimension_pairs)
        
        # Identify priority concerns
        result.priority_concerns = [
            c for c in result.concerns
            if c.is_critical_path or c.severity in (Severity.CRITICAL, Severity.HIGH)
        ]
        
        # Generate coordination recommendations
        result.coordination_recommendations = self._generate_recommendations(result)
        
        return result
    
    def _detect_overlaps(
        self,
        security_findings: list[SecurityFinding],
        privacy_findings: list[PrivacyFinding],
        compliance_findings: list[ComplianceFinding],
        engineering_findings: list[EngineeringFinding],
        architecture_findings: list[ArchitectureFinding],
    ) -> list[CrossFunctionalConcern]:
        """Detect findings that overlap across dimensions."""
        concerns: list[CrossFunctionalConcern] = []
        
        # Check security + privacy overlap (common: data handling issues)
        for sec_finding in security_findings:
            sec_title_lower = sec_finding.title.lower()
            
            for priv_finding in privacy_findings:
                priv_title_lower = priv_finding.title.lower()
                
                # Check for data-related overlap
                if self._titles_overlap(sec_title_lower, priv_title_lower, ["data", "pii", "sensitive", "encryption"]):
                    concerns.append(CrossFunctionalConcern(
                        title=f"Data Protection: {sec_finding.title}",
                        description=(
                            f"This concern spans both security and privacy dimensions. "
                            f"Security: {sec_finding.description[:100]}... "
                            f"Privacy: {priv_finding.description[:100]}..."
                        ),
                        dimensions=[ReviewDimension.SECURITY, ReviewDimension.PRIVACY],
                        related_findings=[sec_finding, priv_finding],
                        severity=max(sec_finding.severity, priv_finding.severity, key=lambda s: self._severity_weight(s)),
                        teams_involved=["Security", "Privacy/Legal"],
                        requires_security_review=True,
                        recommendations=[
                            "Coordinate data protection requirements between security and privacy teams",
                            "Ensure encryption standards meet both security and privacy regulations",
                        ],
                    ))
        
        # Check security + compliance overlap (common: access control, audit)
        for sec_finding in security_findings:
            sec_title_lower = sec_finding.title.lower()
            
            for comp_finding in compliance_findings:
                comp_title_lower = comp_finding.title.lower()
                
                if self._titles_overlap(sec_title_lower, comp_title_lower, ["access", "audit", "logging", "authentication"]):
                    concerns.append(CrossFunctionalConcern(
                        title=f"Compliance & Security: {sec_finding.title}",
                        description=(
                            f"Access control or audit requirement spans security and compliance. "
                            f"Framework: {comp_finding.framework.value if hasattr(comp_finding, 'framework') else 'N/A'}"
                        ),
                        dimensions=[ReviewDimension.SECURITY, ReviewDimension.COMPLIANCE],
                        related_findings=[sec_finding, comp_finding],
                        severity=max(sec_finding.severity, comp_finding.severity, key=lambda s: self._severity_weight(s)),
                        teams_involved=["Security", "Compliance/GRC"],
                        requires_security_review=True,
                        requires_compliance_review=True,
                        recommendations=[
                            "Align access control implementation with compliance framework requirements",
                            "Ensure audit logging meets both security and compliance standards",
                        ],
                    ))
        
        # Check architecture + engineering overlap (common: scalability, maintainability)
        for arch_finding in architecture_findings:
            arch_title_lower = arch_finding.title.lower()
            
            for eng_finding in engineering_findings:
                eng_title_lower = eng_finding.title.lower()
                
                if self._titles_overlap(arch_title_lower, eng_title_lower, ["complexity", "coupling", "dependency", "scale"]):
                    concerns.append(CrossFunctionalConcern(
                        title=f"Architecture & Engineering: {arch_finding.title}",
                        description=(
                            f"Technical debt or complexity issue spans architecture and engineering. "
                            f"This may require architectural changes to address engineering concerns."
                        ),
                        dimensions=[ReviewDimension.ARCHITECTURE, ReviewDimension.ENGINEERING],
                        related_findings=[arch_finding, eng_finding],
                        severity=max(arch_finding.severity, eng_finding.severity, key=lambda s: self._severity_weight(s)),
                        teams_involved=["Architecture", "Engineering"],
                        requires_architecture_review=True,
                        recommendations=[
                            "Review architectural patterns to reduce engineering complexity",
                            "Consider refactoring to improve maintainability",
                        ],
                    ))
        
        return concerns
    
    def _detect_cascading_impacts(
        self,
        security_findings: list[SecurityFinding],
        privacy_findings: list[PrivacyFinding],
        compliance_findings: list[ComplianceFinding],
        engineering_findings: list[EngineeringFinding],
        architecture_findings: list[ArchitectureFinding],
    ) -> list[CrossFunctionalConcern]:
        """Detect findings that cascade into other dimensions."""
        concerns: list[CrossFunctionalConcern] = []
        
        # Architecture changes affecting security
        for arch_finding in architecture_findings:
            if any(kw in arch_finding.title.lower() for kw in ["api", "service", "boundary", "endpoint"]):
                # Check if there are related security findings
                related_security = [
                    f for f in security_findings
                    if any(kw in f.title.lower() for kw in ["api", "endpoint", "access", "auth"])
                ]
                
                if related_security:
                    concerns.append(CrossFunctionalConcern(
                        title=f"Architectural Change with Security Impact: {arch_finding.title}",
                        description=(
                            f"This architectural change may impact security controls. "
                            f"{len(related_security)} security findings may be affected."
                        ),
                        dimensions=[ReviewDimension.ARCHITECTURE, ReviewDimension.SECURITY],
                        related_findings=[arch_finding] + related_security[:3],
                        severity=Severity.HIGH if arch_finding.severity == Severity.CRITICAL else Severity.MEDIUM,
                        teams_involved=["Architecture", "Security"],
                        requires_architecture_review=True,
                        requires_security_review=True,
                        recommendations=[
                            "Conduct security review before implementing architectural changes",
                            "Update threat model for new architecture",
                            "Ensure security controls are maintained across service boundaries",
                        ],
                    ))
        
        # Engineering debt affecting compliance
        high_debt_findings = [
            f for f in engineering_findings
            if f.severity in (Severity.HIGH, Severity.CRITICAL) and
            any(kw in f.title.lower() for kw in ["debt", "missing", "test", "documentation"])
        ]
        
        if high_debt_findings and compliance_findings:
            concerns.append(CrossFunctionalConcern(
                title="Technical Debt Impacting Compliance Posture",
                description=(
                    f"High technical debt ({len(high_debt_findings)} issues) may impact ability to "
                    f"maintain compliance with {len(compliance_findings)} compliance requirements."
                ),
                dimensions=[ReviewDimension.ENGINEERING, ReviewDimension.COMPLIANCE],
                related_findings=high_debt_findings[:3] + compliance_findings[:2],
                severity=Severity.HIGH,
                teams_involved=["Engineering", "Compliance/GRC"],
                requires_compliance_review=True,
                recommendations=[
                    "Prioritize technical debt that impacts audit trail and documentation",
                    "Ensure test coverage meets compliance requirements",
                    "Address missing documentation for compliance-critical components",
                ],
            ))
        
        return concerns
    
    def _detect_coordination_requirements(
        self,
        security_findings: list[SecurityFinding],
        privacy_findings: list[PrivacyFinding],
        compliance_findings: list[ComplianceFinding],
        engineering_findings: list[EngineeringFinding],
        architecture_findings: list[ArchitectureFinding],
    ) -> list[CrossFunctionalConcern]:
        """Detect findings requiring multi-team coordination."""
        concerns: list[CrossFunctionalConcern] = []
        
        # Critical findings requiring immediate coordination
        critical_findings: list[tuple[Finding, ReviewDimension]] = []
        
        for f in security_findings:
            if f.severity == Severity.CRITICAL:
                critical_findings.append((f, ReviewDimension.SECURITY))
        
        for f in privacy_findings:
            if f.severity == Severity.CRITICAL:
                critical_findings.append((f, ReviewDimension.PRIVACY))
        
        for f in compliance_findings:
            if f.severity == Severity.CRITICAL:
                critical_findings.append((f, ReviewDimension.COMPLIANCE))
        
        if len(critical_findings) >= 2:
            dimensions = list(set(d for _, d in critical_findings))
            findings = [f for f, _ in critical_findings]
            
            concerns.append(CrossFunctionalConcern(
                title="Multiple Critical Findings Requiring Cross-Team Coordination",
                description=(
                    f"{len(critical_findings)} critical findings across {len(dimensions)} dimensions "
                    f"require immediate coordinated response."
                ),
                dimensions=dimensions,
                related_findings=findings[:5],
                severity=Severity.CRITICAL,
                impact_score=1.0,
                teams_involved=self._dimensions_to_teams(dimensions),
                requires_architecture_review=ReviewDimension.ARCHITECTURE in dimensions,
                requires_security_review=ReviewDimension.SECURITY in dimensions,
                requires_compliance_review=ReviewDimension.COMPLIANCE in dimensions,
                recommendations=[
                    "Schedule immediate cross-functional meeting",
                    "Create shared remediation plan with clear ownership",
                    "Establish communication channel for coordination",
                ],
                coordination_notes=(
                    "This is a critical cross-functional concern requiring immediate attention "
                    "from multiple teams. Consider blocking release until addressed."
                ),
            ))
        
        # Data flow concerns (privacy + security + architecture)
        if privacy_findings and security_findings and architecture_findings:
            data_flow_privacy = [f for f in privacy_findings if "data" in f.title.lower() or "flow" in f.title.lower()]
            data_flow_security = [f for f in security_findings if "data" in f.title.lower() or "flow" in f.title.lower()]
            data_flow_arch = [f for f in architecture_findings if "data" in f.title.lower() or "model" in f.title.lower()]
            
            if data_flow_privacy or data_flow_security or data_flow_arch:
                concerns.append(CrossFunctionalConcern(
                    title="Data Flow Architecture Review Required",
                    description=(
                        "Data handling concerns identified across privacy, security, and architecture. "
                        "A comprehensive data flow review is recommended."
                    ),
                    dimensions=[ReviewDimension.PRIVACY, ReviewDimension.SECURITY, ReviewDimension.ARCHITECTURE],
                    related_findings=(data_flow_privacy[:2] + data_flow_security[:2] + data_flow_arch[:2]),
                    severity=Severity.HIGH,
                    teams_involved=["Privacy/Legal", "Security", "Architecture", "Data Engineering"],
                    requires_architecture_review=True,
                    requires_security_review=True,
                    recommendations=[
                        "Map all data flows and classify by sensitivity",
                        "Review data retention and deletion requirements",
                        "Ensure encryption at rest and in transit",
                        "Document data processing activities for compliance",
                    ],
                ))
        
        return concerns
    
    def _titles_overlap(self, title1: str, title2: str, keywords: list[str]) -> bool:
        """Check if two finding titles overlap on specific keywords."""
        for keyword in keywords:
            if keyword in title1 and keyword in title2:
                return True
        return False
    
    def _severity_weight(self, severity: Severity) -> int:
        """Get numeric weight for severity comparison."""
        weights = {
            Severity.CRITICAL: 5,
            Severity.HIGH: 4,
            Severity.MEDIUM: 3,
            Severity.LOW: 2,
            Severity.INFO: 1,
        }
        return weights.get(severity, 0)
    
    def _dimensions_to_teams(self, dimensions: list[ReviewDimension]) -> list[str]:
        """Convert dimensions to team names."""
        team_map = {
            ReviewDimension.SECURITY: "Security",
            ReviewDimension.PRIVACY: "Privacy/Legal",
            ReviewDimension.COMPLIANCE: "Compliance/GRC",
            ReviewDimension.ENGINEERING: "Engineering",
            ReviewDimension.ARCHITECTURE: "Architecture",
        }
        return [team_map.get(d, d.value) for d in dimensions]
    
    def _generate_recommendations(self, result: CrossFunctionalAnalysisResult) -> list[str]:
        """Generate coordination recommendations based on analysis."""
        recommendations: list[str] = []
        
        if result.has_critical_concerns:
            recommendations.append(
                "URGENT: Schedule cross-functional review meeting for critical concerns"
            )
        
        if len(result.dimensions_with_overlap) >= 3:
            recommendations.append(
                "Consider establishing a cross-functional working group for this project"
            )
        
        # Check for specific patterns
        security_compliance_overlap = any(
            (ReviewDimension.SECURITY, ReviewDimension.COMPLIANCE) in [tuple(sorted([d1, d2], key=lambda x: x.value)) for d1, d2 in [(ReviewDimension.SECURITY, ReviewDimension.COMPLIANCE)]]
            for d1, d2 in result.dimensions_with_overlap
        )
        
        if security_compliance_overlap:
            recommendations.append(
                "Align security controls with compliance framework requirements before implementation"
            )
        
        privacy_findings_count = sum(
            1 for c in result.concerns
            if ReviewDimension.PRIVACY in c.dimensions
        )
        
        if privacy_findings_count > 0:
            recommendations.append(
                "Conduct privacy impact assessment (PIA) for changes involving personal data"
            )
        
        arch_changes = sum(
            1 for c in result.concerns
            if ReviewDimension.ARCHITECTURE in c.dimensions
        )
        
        if arch_changes > 2:
            recommendations.append(
                "Document architectural decisions in ADRs for traceability"
            )
        
        return recommendations
    
    def _build_overlap_patterns(self) -> dict[str, list[str]]:
        """Build patterns for detecting overlap between dimensions."""
        return {
            "security_privacy": [
                "data", "pii", "sensitive", "encryption", "personal",
                "user data", "customer data", "health information",
            ],
            "security_compliance": [
                "access control", "audit", "logging", "authentication",
                "authorization", "mfa", "password", "session",
            ],
            "architecture_engineering": [
                "complexity", "coupling", "dependency", "technical debt",
                "maintainability", "scalability", "performance",
            ],
            "privacy_compliance": [
                "gdpr", "ccpa", "consent", "retention", "deletion",
                "data subject", "processing", "legal basis",
            ],
        }
    
    def _build_cascade_patterns(self) -> dict[str, list[str]]:
        """Build patterns for detecting cascading impacts."""
        return {
            "architecture_to_security": [
                "api", "endpoint", "service boundary", "trust boundary",
                "microservice", "integration", "external",
            ],
            "engineering_to_compliance": [
                "documentation", "testing", "audit trail", "logging",
                "code review", "change management",
            ],
            "security_to_privacy": [
                "encryption", "access", "authentication", "data",
            ],
        }


# Convenience function

def detect_cross_functional_concerns(
    security_findings: list[SecurityFinding] | None = None,
    privacy_findings: list[PrivacyFinding] | None = None,
    compliance_findings: list[ComplianceFinding] | None = None,
    engineering_findings: list[EngineeringFinding] | None = None,
    architecture_findings: list[ArchitectureFinding] | None = None,
) -> CrossFunctionalAnalysisResult:
    """
    Convenience function to detect cross-functional concerns.
    
    Args:
        security_findings: Security findings
        privacy_findings: Privacy findings
        compliance_findings: Compliance findings
        engineering_findings: Engineering findings
        architecture_findings: Architecture findings
        
    Returns:
        CrossFunctionalAnalysisResult with identified concerns
    """
    detector = CrossFunctionalDetector()
    return detector.analyze(
        security_findings=security_findings or [],
        privacy_findings=privacy_findings or [],
        compliance_findings=compliance_findings or [],
        engineering_findings=engineering_findings or [],
        architecture_findings=architecture_findings or [],
    )
