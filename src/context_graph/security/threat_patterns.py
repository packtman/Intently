"""
Threat Pattern Matcher - Match delta against known security threat patterns.

Implements:
- STRIDE threat modeling
- OWASP Top 10 pattern matching
- Custom security rules
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from context_graph.core.models import (
    SecurityFinding,
    Severity,
    ThreatCategory,
    Entity,
    EntityType,
)
from context_graph.security.delta_analyzer import DeltaAnalysisResult


class StrideCategory(str, Enum):
    """STRIDE threat categories."""
    
    SPOOFING = "spoofing"
    TAMPERING = "tampering"
    REPUDIATION = "repudiation"
    INFORMATION_DISCLOSURE = "information_disclosure"
    DENIAL_OF_SERVICE = "denial_of_service"
    ELEVATION_OF_PRIVILEGE = "elevation_of_privilege"


@dataclass
class ThreatPattern:
    """A threat pattern to match against."""
    
    id: str
    name: str
    description: str
    category: ThreatCategory
    stride_category: StrideCategory | None = None
    severity: Severity = Severity.MEDIUM
    
    # Matching conditions
    requires_new_endpoint: bool = False
    requires_sensitive_data: bool = False
    requires_auth_change: bool = False
    requires_external_integration: bool = False
    
    # Custom matcher function name
    custom_matcher: str | None = None
    
    # Recommendation
    recommendation: str = ""
    mitigations: list[str] = field(default_factory=list)


# Define threat patterns
THREAT_PATTERNS = [
    # STRIDE: Spoofing
    ThreatPattern(
        id="SPOOF-001",
        name="Unauthenticated Endpoint",
        description="New endpoint without authentication requirement may allow unauthorized access",
        category=ThreatCategory.SPOOFING,
        stride_category=StrideCategory.SPOOFING,
        severity=Severity.HIGH,
        requires_new_endpoint=True,
        recommendation="Ensure all endpoints require authentication unless explicitly public",
        mitigations=["Add authentication middleware", "Document public endpoint justification"],
    ),
    ThreatPattern(
        id="SPOOF-002",
        name="Weak Authentication Integration",
        description="New authentication flow may have implementation weaknesses",
        category=ThreatCategory.BROKEN_AUTH,
        stride_category=StrideCategory.SPOOFING,
        severity=Severity.HIGH,
        requires_auth_change=True,
        recommendation="Review authentication implementation against OWASP guidelines",
        mitigations=["Use established auth libraries", "Implement MFA", "Add rate limiting"],
    ),
    
    # STRIDE: Tampering
    ThreatPattern(
        id="TAMP-001",
        name="Missing Input Validation",
        description="New endpoints may lack proper input validation",
        category=ThreatCategory.INJECTION,
        stride_category=StrideCategory.TAMPERING,
        severity=Severity.HIGH,
        requires_new_endpoint=True,
        recommendation="Implement input validation on all new endpoints",
        mitigations=["Use validation library", "Sanitize all inputs", "Use parameterized queries"],
    ),
    ThreatPattern(
        id="TAMP-002",
        name="Data Integrity Risk",
        description="New data flows may lack integrity verification",
        category=ThreatCategory.TAMPERING,
        stride_category=StrideCategory.TAMPERING,
        severity=Severity.MEDIUM,
        requires_sensitive_data=True,
        recommendation="Implement data integrity checks for sensitive data",
        mitigations=["Add checksums", "Use signed tokens", "Implement audit logging"],
    ),
    
    # STRIDE: Repudiation
    ThreatPattern(
        id="REPUD-001",
        name="Insufficient Audit Logging",
        description="New operations may not be properly logged for audit",
        category=ThreatCategory.REPUDIATION,
        stride_category=StrideCategory.REPUDIATION,
        severity=Severity.MEDIUM,
        requires_new_endpoint=True,
        recommendation="Ensure all security-relevant operations are logged",
        mitigations=["Add audit logging", "Include user context", "Secure log storage"],
    ),
    
    # STRIDE: Information Disclosure
    ThreatPattern(
        id="INFO-001",
        name="Sensitive Data Exposure",
        description="New data handling may expose sensitive information",
        category=ThreatCategory.SENSITIVE_DATA_EXPOSURE,
        stride_category=StrideCategory.INFORMATION_DISCLOSURE,
        severity=Severity.HIGH,
        requires_sensitive_data=True,
        recommendation="Implement proper data protection for sensitive fields",
        mitigations=["Encrypt at rest", "Encrypt in transit", "Mask in logs", "Apply field-level security"],
    ),
    ThreatPattern(
        id="INFO-002",
        name="Third-Party Data Leakage",
        description="External integration may expose data to third parties",
        category=ThreatCategory.INFO_DISCLOSURE,
        stride_category=StrideCategory.INFORMATION_DISCLOSURE,
        severity=Severity.MEDIUM,
        requires_external_integration=True,
        recommendation="Review data sharing with external services",
        mitigations=["Minimize data sent", "Review privacy policy", "Use data processing agreements"],
    ),
    
    # STRIDE: Denial of Service
    ThreatPattern(
        id="DOS-001",
        name="Missing Rate Limiting",
        description="New endpoints may be vulnerable to abuse without rate limiting",
        category=ThreatCategory.DENIAL_OF_SERVICE,
        stride_category=StrideCategory.DENIAL_OF_SERVICE,
        severity=Severity.MEDIUM,
        requires_new_endpoint=True,
        recommendation="Implement rate limiting on all new endpoints",
        mitigations=["Add rate limiting", "Implement request throttling", "Add monitoring"],
    ),
    
    # STRIDE: Elevation of Privilege
    ThreatPattern(
        id="EOP-001",
        name="Broken Access Control",
        description="New functionality may have authorization bypass vulnerabilities",
        category=ThreatCategory.BROKEN_ACCESS_CONTROL,
        stride_category=StrideCategory.ELEVATION_OF_PRIVILEGE,
        severity=Severity.CRITICAL,
        requires_new_endpoint=True,
        recommendation="Implement proper authorization checks on all endpoints",
        mitigations=["Add RBAC/ABAC", "Verify object ownership", "Test authorization bypass"],
    ),
    ThreatPattern(
        id="EOP-002",
        name="Insecure Direct Object Reference",
        description="New endpoints with IDs may be vulnerable to IDOR",
        category=ThreatCategory.BROKEN_ACCESS_CONTROL,
        stride_category=StrideCategory.ELEVATION_OF_PRIVILEGE,
        severity=Severity.HIGH,
        requires_new_endpoint=True,
        custom_matcher="check_idor_risk",
        recommendation="Implement proper object-level authorization",
        mitigations=["Validate ownership", "Use indirect references", "Add authorization checks"],
    ),
    
    # OWASP specific
    ThreatPattern(
        id="OWASP-A03",
        name="Injection Risk",
        description="New data inputs may be vulnerable to injection attacks",
        category=ThreatCategory.INJECTION,
        severity=Severity.CRITICAL,
        requires_new_endpoint=True,
        recommendation="Use parameterized queries and input validation",
        mitigations=["Use ORM", "Parameterize queries", "Validate/sanitize inputs"],
    ),
    ThreatPattern(
        id="OWASP-A08",
        name="Insecure Deserialization",
        description="New API endpoints accepting complex objects may be vulnerable",
        category=ThreatCategory.INSECURE_DESERIALIZATION,
        severity=Severity.HIGH,
        requires_new_endpoint=True,
        recommendation="Validate and sanitize deserialized data",
        mitigations=["Use safe deserializers", "Validate structure", "Sign serialized data"],
    ),
]


class ThreatPatternMatcher:
    """
    Matches security threat patterns against delta analysis results.
    """
    
    def __init__(self, patterns: list[ThreatPattern] | None = None) -> None:
        self.patterns = patterns or THREAT_PATTERNS
    
    def match(self, delta_result: DeltaAnalysisResult) -> list[SecurityFinding]:
        """
        Match patterns against delta and generate findings.
        
        Args:
            delta_result: The delta analysis result
            
        Returns:
            List of security findings
        """
        findings: list[SecurityFinding] = []
        
        for pattern in self.patterns:
            if self._pattern_matches(pattern, delta_result):
                finding = self._create_finding(pattern, delta_result)
                findings.append(finding)
        
        # Run custom matchers
        findings.extend(self._run_custom_matchers(delta_result))
        
        # Deduplicate similar findings
        findings = self._deduplicate_findings(findings)
        
        # Sort by severity
        severity_order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
            Severity.INFO: 4,
        }
        findings.sort(key=lambda f: severity_order.get(f.severity, 5))
        
        return findings
    
    def _pattern_matches(
        self, 
        pattern: ThreatPattern, 
        delta: DeltaAnalysisResult
    ) -> bool:
        """Check if a pattern matches the delta."""
        # Check required conditions
        if pattern.requires_new_endpoint and not delta.new_endpoints:
            return False
        
        if pattern.requires_sensitive_data and not delta.introduces_pii:
            if not any(dm.get("is_sensitive") for dm in delta.new_data_models):
                return False
        
        if pattern.requires_auth_change and not delta.modifies_auth_flow:
            return False
        
        if pattern.requires_external_integration and not delta.introduces_external_integration:
            return False
        
        # If pattern has custom matcher but no basic conditions, skip here
        if pattern.custom_matcher and not any([
            pattern.requires_new_endpoint,
            pattern.requires_sensitive_data,
            pattern.requires_auth_change,
            pattern.requires_external_integration,
        ]):
            return False
        
        return True
    
    def _create_finding(
        self, 
        pattern: ThreatPattern, 
        delta: DeltaAnalysisResult
    ) -> SecurityFinding:
        """Create a security finding from a matched pattern."""
        # Build affected components list
        affected = []
        
        if pattern.requires_new_endpoint:
            affected.extend([
                ep.get("path", "unknown") 
                for ep in delta.new_endpoints[:5]
            ])
        
        if pattern.requires_sensitive_data:
            affected.extend([
                dm.get("name", "unknown") 
                for dm in delta.new_data_models[:5]
            ])
        
        return SecurityFinding(
            title=pattern.name,
            description=pattern.description,
            severity=pattern.severity,
            category=pattern.category,
            source_type="pattern",  # Changed from "delta" to "pattern" for proper UI display
            source_reference=f"pattern:{pattern.id}",
            recommendation=pattern.recommendation,
            mitigations=pattern.mitigations,
            confidence=0.7,  # Pattern-based matching confidence
        )
    
    def _run_custom_matchers(
        self, 
        delta: DeltaAnalysisResult
    ) -> list[SecurityFinding]:
        """Run custom matcher functions."""
        findings: list[SecurityFinding] = []
        
        # IDOR check
        findings.extend(self._check_idor_risk(delta))
        
        # External integration specific checks
        findings.extend(self._check_integration_risks(delta))
        
        return findings
    
    def _check_idor_risk(self, delta: DeltaAnalysisResult) -> list[SecurityFinding]:
        """Check for IDOR vulnerability patterns."""
        findings: list[SecurityFinding] = []
        
        for endpoint in delta.new_endpoints:
            path = endpoint.get("path", "")
            
            # Check for ID patterns in path
            if "{id}" in path.lower() or "/{" in path or "/<" in path:
                # Check if there's likely object access
                if any(term in path.lower() for term in [
                    "user", "account", "order", "document", "file", "record"
                ]):
                    findings.append(SecurityFinding(
                        title=f"Potential IDOR in {path}",
                        description=(
                            f"Endpoint {path} accepts an ID parameter and appears to "
                            "access user-specific resources. Ensure proper authorization "
                            "checks verify the requester owns/can access the resource."
                        ),
                        severity=Severity.HIGH,
                        category=ThreatCategory.BROKEN_ACCESS_CONTROL,
                        source_type="pattern",  # Changed from "delta" to "pattern"
                        source_reference=path,
                        recommendation="Implement object-level authorization",
                        mitigations=[
                            "Verify resource ownership before access",
                            "Use indirect references",
                            "Log access attempts",
                        ],
                        confidence=0.8,
                    ))
        
        return findings
    
    def _check_integration_risks(
        self, 
        delta: DeltaAnalysisResult
    ) -> list[SecurityFinding]:
        """Check for external integration security risks."""
        findings: list[SecurityFinding] = []
        
        for boundary in delta.trust_boundary_impacts:
            if "payment" in boundary.lower() or "stripe" in boundary.lower():
                findings.append(SecurityFinding(
                    title="Payment Integration Security",
                    description=(
                        "Payment processing integration requires PCI-DSS compliance "
                        "considerations. Ensure card data never touches your servers."
                    ),
                    severity=Severity.HIGH,
                    category=ThreatCategory.SENSITIVE_DATA_EXPOSURE,
                    source_type="pattern",  # Changed from "delta" to "pattern"
                    source_reference=boundary,
                    recommendation="Follow PCI-DSS guidelines for payment handling",
                    mitigations=[
                        "Use tokenization",
                        "Never store card details",
                        "Use hosted payment forms",
                        "Complete SAQ-A if applicable",
                    ],
                    confidence=0.9,
                ))
            
            if "auth0" in boundary.lower() or "okta" in boundary.lower():
                findings.append(SecurityFinding(
                    title="Identity Provider Integration",
                    description=(
                        "External IdP integration requires careful token validation "
                        "and session management."
                    ),
                    severity=Severity.MEDIUM,
                    category=ThreatCategory.BROKEN_AUTH,
                    source_type="pattern",  # Changed from "delta" to "pattern"
                    source_reference=boundary,
                    recommendation="Follow IdP security best practices",
                    mitigations=[
                        "Validate ID tokens properly",
                        "Check token signatures",
                        "Implement proper logout",
                        "Handle token refresh securely",
                    ],
                    confidence=0.85,
                ))
        
        return findings
    
    def _deduplicate_findings(
        self, 
        findings: list[SecurityFinding]
    ) -> list[SecurityFinding]:
        """Remove duplicate or very similar findings."""
        seen_keys: set[str] = set()
        unique_findings: list[SecurityFinding] = []
        
        for finding in findings:
            key = f"{finding.category}:{finding.title[:30]}"
            if key not in seen_keys:
                seen_keys.add(key)
                unique_findings.append(finding)
        
        return unique_findings

