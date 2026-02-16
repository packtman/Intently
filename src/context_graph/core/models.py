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
from typing import Any, Union
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
    ENGINEERING = "engineering"
    ARCHITECTURE = "architecture"


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


class EngineeringCategory(str, Enum):
    """Engineering review categories."""
    
    # Code Quality
    HIGH_COMPLEXITY = "high_complexity"
    DEEP_NESTING = "deep_nesting"
    LONG_FUNCTIONS = "long_functions"
    LARGE_FILES = "large_files"
    CODE_DUPLICATION = "code_duplication"
    
    # Technical Debt
    TODO_FIXME = "todo_fixme"
    DEPRECATED_CODE = "deprecated_code"
    MAGIC_NUMBERS = "magic_numbers"
    MISSING_ERROR_HANDLING = "missing_error_handling"
    
    # Testing
    LOW_TEST_COVERAGE = "low_test_coverage"
    MISSING_TESTS = "missing_tests"
    FLAKY_TESTS = "flaky_tests"
    
    # Documentation
    MISSING_DOCUMENTATION = "missing_documentation"
    OUTDATED_DOCUMENTATION = "outdated_documentation"
    
    # Maintainability
    TIGHT_COUPLING = "tight_coupling"
    CIRCULAR_DEPENDENCIES = "circular_dependencies"
    MISSING_TYPE_HINTS = "missing_type_hints"
    
    # Observability
    INSUFFICIENT_LOGGING = "insufficient_logging"
    MISSING_METRICS = "missing_metrics"
    NO_HEALTH_CHECKS = "no_health_checks"
    
    # CI/CD
    NO_CI_CD = "no_ci_cd"
    NO_LINTING = "no_linting"
    NO_AUTOMATED_TESTS = "no_automated_tests"


class ArchitectureCategory(str, Enum):
    """Architecture review categories."""
    
    # API Design
    MISSING_API_CONTRACT = "missing_api_contract"
    INCONSISTENT_API = "inconsistent_api"
    NO_API_VERSIONING = "no_api_versioning"
    BREAKING_CHANGE = "breaking_change"
    
    # Service Design
    MISSING_SERVICE_BOUNDARY = "missing_service_boundary"
    MONOLITH_COUPLING = "monolith_coupling"
    DISTRIBUTED_MONOLITH = "distributed_monolith"
    NO_SERVICE_MESH = "no_service_mesh"
    
    # Data Architecture
    MISSING_DATA_MODEL = "missing_data_model"
    DATA_INCONSISTENCY = "data_inconsistency"
    NO_DATA_VALIDATION = "no_data_validation"
    SCHEMA_DRIFT = "schema_drift"
    
    # Dependency Management
    CIRCULAR_DEPENDENCY = "circular_dependency"
    MISSING_DEPENDENCY_LOCK = "missing_dependency_lock"
    OUTDATED_DEPENDENCIES = "outdated_dependencies"
    TOO_MANY_DEPENDENCIES = "too_many_dependencies"
    
    # Communication Patterns
    NO_RETRY_LOGIC = "no_retry_logic"
    MISSING_CIRCUIT_BREAKER = "missing_circuit_breaker"
    SYNC_OVER_ASYNC = "sync_over_async"
    NO_IDEMPOTENCY = "no_idempotency"
    
    # Documentation
    MISSING_ADR = "missing_adr"
    OUTDATED_ARCHITECTURE_DOCS = "outdated_architecture_docs"
    NO_SYSTEM_DIAGRAM = "no_system_diagram"
    
    # Scalability
    SINGLE_POINT_OF_FAILURE = "single_point_of_failure"
    NO_HORIZONTAL_SCALING = "no_horizontal_scaling"
    STATEFUL_SERVICE = "stateful_service"
    
    # Resilience
    NO_FAILOVER = "no_failover"
    MISSING_FALLBACK = "missing_fallback"
    NO_GRACEFUL_DEGRADATION = "no_graceful_degradation"


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
    
    # Collaboration fields (optional, for team validation workflow)
    # These are populated by the API layer when collaboration features are enabled
    validation_status: str = "pending"  # pending, validated, rejected, needs_discussion, accepted_risk, deferred
    validated_by: str | None = None
    validated_at: datetime | None = None
    validation_notes: str | None = None
    assigned_team: str | None = None
    assigned_user: str | None = None
    comment_count: int = 0


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
    
    # Collaboration fields (optional, for team validation workflow)
    validation_status: str = "pending"
    validated_by: str | None = None
    validated_at: datetime | None = None
    validation_notes: str | None = None
    assigned_team: str | None = None
    assigned_user: str | None = None
    comment_count: int = 0


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
    
    # Collaboration fields (optional, for team validation workflow)
    validation_status: str = "pending"
    validated_by: str | None = None
    validated_at: datetime | None = None
    validation_notes: str | None = None
    assigned_team: str | None = None
    assigned_user: str | None = None
    comment_count: int = 0


