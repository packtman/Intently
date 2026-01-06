"""
Privacy Analyzer - LINDDUN-based privacy threat analysis.

Implements:
- LINDDUN privacy threat modeling
- GDPR/CCPA compliance checking
- Personal data flow analysis
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

from context_graph.core.models import (
    PrivacyFinding,
    PrivacyCategory,
    Severity,
    ReviewDimension,
)
from context_graph.security.delta_analyzer import DeltaAnalysisResult


class LinddunCategory(str, Enum):
    """LINDDUN privacy threat categories."""
    
    LINKING = "linking"
    IDENTIFYING = "identifying"
    NON_REPUDIATION = "non_repudiation"
    DETECTING = "detecting"
    DATA_DISCLOSURE = "data_disclosure"
    UNAWARENESS = "unawareness"
    NON_COMPLIANCE = "non_compliance"


@dataclass
class PrivacyPattern:
    """A privacy threat pattern to match against."""
    
    id: str
    name: str
    description: str
    category: PrivacyCategory
    linddun_category: LinddunCategory | None = None
    severity: Severity = Severity.MEDIUM
    
    # Matching conditions
    requires_pii: bool = False
    requires_data_flow: bool = False
    requires_external_integration: bool = False
    requires_user_data: bool = False
    requires_cross_border: bool = False
    
    # Data types that trigger this pattern
    sensitive_data_types: list[str] = field(default_factory=list)
    
    # Regulatory context
    applicable_regulations: list[str] = field(default_factory=list)
    
    # Recommendation
    recommendation: str = ""
    mitigations: list[str] = field(default_factory=list)


# Define privacy patterns based on LINDDUN
PRIVACY_PATTERNS = [
    # LINDDUN: Linking
    PrivacyPattern(
        id="LINK-001",
        name="Data Correlation Risk",
        description="Multiple data points can be linked to build comprehensive user profiles",
        category=PrivacyCategory.LINKING,
        linddun_category=LinddunCategory.LINKING,
        severity=Severity.HIGH,
        requires_pii=True,
        sensitive_data_types=["email", "name", "phone", "address", "user_id"],
        applicable_regulations=["GDPR", "CCPA"],
        recommendation="Implement data minimization and pseudonymization",
        mitigations=[
            "Collect only necessary data",
            "Use pseudonymous identifiers",
            "Separate data stores for different purposes",
            "Implement access controls on linked data",
        ],
    ),
    PrivacyPattern(
        id="LINK-002",
        name="Cross-Service Data Linking",
        description="External integrations may allow cross-service user tracking",
        category=PrivacyCategory.LINKING,
        linddun_category=LinddunCategory.LINKING,
        severity=Severity.MEDIUM,
        requires_external_integration=True,
        applicable_regulations=["GDPR", "CCPA"],
        recommendation="Review third-party data sharing and implement tracking prevention",
        mitigations=[
            "Audit third-party data sharing",
            "Use privacy-preserving identifiers",
            "Implement consent for cross-service tracking",
        ],
    ),
    
    # LINDDUN: Identifying
    PrivacyPattern(
        id="IDENT-001",
        name="Direct Identifier Exposure",
        description="Directly identifying information may be exposed or stored insecurely",
        category=PrivacyCategory.IDENTIFYING,
        linddun_category=LinddunCategory.IDENTIFYING,
        severity=Severity.HIGH,
        requires_pii=True,
        sensitive_data_types=["name", "email", "ssn", "national_id", "passport"],
        applicable_regulations=["GDPR", "CCPA", "HIPAA"],
        recommendation="Encrypt and minimize direct identifiers",
        mitigations=[
            "Encrypt identifiers at rest",
            "Use tokenization",
            "Implement field-level encryption",
            "Apply data masking in non-production environments",
        ],
    ),
    PrivacyPattern(
        id="IDENT-002",
        name="Quasi-Identifier Combination",
        description="Combination of quasi-identifiers may enable re-identification",
        category=PrivacyCategory.IDENTIFYING,
        linddun_category=LinddunCategory.IDENTIFYING,
        severity=Severity.MEDIUM,
        requires_user_data=True,
        sensitive_data_types=["age", "gender", "location", "occupation", "zip_code"],
        applicable_regulations=["GDPR"],
        recommendation="Apply k-anonymity or differential privacy techniques",
        mitigations=[
            "Generalize quasi-identifiers",
            "Apply k-anonymity",
            "Implement differential privacy",
            "Limit data combinations in queries",
        ],
    ),
    
    # LINDDUN: Non-repudiation (privacy context)
    PrivacyPattern(
        id="NONREP-001",
        name="Excessive User Action Logging",
        description="Detailed logging of user actions may violate privacy expectations",
        category=PrivacyCategory.NON_REPUDIATION,
        linddun_category=LinddunCategory.NON_REPUDIATION,
        severity=Severity.MEDIUM,
        requires_user_data=True,
        applicable_regulations=["GDPR"],
        recommendation="Balance security logging with privacy requirements",
        mitigations=[
            "Minimize logged personal data",
            "Implement log retention policies",
            "Anonymize logs after retention period",
            "Document logging in privacy notice",
        ],
    ),
    
    # LINDDUN: Detecting
    PrivacyPattern(
        id="DETECT-001",
        name="Behavioral Pattern Detection",
        description="User behavior patterns may be detectable and analyzed",
        category=PrivacyCategory.DETECTING,
        linddun_category=LinddunCategory.DETECTING,
        severity=Severity.MEDIUM,
        requires_user_data=True,
        sensitive_data_types=["activity_log", "usage_pattern", "browsing_history"],
        applicable_regulations=["GDPR", "CCPA"],
        recommendation="Implement purpose limitation for behavioral data",
        mitigations=[
            "Limit behavioral data collection",
            "Obtain consent for profiling",
            "Provide opt-out mechanisms",
            "Implement data minimization",
        ],
    ),
    PrivacyPattern(
        id="DETECT-002",
        name="Location Tracking",
        description="Location data collection enables tracking user movements",
        category=PrivacyCategory.DETECTING,
        linddun_category=LinddunCategory.DETECTING,
        severity=Severity.HIGH,
        requires_pii=True,
        sensitive_data_types=["location", "gps", "ip_address", "geolocation"],
        applicable_regulations=["GDPR", "CCPA"],
        recommendation="Minimize location data and implement consent mechanisms",
        mitigations=[
            "Collect location only when necessary",
            "Use approximate location when possible",
            "Implement clear consent for tracking",
            "Provide location history deletion",
        ],
    ),
    
    # LINDDUN: Data Disclosure
    PrivacyPattern(
        id="DISC-001",
        name="Unauthorized Data Access",
        description="Personal data may be accessed by unauthorized parties",
        category=PrivacyCategory.DATA_DISCLOSURE,
        linddun_category=LinddunCategory.DATA_DISCLOSURE,
        severity=Severity.CRITICAL,
        requires_pii=True,
        applicable_regulations=["GDPR", "CCPA", "HIPAA"],
        recommendation="Implement strict access controls and encryption",
        mitigations=[
            "Implement role-based access control",
            "Encrypt data at rest and in transit",
            "Audit data access",
            "Implement data loss prevention",
        ],
    ),
    PrivacyPattern(
        id="DISC-002",
        name="Third-Party Data Sharing",
        description="Personal data shared with third parties without adequate controls",
        category=PrivacyCategory.DATA_DISCLOSURE,
        linddun_category=LinddunCategory.DATA_DISCLOSURE,
        severity=Severity.HIGH,
        requires_external_integration=True,
        requires_pii=True,
        applicable_regulations=["GDPR", "CCPA"],
        recommendation="Establish data processing agreements and minimize sharing",
        mitigations=[
            "Execute Data Processing Agreements",
            "Minimize data shared with third parties",
            "Audit third-party data handling",
            "Implement consent for data sharing",
        ],
    ),
    
    # LINDDUN: Unawareness
    PrivacyPattern(
        id="UNAWARE-001",
        name="Insufficient Privacy Notice",
        description="Users may not be adequately informed about data processing",
        category=PrivacyCategory.UNAWARENESS,
        linddun_category=LinddunCategory.UNAWARENESS,
        severity=Severity.HIGH,
        requires_pii=True,
        applicable_regulations=["GDPR", "CCPA"],
        recommendation="Implement comprehensive and clear privacy notices",
        mitigations=[
            "Create clear privacy policy",
            "Implement just-in-time notices",
            "Explain data usage at collection",
            "Maintain records of processing activities",
        ],
    ),
    PrivacyPattern(
        id="UNAWARE-002",
        name="Hidden Data Collection",
        description="Data collection may occur without user awareness",
        category=PrivacyCategory.UNAWARENESS,
        linddun_category=LinddunCategory.UNAWARENESS,
        severity=Severity.HIGH,
        requires_user_data=True,
        applicable_regulations=["GDPR", "CCPA"],
        recommendation="Make all data collection transparent and obtain consent",
        mitigations=[
            "Disclose all data collection",
            "Obtain explicit consent",
            "Avoid dark patterns",
            "Provide data collection dashboard",
        ],
    ),
    
    # LINDDUN: Non-compliance
    PrivacyPattern(
        id="COMPLY-001",
        name="Missing Data Subject Rights",
        description="Required data subject rights may not be implemented",
        category=PrivacyCategory.NON_COMPLIANCE,
        linddun_category=LinddunCategory.NON_COMPLIANCE,
        severity=Severity.CRITICAL,
        requires_pii=True,
        applicable_regulations=["GDPR", "CCPA"],
        recommendation="Implement all required data subject rights",
        mitigations=[
            "Implement access request handling",
            "Enable data portability",
            "Implement right to erasure",
            "Provide rectification mechanisms",
            "Enable objection to processing",
        ],
    ),
    PrivacyPattern(
        id="COMPLY-002",
        name="Cross-Border Transfer Without Safeguards",
        description="Personal data transferred internationally without adequate protections",
        category=PrivacyCategory.CROSS_BORDER_TRANSFER,
        linddun_category=LinddunCategory.NON_COMPLIANCE,
        severity=Severity.HIGH,
        requires_cross_border=True,
        requires_pii=True,
        applicable_regulations=["GDPR"],
        recommendation="Implement appropriate transfer mechanisms",
        mitigations=[
            "Use Standard Contractual Clauses",
            "Implement Binding Corporate Rules",
            "Verify adequacy decisions",
            "Conduct Transfer Impact Assessments",
        ],
    ),
    PrivacyPattern(
        id="COMPLY-003",
        name="Missing Legal Basis",
        description="Processing personal data without establishing legal basis",
        category=PrivacyCategory.NON_COMPLIANCE,
        linddun_category=LinddunCategory.NON_COMPLIANCE,
        severity=Severity.CRITICAL,
        requires_pii=True,
        applicable_regulations=["GDPR"],
        recommendation="Establish and document legal basis for all processing",
        mitigations=[
            "Identify legal basis for each processing activity",
            "Document legal basis in privacy notice",
            "Implement consent management where needed",
            "Maintain records of processing activities",
        ],
    ),
    
    # GDPR/CCPA specific
    PrivacyPattern(
        id="GDPR-001",
        name="Data Retention Violation",
        description="Personal data may be retained longer than necessary",
        category=PrivacyCategory.RETENTION_VIOLATION,
        severity=Severity.MEDIUM,
        requires_pii=True,
        applicable_regulations=["GDPR", "CCPA"],
        recommendation="Implement data retention policies and automated deletion",
        mitigations=[
            "Define retention periods for all data types",
            "Implement automated data deletion",
            "Document retention justification",
            "Regular retention audits",
        ],
    ),
    PrivacyPattern(
        id="GDPR-002",
        name="Purpose Limitation Violation",
        description="Data may be used for purposes beyond original collection",
        category=PrivacyCategory.PURPOSE_LIMITATION,
        severity=Severity.HIGH,
        requires_pii=True,
        applicable_regulations=["GDPR"],
        recommendation="Limit data use to specified purposes",
        mitigations=[
            "Document purposes for each data type",
            "Implement purpose-based access controls",
            "Obtain new consent for new purposes",
            "Audit data usage against stated purposes",
        ],
    ),
    PrivacyPattern(
        id="GDPR-003",
        name="Consent Management Gap",
        description="Consent collection and management may be insufficient",
        category=PrivacyCategory.CONSENT_VIOLATION,
        severity=Severity.HIGH,
        requires_pii=True,
        applicable_regulations=["GDPR", "CCPA"],
        recommendation="Implement comprehensive consent management",
        mitigations=[
            "Implement granular consent options",
            "Enable easy consent withdrawal",
            "Maintain consent records",
            "Avoid pre-checked consent boxes",
        ],
    ),
]


class PrivacyPatternMatcher:
    """
    Matches privacy threat patterns against delta analysis results using LINDDUN framework.
    """
    
    def __init__(self, patterns: list[PrivacyPattern] | None = None) -> None:
        self.patterns = patterns or PRIVACY_PATTERNS
        
        # Common PII indicators
        self.pii_indicators = {
            "name", "email", "phone", "address", "ssn", "social_security",
            "national_id", "passport", "driver_license", "dob", "date_of_birth",
            "birthday", "age", "gender", "sex", "race", "ethnicity",
            "religion", "political", "health", "medical", "genetic", "biometric",
            "fingerprint", "face", "facial", "voice", "retina", "iris",
            "credit_card", "bank_account", "financial", "salary", "income",
            "location", "gps", "coordinates", "ip_address", "device_id",
            "user_id", "customer_id", "account", "username", "password",
        }
        
        # Location-related indicators
        self.location_indicators = {
            "location", "gps", "coordinates", "latitude", "longitude",
            "geolocation", "address", "city", "country", "zip", "postal",
        }
    
    def match(self, delta_result: DeltaAnalysisResult) -> list[PrivacyFinding]:
        """
        Match patterns against delta and generate privacy findings.
        
        Args:
            delta_result: The delta analysis result
            
        Returns:
            List of privacy findings
        """
        findings: list[PrivacyFinding] = []
        
        # Analyze delta for privacy-relevant information
        has_pii = self._check_pii_presence(delta_result)
        has_external = delta_result.introduces_external_integration
        has_user_data = self._check_user_data(delta_result)
        has_data_flow = bool(delta_result.new_endpoints or delta_result.new_data_models)
        has_cross_border = self._check_cross_border(delta_result)
        
        # Match patterns
        for pattern in self.patterns:
            if self._pattern_matches(
                pattern, 
                has_pii, 
                has_external, 
                has_user_data,
                has_data_flow,
                has_cross_border,
                delta_result,
            ):
                finding = self._create_finding(pattern, delta_result)
                findings.append(finding)
        
        # Run custom privacy checks
        findings.extend(self._run_custom_checks(delta_result))
        
        # Deduplicate and sort
        findings = self._deduplicate_findings(findings)
        findings = self._sort_by_severity(findings)
        
        return findings
    
    def _check_pii_presence(self, delta: DeltaAnalysisResult) -> bool:
        """Check if delta introduces or handles PII."""
        if delta.introduces_pii:
            return True
        
        # Check data models for PII indicators
        for model in delta.new_data_models:
            model_name = model.get("name", "").lower()
            fields = model.get("fields", [])
            
            # Check model name
            if any(indicator in model_name for indicator in self.pii_indicators):
                return True
            
            # Check field names
            for field_info in fields:
                field_name = field_info.get("name", "").lower() if isinstance(field_info, dict) else str(field_info).lower()
                if any(indicator in field_name for indicator in self.pii_indicators):
                    return True
        
        return False
    
    def _check_user_data(self, delta: DeltaAnalysisResult) -> bool:
        """Check if delta handles user-related data."""
        user_indicators = {"user", "customer", "member", "account", "profile", "person"}
        
        for model in delta.new_data_models:
            model_name = model.get("name", "").lower()
            if any(indicator in model_name for indicator in user_indicators):
                return True
        
        for endpoint in delta.new_endpoints:
            path = endpoint.get("path", "").lower()
            if any(indicator in path for indicator in user_indicators):
                return True
        
        return False
    
    def _check_cross_border(self, delta: DeltaAnalysisResult) -> bool:
        """Check if delta involves cross-border data transfers."""
        cross_border_indicators = {
            "international", "cross-border", "transfer", "export",
            "eu", "europe", "gdpr", "cloud", "aws", "azure", "gcp",
        }
        
        for boundary in delta.trust_boundary_impacts:
            if any(indicator in boundary.lower() for indicator in cross_border_indicators):
                return True
        
        return False
    
    def _pattern_matches(
        self,
        pattern: PrivacyPattern,
        has_pii: bool,
        has_external: bool,
        has_user_data: bool,
        has_data_flow: bool,
        has_cross_border: bool,
        delta: DeltaAnalysisResult,
    ) -> bool:
        """Check if a pattern matches the delta conditions."""
        if pattern.requires_pii and not has_pii:
            return False
        
        if pattern.requires_external_integration and not has_external:
            return False
        
        if pattern.requires_user_data and not has_user_data:
            return False
        
        if pattern.requires_data_flow and not has_data_flow:
            return False
        
        if pattern.requires_cross_border and not has_cross_border:
            return False
        
        # Check for specific sensitive data types
        if pattern.sensitive_data_types:
            found_sensitive = False
            for model in delta.new_data_models:
                fields = model.get("fields", [])
                for field_info in fields:
                    field_name = field_info.get("name", "").lower() if isinstance(field_info, dict) else str(field_info).lower()
                    for sensitive_type in pattern.sensitive_data_types:
                        if sensitive_type.lower() in field_name:
                            found_sensitive = True
                            break
                    if found_sensitive:
                        break
                if found_sensitive:
                    break
            
            if pattern.sensitive_data_types and not found_sensitive and not has_pii:
                return False
        
        return True
    
    def _create_finding(
        self,
        pattern: PrivacyPattern,
        delta: DeltaAnalysisResult,
    ) -> PrivacyFinding:
        """Create a privacy finding from a matched pattern."""
        # Extract affected personal data types
        personal_data_types = []
        data_subjects = []
        
        for model in delta.new_data_models:
            model_name = model.get("name", "").lower()
            fields = model.get("fields", [])
            
            # Identify data subjects
            if "user" in model_name or "customer" in model_name:
                data_subjects.append("users")
            if "employee" in model_name or "staff" in model_name:
                data_subjects.append("employees")
            
            # Identify personal data types
            for field_info in fields:
                field_name = field_info.get("name", "").lower() if isinstance(field_info, dict) else str(field_info).lower()
                for pii in self.pii_indicators:
                    if pii in field_name:
                        personal_data_types.append(field_name)
                        break
        
        # Determine processing activities
        processing_activities = []
        if delta.new_endpoints:
            for ep in delta.new_endpoints:
                method = ep.get("method", "").upper()
                if method == "POST":
                    processing_activities.append("collection")
                elif method == "GET":
                    processing_activities.append("access")
                elif method in ("PUT", "PATCH"):
                    processing_activities.append("modification")
                elif method == "DELETE":
                    processing_activities.append("erasure")
        
        return PrivacyFinding(
            id=uuid4(),
            title=pattern.name,
            description=pattern.description,
            severity=pattern.severity,
            category=pattern.category,
            dimension=ReviewDimension.PRIVACY,
            data_subjects=list(set(data_subjects)) or ["users"],
            personal_data_types=list(set(personal_data_types)),
            processing_activities=list(set(processing_activities)),
            applicable_regulations=pattern.applicable_regulations,
            legal_basis_required="GDPR" in pattern.applicable_regulations,
            consent_required="consent" in pattern.name.lower() or pattern.category == PrivacyCategory.CONSENT_VIOLATION,
            source_type="pattern",
            source_reference=f"pattern:{pattern.id}",
            recommendation=pattern.recommendation,
            mitigations=pattern.mitigations,
            confidence=0.7,
        )
    
    def _run_custom_checks(self, delta: DeltaAnalysisResult) -> list[PrivacyFinding]:
        """Run custom privacy checks beyond pattern matching."""
        findings: list[PrivacyFinding] = []
        
        # Check for special categories of data
        findings.extend(self._check_special_categories(delta))
        
        # Check for child data
        findings.extend(self._check_child_data(delta))
        
        # Check for biometric data
        findings.extend(self._check_biometric_data(delta))
        
        return findings
    
    def _check_special_categories(self, delta: DeltaAnalysisResult) -> list[PrivacyFinding]:
        """Check for special categories of personal data (GDPR Article 9)."""
        findings: list[PrivacyFinding] = []
        
        special_categories = {
            "health": ["health", "medical", "diagnosis", "treatment", "prescription", "symptom"],
            "genetic": ["genetic", "dna", "genome"],
            "biometric": ["biometric", "fingerprint", "face_id", "facial", "retina", "iris", "voice_print"],
            "racial": ["race", "ethnic", "ethnicity"],
            "political": ["political", "party", "vote"],
            "religious": ["religion", "religious", "belief", "faith"],
            "sexual": ["sexual", "sex_life", "orientation"],
            "trade_union": ["union", "trade_union"],
        }
        
        for model in delta.new_data_models:
            fields = model.get("fields", [])
            for field_info in fields:
                field_name = field_info.get("name", "").lower() if isinstance(field_info, dict) else str(field_info).lower()
                
                for category, indicators in special_categories.items():
                    if any(indicator in field_name for indicator in indicators):
                        findings.append(PrivacyFinding(
                            id=uuid4(),
                            title=f"Special Category Data: {category.title()}",
                            description=f"Processing of special category data ({category}) requires explicit consent and additional safeguards under GDPR Article 9.",
                            severity=Severity.CRITICAL,
                            category=PrivacyCategory.NON_COMPLIANCE,
                            dimension=ReviewDimension.PRIVACY,
                            data_subjects=["users"],
                            personal_data_types=[field_name],
                            processing_activities=["collection", "processing"],
                            applicable_regulations=["GDPR Article 9"],
                            legal_basis_required=True,
                            consent_required=True,
                            source_type="pattern",
                            source_reference=f"special_category:{category}",
                            recommendation=f"Ensure explicit consent and implement enhanced protections for {category} data",
                            mitigations=[
                                "Obtain explicit consent",
                                "Implement enhanced access controls",
                                "Conduct Data Protection Impact Assessment",
                                "Minimize collection of special category data",
                            ],
                            confidence=0.9,
                        ))
                        break
        
        return findings
    
    def _check_child_data(self, delta: DeltaAnalysisResult) -> list[PrivacyFinding]:
        """Check for processing of children's data."""
        findings: list[PrivacyFinding] = []
        
        child_indicators = ["child", "minor", "kid", "youth", "teen", "student", "parental"]
        
        for model in delta.new_data_models:
            model_name = model.get("name", "").lower()
            if any(indicator in model_name for indicator in child_indicators):
                findings.append(PrivacyFinding(
                    id=uuid4(),
                    title="Children's Data Processing",
                    description="Processing children's data requires parental consent and enhanced protections under GDPR and COPPA.",
                    severity=Severity.CRITICAL,
                    category=PrivacyCategory.CONSENT_VIOLATION,
                    dimension=ReviewDimension.PRIVACY,
                    data_subjects=["children", "minors"],
                    personal_data_types=[],
                    processing_activities=["collection"],
                    applicable_regulations=["GDPR", "COPPA"],
                    legal_basis_required=True,
                    consent_required=True,
                    source_type="pattern",
                    source_reference="child_data",
                    recommendation="Implement age verification and parental consent mechanisms",
                    mitigations=[
                        "Implement age verification",
                        "Obtain verifiable parental consent",
                        "Minimize data collection from children",
                        "Provide child-appropriate privacy notices",
                    ],
                    confidence=0.85,
                ))
                break
        
        return findings
    
    def _check_biometric_data(self, delta: DeltaAnalysisResult) -> list[PrivacyFinding]:
        """Check for biometric data processing."""
        findings: list[PrivacyFinding] = []
        
        biometric_indicators = [
            "fingerprint", "face", "facial", "retina", "iris", "voice",
            "biometric", "faceprint", "voiceprint", "palm", "vein",
        ]
        
        for model in delta.new_data_models:
            fields = model.get("fields", [])
            for field_info in fields:
                field_name = field_info.get("name", "").lower() if isinstance(field_info, dict) else str(field_info).lower()
                
                if any(indicator in field_name for indicator in biometric_indicators):
                    findings.append(PrivacyFinding(
                        id=uuid4(),
                        title="Biometric Data Processing",
                        description="Collection and processing of biometric data requires specific legal basis and security measures.",
                        severity=Severity.CRITICAL,
                        category=PrivacyCategory.DATA_DISCLOSURE,
                        dimension=ReviewDimension.PRIVACY,
                        data_subjects=["users"],
                        personal_data_types=["biometric"],
                        processing_activities=["collection", "storage", "processing"],
                        applicable_regulations=["GDPR Article 9", "BIPA", "CCPA"],
                        legal_basis_required=True,
                        consent_required=True,
                        source_type="pattern",
                        source_reference="biometric_data",
                        recommendation="Implement strict controls for biometric data and obtain explicit consent",
                        mitigations=[
                            "Obtain explicit written consent",
                            "Implement biometric-specific security measures",
                            "Define retention and destruction policies",
                            "Provide clear notice of biometric collection",
                        ],
                        confidence=0.9,
                    ))
                    break
        
        return findings
    
    def _deduplicate_findings(self, findings: list[PrivacyFinding]) -> list[PrivacyFinding]:
        """Remove duplicate or very similar findings."""
        seen_keys: set[str] = set()
        unique_findings: list[PrivacyFinding] = []
        
        for finding in findings:
            key = f"{finding.category}:{finding.title[:30]}"
            if key not in seen_keys:
                seen_keys.add(key)
                unique_findings.append(finding)
        
        return unique_findings
    
    def _sort_by_severity(self, findings: list[PrivacyFinding]) -> list[PrivacyFinding]:
        """Sort findings by severity."""
        severity_order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
            Severity.INFO: 4,
        }
        findings.sort(key=lambda f: severity_order.get(f.severity, 5))
        return findings

