"""
Analysis Categories - Define categories for iterative analysis across all review types.

Each analysis type has specific categories that should be covered.
The iterative analyzer uses these to track coverage and request continuation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AnalysisTypeCategories(str, Enum):
    """Analysis types that support iterative generation."""
    
    SECURITY = "security"
    PRIVACY = "privacy"
    COMPLIANCE = "compliance"
    ENGINEERING = "engineering"
    ARCHITECTURE = "architecture"
    THREAT_MODEL = "threat_model"


@dataclass
class CategoryConfig:
    """Configuration for a specific category within an analysis type."""
    
    id: str
    name: str
    description: str
    keywords: list[str] = field(default_factory=list)  # Keywords to detect coverage
    priority: int = 1  # 1=highest, 3=lowest


@dataclass
class IterativeAnalysisConfig:
    """Configuration for iterative analysis of a specific type."""
    
    analysis_type: AnalysisTypeCategories
    categories: list[CategoryConfig]
    max_rounds: int = 5
    min_findings_per_round: int = 2
    enabled: bool = True
    
    # Stopping conditions
    max_uncovered_categories_to_stop: int = 2  # Stop if <=N categories uncovered
    stop_on_no_new_findings: bool = True
    
    def get_category_names(self) -> list[str]:
        """Get list of category names."""
        return [c.name for c in self.categories]
    
    def get_category_keywords(self) -> dict[str, list[str]]:
        """Get mapping of category name to keywords."""
        return {c.name: c.keywords for c in self.categories}


# ==================== Security Review Categories ====================

SECURITY_CATEGORIES = [
    CategoryConfig(
        id="auth",
        name="Authentication/Identity",
        description="Authentication mechanisms, identity verification, credential handling",
        keywords=["authentication", "auth", "identity", "login", "credential", "password", "mfa", "2fa", "sso", "session", "token"],
        priority=1,
    ),
    CategoryConfig(
        id="authz",
        name="Authorization/Access Control",
        description="Authorization, access control, permissions, RBAC",
        keywords=["authorization", "access control", "permission", "rbac", "role", "privilege", "acl", "policy"],
        priority=1,
    ),
    CategoryConfig(
        id="input",
        name="Input Validation/Injection",
        description="Input validation, sanitization, injection attacks",
        keywords=["input validation", "injection", "sql injection", "xss", "sanitize", "escape", "validate"],
        priority=1,
    ),
    CategoryConfig(
        id="data_protection",
        name="Data Protection/Cryptography",
        description="Encryption, key management, data at rest/transit protection",
        keywords=["encryption", "crypto", "key management", "tls", "ssl", "hash", "decrypt", "secret"],
        priority=1,
    ),
    CategoryConfig(
        id="session",
        name="Session Management",
        description="Session handling, cookies, token management",
        keywords=["session", "cookie", "jwt", "token", "logout", "expiry", "refresh token"],
        priority=2,
    ),
    CategoryConfig(
        id="error",
        name="Error Handling/Information Leakage",
        description="Error handling, stack traces, information disclosure",
        keywords=["error handling", "exception", "stack trace", "debug", "verbose", "information disclosure", "leak"],
        priority=2,
    ),
    CategoryConfig(
        id="logging",
        name="Logging/Audit",
        description="Security logging, audit trails, monitoring",
        keywords=["logging", "audit", "monitor", "trace", "log", "event", "security log"],
        priority=2,
    ),
    CategoryConfig(
        id="api",
        name="API Security",
        description="API authentication, rate limiting, CORS, CSRF",
        keywords=["api", "rate limit", "cors", "csrf", "api key", "endpoint", "rest", "graphql"],
        priority=2,
    ),
    CategoryConfig(
        id="business_logic",
        name="Business Logic",
        description="Business logic flaws, workflow bypass, race conditions",
        keywords=["business logic", "workflow", "bypass", "race condition", "toctou", "state", "order"],
        priority=2,
    ),
    CategoryConfig(
        id="supply_chain",
        name="Third-Party/Supply Chain",
        description="Third-party dependencies, external integrations, supply chain risks",
        keywords=["third party", "dependency", "library", "external", "integration", "vendor", "supply chain"],
        priority=3,
    ),
]

SECURITY_ANALYSIS_CONFIG = IterativeAnalysisConfig(
    analysis_type=AnalysisTypeCategories.SECURITY,
    categories=SECURITY_CATEGORIES,
    max_rounds=5,
    min_findings_per_round=2,
)


# ==================== Privacy Review Categories (LINDDUN) ====================

PRIVACY_CATEGORIES = [
    CategoryConfig(
        id="linking",
        name="Linking",
        description="Data can be linked to reveal identity or sensitive patterns",
        keywords=["linking", "correlation", "profile", "combine", "aggregate", "track"],
        priority=1,
    ),
    CategoryConfig(
        id="identifying",
        name="Identifying",
        description="Individuals can be identified from data",
        keywords=["identifying", "identity", "personal", "pii", "name", "email", "phone", "ssn"],
        priority=1,
    ),
    CategoryConfig(
        id="non_repudiation",
        name="Non-Repudiation (Privacy)",
        description="Users cannot deny actions - privacy concern with excessive logging",
        keywords=["non-repudiation", "logging", "audit", "trace", "action log"],
        priority=2,
    ),
    CategoryConfig(
        id="detecting",
        name="Detecting",
        description="User behavior/patterns can be detected",
        keywords=["detecting", "behavior", "pattern", "activity", "usage", "browsing"],
        priority=2,
    ),
    CategoryConfig(
        id="data_disclosure",
        name="Data Disclosure",
        description="Unauthorized personal data exposure",
        keywords=["disclosure", "exposure", "leak", "breach", "unauthorized access"],
        priority=1,
    ),
    CategoryConfig(
        id="unawareness",
        name="Unawareness",
        description="Users not informed about data processing",
        keywords=["unawareness", "notice", "consent", "inform", "transparency", "policy"],
        priority=2,
    ),
    CategoryConfig(
        id="non_compliance",
        name="Non-Compliance",
        description="Violations of data protection laws/regulations",
        keywords=["compliance", "gdpr", "ccpa", "regulation", "legal", "lawful"],
        priority=1,
    ),
    CategoryConfig(
        id="data_minimization",
        name="Data Minimization",
        description="Collecting more data than necessary",
        keywords=["minimization", "excessive", "unnecessary", "collect", "purpose"],
        priority=2,
    ),
    CategoryConfig(
        id="retention",
        name="Retention/Deletion",
        description="Data kept longer than necessary, deletion issues",
        keywords=["retention", "deletion", "erasure", "forget", "right to be forgotten"],
        priority=2,
    ),
    CategoryConfig(
        id="cross_border",
        name="Cross-Border Transfer",
        description="International data transfers without safeguards",
        keywords=["transfer", "international", "cross-border", "eu", "schrems"],
        priority=3,
    ),
]

PRIVACY_ANALYSIS_CONFIG = IterativeAnalysisConfig(
    analysis_type=AnalysisTypeCategories.PRIVACY,
    categories=PRIVACY_CATEGORIES,
    max_rounds=4,
    min_findings_per_round=2,
)


# ==================== Compliance Review Categories ====================

COMPLIANCE_CATEGORIES = [
    CategoryConfig(
        id="access_control",
        name="Access Control",
        description="SOC2 CC6, HIPAA 164.312(a), PCI Req 7-9",
        keywords=["access control", "authentication", "authorization", "cc6", "164.312", "req 7", "req 8"],
        priority=1,
    ),
    CategoryConfig(
        id="data_protection",
        name="Data Protection",
        description="SOC2 C1, HIPAA Technical, PCI Req 3-4",
        keywords=["data protection", "encryption", "confidentiality", "c1", "req 3", "req 4"],
        priority=1,
    ),
    CategoryConfig(
        id="audit_logging",
        name="Audit Logging",
        description="SOC2 CC7, HIPAA 164.312(b), PCI Req 10",
        keywords=["audit", "logging", "monitoring", "cc7", "164.312(b)", "req 10"],
        priority=1,
    ),
    CategoryConfig(
        id="incident_response",
        name="Incident Response",
        description="SOC2 CC7, HIPAA 164.308",
        keywords=["incident", "response", "breach", "notification", "cc7"],
        priority=2,
    ),
    CategoryConfig(
        id="availability",
        name="Availability/Continuity",
        description="SOC2 A1, Business continuity, DR",
        keywords=["availability", "continuity", "disaster", "recovery", "a1", "dr", "backup"],
        priority=2,
    ),
    CategoryConfig(
        id="vulnerability_mgmt",
        name="Vulnerability Management",
        description="PCI Req 5-6, 11, ISO 27001 A.8.8",
        keywords=["vulnerability", "patch", "scan", "penetration", "req 5", "req 6", "req 11"],
        priority=2,
    ),
    CategoryConfig(
        id="network_security",
        name="Network Security",
        description="PCI Req 1-2, Network segmentation",
        keywords=["network", "firewall", "segmentation", "req 1", "req 2"],
        priority=2,
    ),
    CategoryConfig(
        id="phi_handling",
        name="PHI Handling (HIPAA)",
        description="HIPAA-specific PHI safeguards",
        keywords=["phi", "ephi", "health", "hipaa", "safeguard"],
        priority=1,
    ),
    CategoryConfig(
        id="pci_cardholder",
        name="Cardholder Data (PCI)",
        description="PCI-specific cardholder data requirements",
        keywords=["cardholder", "pan", "card", "pci", "payment"],
        priority=1,
    ),
]

COMPLIANCE_ANALYSIS_CONFIG = IterativeAnalysisConfig(
    analysis_type=AnalysisTypeCategories.COMPLIANCE,
    categories=COMPLIANCE_CATEGORIES,
    max_rounds=4,
    min_findings_per_round=2,
)


# ==================== Engineering Review Categories ====================

ENGINEERING_CATEGORIES = [
    CategoryConfig(
        id="complexity",
        name="Code Complexity",
        description="Cyclomatic complexity, nesting depth, function size",
        keywords=["complexity", "cyclomatic", "nesting", "function length", "cognitive"],
        priority=1,
    ),
    CategoryConfig(
        id="tech_debt",
        name="Technical Debt",
        description="TODOs, FIXMEs, code smells, duplication",
        keywords=["technical debt", "todo", "fixme", "hack", "smell", "duplication"],
        priority=2,
    ),
    CategoryConfig(
        id="test_coverage",
        name="Test Coverage",
        description="Unit tests, integration tests, coverage gaps",
        keywords=["test", "coverage", "unit test", "integration", "e2e"],
        priority=1,
    ),
    CategoryConfig(
        id="documentation",
        name="Documentation",
        description="Code documentation, API docs, README",
        keywords=["documentation", "docstring", "comment", "readme", "api doc"],
        priority=3,
    ),
    CategoryConfig(
        id="maintainability",
        name="Maintainability",
        description="Code organization, modularity, coupling",
        keywords=["maintainability", "modular", "coupling", "cohesion", "dependency"],
        priority=2,
    ),
    CategoryConfig(
        id="performance",
        name="Performance Concerns",
        description="Performance bottlenecks, inefficiencies",
        keywords=["performance", "bottleneck", "slow", "inefficient", "optimize"],
        priority=2,
    ),
    CategoryConfig(
        id="scalability",
        name="Scalability",
        description="Horizontal scaling, resource usage, limits",
        keywords=["scalability", "scale", "resource", "memory", "cpu", "limit"],
        priority=2,
    ),
    CategoryConfig(
        id="feasibility",
        name="Implementation Feasibility",
        description="Blockers, risks, dependencies",
        keywords=["feasibility", "blocker", "risk", "dependency", "prerequisite"],
        priority=1,
    ),
]

ENGINEERING_ANALYSIS_CONFIG = IterativeAnalysisConfig(
    analysis_type=AnalysisTypeCategories.ENGINEERING,
    categories=ENGINEERING_CATEGORIES,
    max_rounds=3,
    min_findings_per_round=2,
)


# ==================== Architecture Review Categories ====================

ARCHITECTURE_CATEGORIES = [
    CategoryConfig(
        id="api_design",
        name="API Design",
        description="REST conventions, versioning, contracts",
        keywords=["api", "rest", "versioning", "contract", "endpoint", "openapi"],
        priority=1,
    ),
    CategoryConfig(
        id="service_boundaries",
        name="Service Boundaries",
        description="Microservice boundaries, bounded contexts",
        keywords=["service", "boundary", "microservice", "bounded context", "domain"],
        priority=1,
    ),
    CategoryConfig(
        id="data_architecture",
        name="Data Architecture",
        description="Data models, schema, consistency",
        keywords=["data model", "schema", "database", "consistency", "cqrs"],
        priority=1,
    ),
    CategoryConfig(
        id="dependencies",
        name="Dependencies",
        description="Circular dependencies, coupling direction",
        keywords=["dependency", "circular", "coupling", "import", "abstraction"],
        priority=2,
    ),
    CategoryConfig(
        id="resilience",
        name="Resilience Patterns",
        description="Circuit breakers, retries, timeouts",
        keywords=["resilience", "circuit breaker", "retry", "timeout", "fallback", "bulkhead"],
        priority=2,
    ),
    CategoryConfig(
        id="scalability",
        name="Scalability Design",
        description="Horizontal scaling, caching, async",
        keywords=["scalability", "horizontal", "cache", "async", "queue", "load balancing"],
        priority=2,
    ),
    CategoryConfig(
        id="breaking_changes",
        name="Breaking Changes",
        description="Backward compatibility, migration",
        keywords=["breaking", "compatibility", "migration", "deprecation"],
        priority=1,
    ),
    CategoryConfig(
        id="patterns",
        name="Architectural Patterns",
        description="Design patterns usage and violations",
        keywords=["pattern", "repository", "factory", "observer", "saga", "event sourcing"],
        priority=3,
    ),
]

ARCHITECTURE_ANALYSIS_CONFIG = IterativeAnalysisConfig(
    analysis_type=AnalysisTypeCategories.ARCHITECTURE,
    categories=ARCHITECTURE_CATEGORIES,
    max_rounds=4,
    min_findings_per_round=2,
)


# ==================== Threat Model Categories ====================

THREAT_MODEL_CATEGORIES = [
    CategoryConfig(
        id="spoofing",
        name="Spoofing",
        description="Identity spoofing, impersonation attacks",
        keywords=["spoofing", "impersonate", "identity", "fake", "forge"],
        priority=1,
    ),
    CategoryConfig(
        id="tampering",
        name="Tampering",
        description="Data tampering, modification attacks",
        keywords=["tampering", "modify", "alter", "integrity", "forge"],
        priority=1,
    ),
    CategoryConfig(
        id="repudiation",
        name="Repudiation",
        description="Actions that cannot be proven",
        keywords=["repudiation", "deny", "proof", "audit", "non-repudiation"],
        priority=2,
    ),
    CategoryConfig(
        id="info_disclosure",
        name="Information Disclosure",
        description="Unauthorized information exposure",
        keywords=["disclosure", "leak", "exposure", "confidentiality", "sensitive"],
        priority=1,
    ),
    CategoryConfig(
        id="dos",
        name="Denial of Service",
        description="Availability attacks, resource exhaustion",
        keywords=["denial of service", "dos", "availability", "exhaust", "flood"],
        priority=2,
    ),
    CategoryConfig(
        id="elevation",
        name="Elevation of Privilege",
        description="Privilege escalation attacks",
        keywords=["elevation", "privilege", "escalation", "admin", "root"],
        priority=1,
    ),
    CategoryConfig(
        id="cost_exploitation",
        name="Cost Exploitation",
        description="Attacks that cause financial cost",
        keywords=["cost", "financial", "billing", "resource", "abuse"],
        priority=2,
    ),
    CategoryConfig(
        id="race_condition",
        name="Race Conditions",
        description="TOCTOU, timing attacks",
        keywords=["race condition", "toctou", "timing", "concurrent", "parallel"],
        priority=2,
    ),
]

THREAT_MODEL_ANALYSIS_CONFIG = IterativeAnalysisConfig(
    analysis_type=AnalysisTypeCategories.THREAT_MODEL,
    categories=THREAT_MODEL_CATEGORIES,
    max_rounds=5,
    min_findings_per_round=2,
)


# ==================== Config Registry ====================

ANALYSIS_CONFIGS: dict[AnalysisTypeCategories, IterativeAnalysisConfig] = {
    AnalysisTypeCategories.SECURITY: SECURITY_ANALYSIS_CONFIG,
    AnalysisTypeCategories.PRIVACY: PRIVACY_ANALYSIS_CONFIG,
    AnalysisTypeCategories.COMPLIANCE: COMPLIANCE_ANALYSIS_CONFIG,
    AnalysisTypeCategories.ENGINEERING: ENGINEERING_ANALYSIS_CONFIG,
    AnalysisTypeCategories.ARCHITECTURE: ARCHITECTURE_ANALYSIS_CONFIG,
    AnalysisTypeCategories.THREAT_MODEL: THREAT_MODEL_ANALYSIS_CONFIG,
}


def get_analysis_config(analysis_type: AnalysisTypeCategories) -> IterativeAnalysisConfig:
    """Get the iterative analysis configuration for a specific analysis type."""
    return ANALYSIS_CONFIGS.get(analysis_type, SECURITY_ANALYSIS_CONFIG)


def get_all_analysis_configs() -> dict[AnalysisTypeCategories, IterativeAnalysisConfig]:
    """Get all analysis configurations."""
    return ANALYSIS_CONFIGS
