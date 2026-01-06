"""
Core data models for Context Graph.

These models represent the fundamental concepts:
- Intent: What the PRD wants to achieve
- State: Current codebase reality
- Delta: The gap requiring implementation
- SecurityFinding: Identified security concerns
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class EntityType(str, Enum):
    """Types of entities in the context graph."""
    
    # Data entities
    USER = "user"
    DATA = "data"
    PII = "pii"
    SECRET = "secret"
    
    # System entities
    API = "api"
    ENDPOINT = "endpoint"
    SERVICE = "service"
    DATABASE = "database"
    QUEUE = "queue"
    
    # Code entities
    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"
    
    # Security entities
    AUTH_PROVIDER = "auth_provider"
    TRUST_BOUNDARY = "trust_boundary"
    SECURITY_CONTROL = "security_control"


class RelationshipType(str, Enum):
    """Types of relationships between entities."""
    
    # Data flow
    READS = "reads"
    WRITES = "writes"
    FLOWS_TO = "flows_to"
    TRANSFORMS = "transforms"
    
    # Access control
    AUTHENTICATES = "authenticates"
    AUTHORIZES = "authorizes"
    OWNS = "owns"
    ACCESSES = "accesses"
    
    # Trust
    TRUSTS = "trusts"
    VALIDATES = "validates"
    SANITIZES = "sanitizes"
    
    # Structural
    CONTAINS = "contains"
    CALLS = "calls"
    DEPENDS_ON = "depends_on"
    IMPLEMENTS = "implements"


class Severity(str, Enum):
    """Security finding severity levels."""
    
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ThreatCategory(str, Enum):
    """STRIDE + additional threat categories."""
    
    # STRIDE
    SPOOFING = "spoofing"
    TAMPERING = "tampering"
    REPUDIATION = "repudiation"
    INFO_DISCLOSURE = "information_disclosure"
    DENIAL_OF_SERVICE = "denial_of_service"
    ELEVATION_OF_PRIVILEGE = "elevation_of_privilege"
    
    # Additional categories
    INJECTION = "injection"
    BROKEN_AUTH = "broken_authentication"
    SENSITIVE_DATA_EXPOSURE = "sensitive_data_exposure"
    BROKEN_ACCESS_CONTROL = "broken_access_control"
    SECURITY_MISCONFIGURATION = "security_misconfiguration"
    INSECURE_DESERIALIZATION = "insecure_deserialization"
    INSUFFICIENT_LOGGING = "insufficient_logging"


class ReviewDimension(str, Enum):
    """Dimensions of review analysis."""
    
    SECURITY = "security"
    PRIVACY = "privacy"
    COMPLIANCE = "compliance"


class PrivacyCategory(str, Enum):
    """LINDDUN privacy threat categories."""
    
    # LINDDUN categories
    LINKING = "linking"  # Associating data to reveal identity
    IDENTIFYING = "identifying"  # Learning the identity of a data subject
    NON_REPUDIATION = "non_repudiation"  # Unable to deny actions (privacy context)
    DETECTING = "detecting"  # Deducing data subject involvement
    DATA_DISCLOSURE = "data_disclosure"  # Exposing personal data
    UNAWARENESS = "unawareness"  # Data subject not informed of processing
    NON_COMPLIANCE = "non_compliance"  # Violating data protection legislation
    
    # GDPR/CCPA principles
    DATA_MINIMIZATION = "data_minimization"
    PURPOSE_LIMITATION = "purpose_limitation"
    CONSENT_VIOLATION = "consent_violation"
    DATA_SUBJECT_RIGHTS = "data_subject_rights"
    CROSS_BORDER_TRANSFER = "cross_border_transfer"
    RETENTION_VIOLATION = "retention_violation"


class ComplianceCategory(str, Enum):
    """Compliance framework categories."""
    
    # SOC 2 Trust Service Criteria
    SOC2_SECURITY = "soc2_security"
    SOC2_AVAILABILITY = "soc2_availability"
    SOC2_PROCESSING_INTEGRITY = "soc2_processing_integrity"
    SOC2_CONFIDENTIALITY = "soc2_confidentiality"
    SOC2_PRIVACY = "soc2_privacy"
    
    # HIPAA
    HIPAA_PHI_HANDLING = "hipaa_phi_handling"
    HIPAA_ACCESS_CONTROL = "hipaa_access_control"
    HIPAA_AUDIT_LOGGING = "hipaa_audit_logging"
    HIPAA_ENCRYPTION = "hipaa_encryption"
    HIPAA_BAA_REQUIRED = "hipaa_baa_required"
    
    # PCI-DSS
    PCI_CARDHOLDER_DATA = "pci_cardholder_data"
    PCI_NETWORK_SECURITY = "pci_network_security"
    PCI_ACCESS_CONTROL = "pci_access_control"
    PCI_MONITORING = "pci_monitoring"
    PCI_SECURITY_POLICY = "pci_security_policy"
    
    # ISO 27001
    ISO_INFORMATION_SECURITY = "iso_information_security"
    ISO_ACCESS_MANAGEMENT = "iso_access_management"
    ISO_CRYPTOGRAPHY = "iso_cryptography"
    ISO_OPERATIONS_SECURITY = "iso_operations_security"
    ISO_INCIDENT_MANAGEMENT = "iso_incident_management"
    
    # General
    REGULATORY_VIOLATION = "regulatory_violation"
    POLICY_VIOLATION = "policy_violation"
    DOCUMENTATION_GAP = "documentation_gap"


class ComplianceFramework(str, Enum):
    """Supported compliance frameworks."""
    
    SOC2 = "soc2"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    ISO_27001 = "iso_27001"
    GDPR = "gdpr"
    CCPA = "ccpa"


@dataclass
class Entity:
    """
    A node in the context graph representing a security-relevant entity.
    
    Examples: User, API endpoint, Database, PII field, Auth provider
    """
    
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    entity_type: EntityType = EntityType.DATA
    description: str = ""
    properties: dict[str, Any] = field(default_factory=dict)
    source: str = ""  # Where this entity was discovered (file path, PRD section)
    
    # Security-relevant metadata
    is_sensitive: bool = False
    requires_auth: bool = False
    trust_level: int = 0  # 0 = untrusted, 10 = fully trusted
    
    def __hash__(self) -> int:
        return hash(self.id)
    
    def __eq__(self, other: object) -> bool:
        if isinstance(other, Entity):
            return self.id == other.id
        return False


@dataclass
class Relationship:
    """
    An edge in the context graph representing a relationship between entities.
    """
    
    id: UUID = field(default_factory=uuid4)
    source_id: UUID = field(default_factory=uuid4)
    target_id: UUID = field(default_factory=uuid4)
    relationship_type: RelationshipType = RelationshipType.FLOWS_TO
    properties: dict[str, Any] = field(default_factory=dict)
    
    # Security-relevant metadata
    crosses_trust_boundary: bool = False
    requires_encryption: bool = False
    
    def __hash__(self) -> int:
        return hash(self.id)


@dataclass
class Intent:
    """
    Structured representation of what the PRD intends to achieve.
    
    Extracted from product requirement documents.
    """
    
    id: UUID = field(default_factory=uuid4)
    title: str = ""
    summary: str = ""
    
    # Extracted elements
    features: list[str] = field(default_factory=list)
    user_stories: list[str] = field(default_factory=list)
    data_entities: list[Entity] = field(default_factory=list)
    api_changes: list[dict[str, Any]] = field(default_factory=list)
    
    # Security-relevant elements
    auth_requirements: list[str] = field(default_factory=list)
    data_sensitivity: list[str] = field(default_factory=list)
    external_integrations: list[str] = field(default_factory=list)
    
    # Metadata
    source_document: str = ""
    parsed_at: datetime = field(default_factory=datetime.now)
    raw_content: str = ""


@dataclass
class State:
    """
    Representation of the current codebase state.
    
    Maps security-relevant patterns in existing code.
    """
    
    id: UUID = field(default_factory=uuid4)
    codebase_path: str = ""
    analyzed_at: datetime = field(default_factory=datetime.now)
    
    # Discovered elements
    entities: list[Entity] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    
    # Code structure
    api_endpoints: list[dict[str, Any]] = field(default_factory=list)
    data_models: list[dict[str, Any]] = field(default_factory=list)
    auth_patterns: list[dict[str, Any]] = field(default_factory=list)
    
    # Security controls
    existing_controls: list[str] = field(default_factory=list)
    trust_boundaries: list[str] = field(default_factory=list)
    
    # Metrics
    files_analyzed: int = 0
    lines_of_code: int = 0


@dataclass
class Delta:
    """
    The difference between Intent and State.
    
    Represents what needs to be implemented and its security implications.
    """
    
    id: UUID = field(default_factory=uuid4)
    intent_id: UUID = field(default_factory=uuid4)
    state_id: UUID = field(default_factory=uuid4)
    
    # Changes
    new_entities: list[Entity] = field(default_factory=list)
    modified_entities: list[Entity] = field(default_factory=list)
    new_relationships: list[Relationship] = field(default_factory=list)
    
    # Impact analysis
    affected_components: list[str] = field(default_factory=list)
    new_trust_boundaries: list[str] = field(default_factory=list)
    expanded_attack_surface: list[str] = field(default_factory=list)
    
    # Summary
    summary: str = ""
    risk_score: float = 0.0


@dataclass
class SecurityFinding:
    """
    A security concern identified during review.
    """
    
    id: UUID = field(default_factory=uuid4)
    title: str = ""
    description: str = ""
    
    # Classification
    severity: Severity = Severity.MEDIUM
    category: ThreatCategory = ThreatCategory.INFO_DISCLOSURE
    dimension: ReviewDimension = ReviewDimension.SECURITY
    
    # Context
    affected_entities: list[UUID] = field(default_factory=list)
    affected_relationships: list[UUID] = field(default_factory=list)
    
    # Location
    source_type: str = ""  # "intent", "state", "delta", "pattern", "llm"
    source_reference: str = ""  # File path, PRD section, etc.
    
    # Remediation
    recommendation: str = ""
    mitigations: list[str] = field(default_factory=list)
    
    # Metadata
    confidence: float = 0.0  # 0.0 to 1.0
    found_at: datetime = field(default_factory=datetime.now)


@dataclass
class PrivacyFinding:
    """
    A privacy concern identified during review using LINDDUN framework.
    """
    
    id: UUID = field(default_factory=uuid4)
    title: str = ""
    description: str = ""
    
    # Classification
    severity: Severity = Severity.MEDIUM
    category: PrivacyCategory = PrivacyCategory.DATA_DISCLOSURE
    dimension: ReviewDimension = ReviewDimension.PRIVACY
    
    # LINDDUN-specific
    data_subjects: list[str] = field(default_factory=list)  # Affected data subjects
    personal_data_types: list[str] = field(default_factory=list)  # Types of PII involved
    processing_activities: list[str] = field(default_factory=list)  # What processing occurs
    
    # Context
    affected_entities: list[UUID] = field(default_factory=list)
    affected_relationships: list[UUID] = field(default_factory=list)
    
    # Location
    source_type: str = ""
    source_reference: str = ""
    
    # Regulatory context
    applicable_regulations: list[str] = field(default_factory=list)  # GDPR, CCPA, etc.
    legal_basis_required: bool = False
    consent_required: bool = False
    
    # Remediation
    recommendation: str = ""
    mitigations: list[str] = field(default_factory=list)
    
    # Metadata
    confidence: float = 0.0
    found_at: datetime = field(default_factory=datetime.now)


@dataclass
class ComplianceFinding:
    """
    A compliance concern identified during review.
    """
    
    id: UUID = field(default_factory=uuid4)
    title: str = ""
    description: str = ""
    
    # Classification
    severity: Severity = Severity.MEDIUM
    category: ComplianceCategory = ComplianceCategory.REGULATORY_VIOLATION
    dimension: ReviewDimension = ReviewDimension.COMPLIANCE
    framework: ComplianceFramework = ComplianceFramework.SOC2
    
    # Compliance-specific
    control_id: str = ""  # e.g., "CC6.1" for SOC2, "164.312(a)(1)" for HIPAA
    control_description: str = ""
    requirement_text: str = ""
    
    # Context
    affected_entities: list[UUID] = field(default_factory=list)
    affected_relationships: list[UUID] = field(default_factory=list)
    
    # Location
    source_type: str = ""
    source_reference: str = ""
    
    # Gap analysis
    current_state: str = ""  # What exists now
    required_state: str = ""  # What's needed for compliance
    gap_description: str = ""
    
    # Remediation
    recommendation: str = ""
    mitigations: list[str] = field(default_factory=list)
    remediation_effort: str = ""  # "low", "medium", "high"
    
    # Metadata
    confidence: float = 0.0
    found_at: datetime = field(default_factory=datetime.now)


@dataclass
class SecurityReview:
    """
    Complete security review output.
    """
    
    id: UUID = field(default_factory=uuid4)
    
    # Inputs
    intent: Intent = field(default_factory=Intent)
    state: State = field(default_factory=State)
    delta: Delta = field(default_factory=Delta)
    
    # Findings
    findings: list[SecurityFinding] = field(default_factory=list)
    
    # Summary
    executive_summary: str = ""
    risk_rating: str = ""
    
    # Metadata
    reviewed_at: datetime = field(default_factory=datetime.now)
    reviewer: str = "context-graph"
    
    @property
    def critical_findings(self) -> list[SecurityFinding]:
        return [f for f in self.findings if f.severity == Severity.CRITICAL]
    
    @property
    def high_findings(self) -> list[SecurityFinding]:
        return [f for f in self.findings if f.severity == Severity.HIGH]
    
    @property
    def findings_by_category(self) -> dict[ThreatCategory, list[SecurityFinding]]:
        result: dict[ThreatCategory, list[SecurityFinding]] = {}
        for finding in self.findings:
            if finding.category not in result:
                result[finding.category] = []
            result[finding.category].append(finding)
        return result