@dataclass
class EngineeringFinding:
    """
    An engineering concern identified during review.
    
    Covers code quality, technical debt, testing, and maintainability.
    """
    
    id: UUID = field(default_factory=uuid4)
    title: str = ""
    description: str = ""
    
    # Classification
    severity: Severity = Severity.MEDIUM
    category: EngineeringCategory = EngineeringCategory.HIGH_COMPLEXITY
    dimension: ReviewDimension = ReviewDimension.ENGINEERING
    
    # Engineering-specific metrics
    complexity_score: int = 0  # 0-100, higher = more complex
    estimated_effort: str = ""  # "trivial", "low", "medium", "high", "very_high"
    estimated_days: str = ""  # e.g., "1-2 days", "1-2 weeks"
    
    # Affected code
    affected_files: list[str] = field(default_factory=list)
    affected_functions: list[str] = field(default_factory=list)
    lines_of_code_affected: int = 0
    
    # Technical debt indicators
    tech_debt_items: int = 0  # TODOs, FIXMEs, etc.
    test_coverage_gap: float = 0.0  # 0.0 to 1.0
    
    # Context
    affected_entities: list[UUID] = field(default_factory=list)
    affected_relationships: list[UUID] = field(default_factory=list)
    
    # Location
    source_type: str = ""
    source_reference: str = ""
    
    # Remediation
    recommendation: str = ""
    mitigations: list[str] = field(default_factory=list)
    refactoring_suggestions: list[str] = field(default_factory=list)
    
    # Metadata
    confidence: float = 0.0
    found_at: datetime = field(default_factory=datetime.now)
    
    # Collaboration fields (optional, for team validation workflow)
    validation_status: str = "pending"
    validated_by: str | None = None
    validated_at: datetime | None = None
    validation_notes: str | None = None
    assigned_team: str | None = None
    assigned_user: str | None = None
    comment_count: int = 0


@dataclass
class ArchitectureFinding:
    """
    An architecture concern identified during review.
    
    Covers API design, service boundaries, dependencies, and system design.
    """
    
    id: UUID = field(default_factory=uuid4)
    title: str = ""
    description: str = ""
    
    # Classification
    severity: Severity = Severity.MEDIUM
    category: ArchitectureCategory = ArchitectureCategory.MISSING_API_CONTRACT
    dimension: ReviewDimension = ReviewDimension.ARCHITECTURE
    
    # Architecture-specific
    architectural_pattern: str = ""  # e.g., "microservices", "monolith", "event-driven"
    affected_services: list[str] = field(default_factory=list)
    affected_apis: list[str] = field(default_factory=list)
    
    # Dependency analysis
    dependency_chain: list[str] = field(default_factory=list)
    is_circular_dependency: bool = False
    coupling_score: float = 0.0  # 0.0 (loose) to 1.0 (tight)
    
    # Impact assessment
    breaking_change: bool = False
    backward_compatible: bool = True
    migration_required: bool = False
    downstream_impact: list[str] = field(default_factory=list)
    upstream_dependencies: list[str] = field(default_factory=list)
    
    # Context
    affected_entities: list[UUID] = field(default_factory=list)
    affected_relationships: list[UUID] = field(default_factory=list)
    
    # Location
    source_type: str = ""
    source_reference: str = ""
    
    # Remediation
    recommendation: str = ""
    mitigations: list[str] = field(default_factory=list)
    design_alternatives: list[str] = field(default_factory=list)
    
    # Metadata
    confidence: float = 0.0
    found_at: datetime = field(default_factory=datetime.now)
    
    # Collaboration fields (optional, for team validation workflow)
    validation_status: str = "pending"
    validated_by: str | None = None
    validated_at: datetime | None = None
    validation_notes: str | None = None
    assigned_team: str | None = None
    assigned_user: str | None = None
    comment_count: int = 0


# Type alias for any finding type
Finding = Union[SecurityFinding, PrivacyFinding, ComplianceFinding, EngineeringFinding, ArchitectureFinding]


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


# ==================== PM-Focused Models (Unified PM Tool) ====================

@dataclass
class CodeEvidence:
    """Code evidence that grounds a prediction."""
    file_path: str
    line_number: int | None = None
    code_snippet: str = ""
    context: str = ""  # Additional context about why this is relevant


@dataclass
class DiffHunk:
    """A single hunk of a diff, for precise rendering."""
    operation: str  # "add", "remove", "context"
    content: str
    line_number: int | None = None  # Line in original PRD


@dataclass
class PRDChange:
    """A suggested change to the PRD, displayed as a diff."""
    id: UUID = field(default_factory=uuid4)
    prediction_id: UUID = field(default_factory=uuid4)  # Links to the prediction that generated this
    
    # Location in PRD
    section: str = ""  # "## Technical Requirements", "## Security", etc.
    start_line: int = 0
    end_line: int = 0
    
    # Diff content
    change_type: str = "addition"  # "addition", "modification", "restructure"
    current_text: str = ""  # What's currently in the PRD (shown in red if modified)
    suggested_text: str = ""  # What it should become (shown in green)
    
    # For rendering the diff
    diff_hunks: list[DiffHunk] = field(default_factory=list)
    
    # Metadata
    reasoning: str = ""  # Why this change is needed
    applied_at: datetime | None = None
    status: str = "open"  # "open", "accepted", "rejected", "dismissed"
    
    # Edit tracking (when PM modifies suggestion before accepting)
    original_suggested_text: str | None = None  # AI's original, if PM edited
    edited_by_pm: bool = False
    edit_history: list[str] = field(default_factory=list)  # Track PM iterations


