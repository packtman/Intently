"""
Architecture Pattern Matcher - Analyze code for architectural concerns.

Evaluates:
- API design and contracts
- Service boundaries and dependencies
- Communication patterns
- Scalability and resilience
- Documentation (ADRs)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from context_graph.core.models import (
    ArchitectureFinding,
    ArchitectureCategory,
    Severity,
    State,
    Intent,
)
from context_graph.security.delta_analyzer import DeltaAnalysisResult


@dataclass
class ArchitecturePattern:
    """An architecture pattern to match against."""
    
    id: str
    name: str
    description: str
    category: ArchitectureCategory
    severity: Severity = Severity.MEDIUM
    
    # Matching conditions
    requires_new_api: bool = False
    requires_new_service: bool = False
    requires_external_integration: bool = False
    
    # Recommendations
    recommendation: str = ""
    mitigations: list[str] = field(default_factory=list)
    design_alternatives: list[str] = field(default_factory=list)


# Define architecture patterns
ARCHITECTURE_PATTERNS = [
    # API Design
    ArchitecturePattern(
        id="ARCH-001",
        name="Missing API Contract",
        description="New API endpoints lack formal contract definition (OpenAPI/GraphQL schema)",
        category=ArchitectureCategory.MISSING_API_CONTRACT,
        severity=Severity.MEDIUM,
        requires_new_api=True,
        recommendation="Define API contracts before implementation",
        mitigations=[
            "Create OpenAPI/Swagger specification",
            "Use contract-first development",
            "Generate client SDKs from spec",
        ],
        design_alternatives=[
            "OpenAPI 3.0 specification",
            "GraphQL schema",
            "AsyncAPI for event-driven APIs",
        ],
    ),
    ArchitecturePattern(
        id="ARCH-002",
        name="No API Versioning",
        description="APIs lack versioning strategy, risking breaking changes",
        category=ArchitectureCategory.NO_API_VERSIONING,
        severity=Severity.MEDIUM,
        requires_new_api=True,
        recommendation="Implement API versioning strategy",
        mitigations=[
            "Use URL path versioning (/v1/, /v2/)",
            "Consider header-based versioning",
            "Document deprecation policy",
        ],
        design_alternatives=[
            "URL path versioning",
            "Query parameter versioning",
            "Header versioning",
        ],
    ),
    ArchitecturePattern(
        id="ARCH-003",
        name="Potential Breaking Change",
        description="API changes may break existing clients",
        category=ArchitectureCategory.BREAKING_CHANGE,
        severity=Severity.HIGH,
        requires_new_api=True,
        recommendation="Ensure backward compatibility or use versioning",
        mitigations=[
            "Add new fields instead of modifying existing",
            "Create new endpoint version",
            "Provide migration guide for clients",
        ],
    ),
    
    # Service Design
    ArchitecturePattern(
        id="ARCH-010",
        name="Missing Service Boundary",
        description="New functionality may blur service boundaries",
        category=ArchitectureCategory.MISSING_SERVICE_BOUNDARY,
        severity=Severity.MEDIUM,
        requires_new_service=True,
        recommendation="Clearly define service boundaries and responsibilities",
        mitigations=[
            "Define bounded contexts",
            "Document service ownership",
            "Establish clear APIs between services",
        ],
        design_alternatives=[
            "Domain-driven design bounded contexts",
            "Microservices decomposition",
            "Module boundaries within monolith",
        ],
    ),
    ArchitecturePattern(
        id="ARCH-011",
        name="Distributed Monolith Risk",
        description="Services are tightly coupled, creating a distributed monolith",
        category=ArchitectureCategory.DISTRIBUTED_MONOLITH,
        severity=Severity.HIGH,
        recommendation="Reduce inter-service coupling",
        mitigations=[
            "Use event-driven communication",
            "Implement async messaging",
            "Define clear service contracts",
        ],
    ),
    
    # Data Architecture
    ArchitecturePattern(
        id="ARCH-020",
        name="Missing Data Model Documentation",
        description="Data models lack documentation or schema definition",
        category=ArchitectureCategory.MISSING_DATA_MODEL,
        severity=Severity.LOW,
        recommendation="Document data models and their relationships",
        mitigations=[
            "Create entity-relationship diagrams",
            "Document data ownership",
            "Define data validation rules",
        ],
    ),
    ArchitecturePattern(
        id="ARCH-021",
        name="No Data Validation",
        description="Data entities lack validation rules",
        category=ArchitectureCategory.NO_DATA_VALIDATION,
        severity=Severity.MEDIUM,
        recommendation="Implement data validation at all boundaries",
        mitigations=[
            "Add schema validation",
            "Implement input sanitization",
            "Use typed data models",
        ],
    ),
    
    # Dependency Management
    ArchitecturePattern(
        id="ARCH-030",
        name="Circular Dependency",
        description="Circular dependencies detected between modules/services",
        category=ArchitectureCategory.CIRCULAR_DEPENDENCY,
        severity=Severity.HIGH,
        recommendation="Break circular dependencies to improve maintainability",
        mitigations=[
            "Extract shared code to common module",
            "Use dependency inversion",
            "Introduce event-driven communication",
        ],
        design_alternatives=[
            "Event sourcing",
            "Shared kernel pattern",
            "Interface segregation",
        ],
    ),
    ArchitecturePattern(
        id="ARCH-031",
        name="Missing Dependency Lock",
        description="Project lacks dependency lock file",
        category=ArchitectureCategory.MISSING_DEPENDENCY_LOCK,
        severity=Severity.MEDIUM,
        recommendation="Add dependency lock file for reproducible builds",
        mitigations=[
            "Generate and commit lock file",
            "Pin dependency versions",
            "Use CI to verify lock file",
        ],
    ),
    ArchitecturePattern(
        id="ARCH-032",
        name="Too Many Dependencies",
        description="Project has excessive external dependencies",
        category=ArchitectureCategory.TOO_MANY_DEPENDENCIES,
        severity=Severity.LOW,
        recommendation="Review and reduce unnecessary dependencies",
        mitigations=[
            "Audit dependency tree",
            "Remove unused dependencies",
            "Consider bundling small utilities",
        ],
    ),
    
    # Communication Patterns
    ArchitecturePattern(
        id="ARCH-040",
        name="Missing Retry Logic",
        description="External calls lack retry logic for resilience",
        category=ArchitectureCategory.NO_RETRY_LOGIC,
        severity=Severity.MEDIUM,
        requires_external_integration=True,
        recommendation="Implement retry with exponential backoff",
        mitigations=[
            "Add retry with backoff",
            "Implement circuit breaker",
            "Add timeout handling",
        ],
    ),
    ArchitecturePattern(
        id="ARCH-041",
        name="Missing Circuit Breaker",
        description="External integrations lack circuit breaker pattern",
        category=ArchitectureCategory.MISSING_CIRCUIT_BREAKER,
        severity=Severity.MEDIUM,
        requires_external_integration=True,
        recommendation="Implement circuit breaker for external calls",
        mitigations=[
            "Add circuit breaker library",
            "Configure failure thresholds",
            "Implement fallback responses",
        ],
    ),
    ArchitecturePattern(
        id="ARCH-042",
        name="Synchronous Over Asynchronous",
        description="Using synchronous calls where async would be more appropriate",
        category=ArchitectureCategory.SYNC_OVER_ASYNC,
        severity=Severity.LOW,
        recommendation="Consider async patterns for non-blocking operations",
        mitigations=[
            "Use message queues for async processing",
            "Implement event-driven architecture",
            "Add async endpoints for long operations",
        ],
    ),
    ArchitecturePattern(
        id="ARCH-043",
        name="Missing Idempotency",
        description="APIs lack idempotency guarantees for safe retries",
        category=ArchitectureCategory.NO_IDEMPOTENCY,
        severity=Severity.MEDIUM,
        requires_new_api=True,
        recommendation="Implement idempotency for mutation endpoints",
        mitigations=[
            "Add idempotency keys",
            "Make operations naturally idempotent",
            "Track and deduplicate requests",
        ],
    ),
    
    # Documentation
    ArchitecturePattern(
        id="ARCH-050",
        name="Missing Architecture Decision Records",
        description="Significant decisions lack ADR documentation",
        category=ArchitectureCategory.MISSING_ADR,
        severity=Severity.LOW,
        recommendation="Document architecture decisions in ADRs",
        mitigations=[
            "Create ADR for this change",
            "Document alternatives considered",
            "Include decision rationale",
        ],
    ),
    ArchitecturePattern(
        id="ARCH-051",
        name="No System Diagram",
        description="System lacks architectural diagram",
        category=ArchitectureCategory.NO_SYSTEM_DIAGRAM,
        severity=Severity.LOW,
        recommendation="Create and maintain system architecture diagrams",
        mitigations=[
            "Create C4 model diagrams",
            "Document service interactions",
            "Include data flow diagrams",
        ],
    ),
    
    # Scalability
    ArchitecturePattern(
        id="ARCH-060",
        name="Single Point of Failure",
        description="Architecture contains single points of failure",
        category=ArchitectureCategory.SINGLE_POINT_OF_FAILURE,
        severity=Severity.HIGH,
        recommendation="Eliminate single points of failure",
        mitigations=[
            "Add redundancy for critical components",
            "Implement load balancing",
            "Design for horizontal scaling",
        ],
    ),
    ArchitecturePattern(
        id="ARCH-061",
        name="Stateful Service",
        description="Service maintains state that prevents horizontal scaling",
        category=ArchitectureCategory.STATEFUL_SERVICE,
        severity=Severity.MEDIUM,
        recommendation="Externalize state for better scalability",
        mitigations=[
            "Move state to external store",
            "Use distributed cache",
            "Implement sticky sessions if needed",
        ],
    ),
    
    # Resilience
    ArchitecturePattern(
        id="ARCH-070",
        name="No Failover Strategy",
        description="System lacks failover strategy for critical components",
        category=ArchitectureCategory.NO_FAILOVER,
        severity=Severity.HIGH,
        recommendation="Implement failover for critical paths",
        mitigations=[
            "Configure automatic failover",
            "Implement health checks",
            "Test failover scenarios",
        ],
    ),
    ArchitecturePattern(
        id="ARCH-071",
        name="Missing Fallback",
        description="External dependencies lack fallback behavior",
        category=ArchitectureCategory.MISSING_FALLBACK,
        severity=Severity.MEDIUM,
        requires_external_integration=True,
        recommendation="Implement graceful fallbacks",
        mitigations=[
            "Add cached responses as fallback",
            "Implement default behaviors",
            "Design for graceful degradation",
        ],
    ),
]


class ArchitecturePatternMatcher:
    """
    Match codebase against architecture patterns.
    
    Analyzes API design, service boundaries, dependencies, and resilience.
    """
    
    def __init__(self, patterns: list[ArchitecturePattern] | None = None) -> None:
        self.patterns = patterns or ARCHITECTURE_PATTERNS
    
    def match(
        self,
        delta_result: DeltaAnalysisResult,
        state: State | None = None,
        intent: Intent | None = None,
        architecture_metrics: dict[str, Any] | None = None,
    ) -> list[ArchitectureFinding]:
        """
        Match delta and state against architecture patterns.
        
        Args:
            delta_result: Delta analysis between intent and state
            state: Current codebase state
            intent: Intent from PRD
            architecture_metrics: Metrics from ArchitectureAnalyzer
            
        Returns:
            List of ArchitectureFindings
        """
        findings: list[ArchitectureFinding] = []
        
        metrics = architecture_metrics or {}
        
        # Analyze changes
        has_new_api = len(delta_result.new_endpoints) > 0
        has_new_service = len(delta_result.delta.new_entities) > 0
        has_external_integration = (
            intent and len(intent.external_integrations) > 0
        ) if intent else False
        
        # Check each pattern
        for pattern in self.patterns:
            if self._pattern_applies(pattern, has_new_api, has_new_service, has_external_integration):
                finding = self._check_pattern(pattern, delta_result, state, metrics, intent)
                if finding:
                    findings.append(finding)
        
        # Add findings based on metrics
        if metrics:
            findings.extend(self._analyze_metrics(metrics, delta_result))
        
        # Analyze API changes
        if has_new_api:
            findings.extend(self._analyze_api_changes(delta_result, state))
        
        return findings
    
    def _pattern_applies(
        self,
        pattern: ArchitecturePattern,
        has_new_api: bool,
        has_new_service: bool,
        has_external_integration: bool,
    ) -> bool:
        """Check if pattern conditions are met."""
        if pattern.requires_new_api and not has_new_api:
            return False
        if pattern.requires_new_service and not has_new_service:
            return False
        if pattern.requires_external_integration and not has_external_integration:
            return False
        return True
    
    def _check_pattern(
        self,
        pattern: ArchitecturePattern,
        delta_result: DeltaAnalysisResult,
        state: State | None,
        metrics: dict[str, Any],
        intent: Intent | None,
    ) -> ArchitectureFinding | None:
        """Check if a pattern matches and create finding."""
        
        # Pattern-specific checks
        if pattern.category == ArchitectureCategory.MISSING_API_CONTRACT:
            api_contracts = metrics.get("api_contracts", 0)
            if api_contracts > 0:
                return None
        
        elif pattern.category == ArchitectureCategory.CIRCULAR_DEPENDENCY:
            if metrics.get("circular_dependency_risk", 0) == 0:
                return None
        
        elif pattern.category == ArchitectureCategory.MISSING_DEPENDENCY_LOCK:
            if metrics.get("has_dependency_lock", True):
                return None
        
        elif pattern.category == ArchitectureCategory.MISSING_ADR:
            if metrics.get("adrs_found", 0) > 0:
                return None
        
        elif pattern.category == ArchitectureCategory.TOO_MANY_DEPENDENCIES:
            if metrics.get("external_dependencies", 0) < 50:
                return None
        
        # Check if we should create finding
        if self._should_create_finding(pattern, delta_result, state, metrics):
            return self._create_finding(pattern, delta_result, metrics, intent)
        
        return None
    
    def _should_create_finding(
        self,
        pattern: ArchitecturePattern,
        delta_result: DeltaAnalysisResult,
        state: State | None,
        metrics: dict[str, Any],
    ) -> bool:
        """Determine if we should create a finding for this pattern."""
        category = pattern.category
        
        # API Design
        if category == ArchitectureCategory.MISSING_API_CONTRACT:
            return (
                len(delta_result.new_endpoints) > 0 and
                metrics.get("api_contracts", 0) == 0
            )
        
        if category == ArchitectureCategory.NO_API_VERSIONING:
            # Check if any endpoints have versioning
            for endpoint in delta_result.new_endpoints:
                path = endpoint.get("path", "")
                if "/v1" in path or "/v2" in path or "version" in path.lower():
                    return False
            return len(delta_result.new_endpoints) > 0
        
        # Dependency
        if category == ArchitectureCategory.CIRCULAR_DEPENDENCY:
            return metrics.get("circular_dependency_risk", 0) > 0
        
        if category == ArchitectureCategory.MISSING_DEPENDENCY_LOCK:
            return not metrics.get("has_dependency_lock", True)
        
        # Documentation
        if category == ArchitectureCategory.MISSING_ADR:
            return metrics.get("adrs_found", 0) == 0
        
        # Resilience patterns - check if external integrations exist
        if category in [
            ArchitectureCategory.NO_RETRY_LOGIC,
            ArchitectureCategory.MISSING_CIRCUIT_BREAKER,
            ArchitectureCategory.MISSING_FALLBACK,
        ]:
            # Check for resilience patterns in existing controls
            if state:
                controls = state.existing_controls
                if category == ArchitectureCategory.NO_RETRY_LOGIC:
                    return "retry_configuration" not in controls
                if category == ArchitectureCategory.MISSING_CIRCUIT_BREAKER:
                    return not any("circuit" in c.lower() for c in controls)
            return True
        
        return True
    
    def _create_finding(
        self,
        pattern: ArchitecturePattern,
        delta_result: DeltaAnalysisResult,
        metrics: dict[str, Any],
        intent: Intent | None,
    ) -> ArchitectureFinding:
        """Create an architecture finding from a matched pattern."""
        finding = ArchitectureFinding(
            id=uuid4(),
            title=pattern.name,
            description=pattern.description,
            severity=pattern.severity,
            category=pattern.category,
            recommendation=pattern.recommendation,
            mitigations=pattern.mitigations.copy(),
            design_alternatives=pattern.design_alternatives.copy(),
            source_type="pattern",
            source_reference=pattern.id,
            confidence=0.75,
        )
        
        # Add context
        if pattern.requires_new_api:
            finding.affected_apis = [
                ep.get("path", "unknown") for ep in delta_result.new_endpoints[:5]
            ]
        
        if pattern.category == ArchitectureCategory.CIRCULAR_DEPENDENCY:
            finding.is_circular_dependency = True
        
        if metrics.get("architectural_patterns"):
            finding.architectural_pattern = ", ".join(metrics["architectural_patterns"][:3])
        
        if metrics.get("services_identified"):
            finding.affected_services = metrics.get("discovered_services", [])[:5]
        
        return finding
    
    def _analyze_metrics(
        self,
        metrics: dict[str, Any],
        delta_result: DeltaAnalysisResult,
    ) -> list[ArchitectureFinding]:
        """Generate findings from architecture metrics."""
        findings: list[ArchitectureFinding] = []
        
        # Check for high coupling
        internal_deps = metrics.get("internal_dependencies", 0)
        if internal_deps > 100:
            findings.append(ArchitectureFinding(
                id=uuid4(),
                title="High Internal Coupling",
                description=f"Codebase has {internal_deps} internal dependencies indicating tight coupling",
                severity=Severity.MEDIUM,
                category=ArchitectureCategory.MONOLITH_COUPLING,
                coupling_score=min(1.0, internal_deps / 200),
                recommendation="Consider reducing coupling between modules",
                mitigations=[
                    "Extract shared interfaces",
                    "Use dependency injection",
                    "Apply interface segregation principle",
                ],
                source_type="metrics",
                confidence=0.7,
            ))
        
        # Check architectural patterns
        patterns = metrics.get("architectural_patterns", [])
        if "event_driven" in patterns and "graphql" not in patterns and "grpc_services" not in patterns:
            if metrics.get("api_contracts", 0) == 0:
                findings.append(ArchitectureFinding(
                    id=uuid4(),
                    title="Event-Driven Without Schema",
                    description="Event-driven architecture detected but no event schema documentation found",
                    severity=Severity.MEDIUM,
                    category=ArchitectureCategory.MISSING_API_CONTRACT,
                    architectural_pattern="event_driven",
                    recommendation="Define event schemas using AsyncAPI or similar",
                    mitigations=[
                        "Create AsyncAPI specification",
                        "Document event payload schemas",
                        "Version event schemas",
                    ],
                    source_type="metrics",
                    confidence=0.65,
                ))
        
        return findings
    
    def _analyze_api_changes(
        self,
        delta_result: DeltaAnalysisResult,
        state: State | None,
    ) -> list[ArchitectureFinding]:
        """Analyze API changes for architectural concerns."""
        findings: list[ArchitectureFinding] = []
        
        # Check for potentially breaking changes
        for endpoint in delta_result.modified_endpoints:
            # If modifying existing endpoints, flag potential breaking change
            findings.append(ArchitectureFinding(
                id=uuid4(),
                title="API Modification - Potential Breaking Change",
                description=f"Modifying endpoint {endpoint.get('path', 'unknown')} may affect existing clients",
                severity=Severity.MEDIUM,
                category=ArchitectureCategory.BREAKING_CHANGE,
                affected_apis=[endpoint.get("path", "unknown")],
                breaking_change=True,
                recommendation="Verify backward compatibility or use API versioning",
                mitigations=[
                    "Add new fields instead of modifying existing",
                    "Create new endpoint version",
                    "Communicate changes to API consumers",
                ],
                source_type="delta",
                confidence=0.6,
            ))
        
        return findings