@dataclass
class PredictedQuestion:
    """A question a team is likely to ask."""
    id: UUID = field(default_factory=uuid4)
    question: str = ""
    team: str = ""  # "engineering", "security", "privacy", "infra"
    severity: str = "likely"  # "blocker", "likely", "possible"
    
    # Code-grounded reasoning
    reasoning: str = ""
    code_evidence: list[CodeEvidence] = field(default_factory=list)
    
    # Suggested PRD change (diff-style)
    suggested_change: PRDChange | None = None
    
    # Status
    status: str = "open"  # "open", "accepted", "rejected", "dismissed", "asked_expert"
    
    # Expert assist (if used)
    expert_ask_id: UUID | None = None


@dataclass
class ExpertResponse:
    """Expert's lightweight response - one click + optional note."""
    verdict: str = ""  # "correct", "wrong", "partially_right"
    note: str | None = None  # Optional context
    
    # For pattern learning
    correct_answer: str | None = None  # What should the prediction have said?
    should_learn: bool = True  # Should this train future predictions?
    responded_at: datetime = field(default_factory=datetime.now)


@dataclass
class ExpertAsk:
    """A quick ask to a specific expert - NOT a ticket."""
    id: UUID = field(default_factory=uuid4)
    prediction_id: UUID = field(default_factory=uuid4)  # Which prediction this relates to
    
    # Who's asking
    pm_id: str = ""
    pm_name: str = ""
    
    # Who's being asked (specific person, not team)
    expert_id: str = ""
    expert_name: str = ""
    expert_domain: str = ""  # "security", "devops", etc.
    
    # The question (usually pre-filled from prediction)
    question: str = ""
    
    # Response (if received)
    response: ExpertResponse | None = None
    
    # Timestamps
    asked_at: datetime = field(default_factory=datetime.now)
    responded_at: datetime | None = None


@dataclass
class LearnedPattern:
    """A pattern learned from expert feedback."""
    id: UUID = field(default_factory=uuid4)
    
    # What we learned
    pattern_description: str = ""
    applies_when: str = ""  # Conditions for this pattern
    correction: str = ""  # What to say instead
    
    # Source
    learned_from: list[UUID] = field(default_factory=list)  # Expert response IDs
    times_applied: int = 0
    
    # Validation
    accuracy_score: float = 0.0  # How often experts agree with this pattern
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class FalsePositiveFilterStats:
    """Statistics from the false positive filtering pipeline."""
    
    dimension: str = ""
    original_count: int = 0
    final_count: int = 0
    total_removed: int = 0
    total_downgraded: int = 0
    total_iterations: int = 0
    removal_rate: float = 0.0
    iteration_details: list[dict[str, Any]] = field(default_factory=list)
    removed_findings: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class PRDQualityScore:
    """PRD quality assessment."""
    score: float = 0.0  # 0-100
    grade: str = "F"  # A, B, C, D, F
    gaps: list[str] = field(default_factory=list)
    predicted_pushback: int = 0  # Number of questions teams will likely ask
    blockers: int = 0  # Number of blocker-level questions
    likely_questions: int = 0
    possible_questions: int = 0


@dataclass
class EffortEstimation:
    """Code-grounded effort estimation."""
    total_days: dict[str, int] = field(default_factory=lambda: {"min": 0, "likely": 0, "max": 0})
    by_requirement: list[dict[str, Any]] = field(default_factory=list)
    codebase_support: float = 0.0  # 0-100, percentage of patterns that exist
    tldr: str = ""  # Human-readable summary


# ==================== Side-by-Side Diff Models ====================

@dataclass
class WordChange:
    """A word-level change within a line."""
    start: int  # Start character index
    end: int  # End character index
    change_type: str  # "added", "removed"


@dataclass
class DiffLine:
    """A single line in the side-by-side diff view."""
    line_number: int | None = None
    content: str = ""
    status: str = "unchanged"  # "unchanged", "deleted", "added", "modified", "empty"
    word_changes: list[WordChange] = field(default_factory=list)


@dataclass
class DiffStats:
    """Statistics about a diff."""
    lines_added: int = 0
    lines_removed: int = 0
    lines_modified: int = 0


@dataclass
class SideBySideDiff:
    """Side-by-side diff representation for UI rendering."""
    change_id: str = ""
    file_name: str = ""
    section: str = ""
    original_lines: list[DiffLine] = field(default_factory=list)
    suggested_lines: list[DiffLine] = field(default_factory=list)
    stats: DiffStats = field(default_factory=DiffStats)


@dataclass
class PRDFileInfo:
    """Information about the PRD file being analyzed."""
    file_path: str = ""  # Full path to the PRD file
    file_name: str = ""  # Just the filename
    original_content: str = ""  # Original content when loaded
    current_content: str = ""  # Current content (with accepted changes)
    backup_path: str | None = None  # Path to backup file if created
    last_saved_at: datetime | None = None

