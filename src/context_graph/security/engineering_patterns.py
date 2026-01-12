"""
Engineering Pattern Matcher - Analyze code for engineering quality concerns.

Evaluates:
- Code complexity and maintainability
- Technical debt indicators
- Test coverage gaps
- Documentation quality
- CI/CD maturity
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from context_graph.core.models import (
    EngineeringFinding,
    EngineeringCategory,
    Severity,
    State,
)
from context_graph.security.delta_analyzer import DeltaAnalysisResult


@dataclass
class EngineeringPattern:
    """An engineering pattern to match against."""
    
    id: str
    name: str
    description: str
    category: EngineeringCategory
    severity: Severity = Severity.MEDIUM
    
    # Thresholds and conditions
    min_complexity_score: int = 0
    min_tech_debt_items: int = 0
    max_test_coverage: float = 1.0  # Trigger if coverage below this
    
    # Recommendations
    recommendation: str = ""
    mitigations: list[str] = field(default_factory=list)
    estimated_effort: str = "medium"


# Define engineering patterns
ENGINEERING_PATTERNS = [
    # Code Complexity
    EngineeringPattern(
        id="ENG-001",
        name="High Cyclomatic Complexity",
        description="Code has high cyclomatic complexity making it difficult to test and maintain",
        category=EngineeringCategory.HIGH_COMPLEXITY,
        severity=Severity.MEDIUM,
        min_complexity_score=50,
        recommendation="Refactor complex functions into smaller, focused units",
        mitigations=[
            "Extract helper functions",
            "Apply single responsibility principle",
            "Consider using design patterns to reduce branching",
        ],
        estimated_effort="medium",
    ),
    EngineeringPattern(
        id="ENG-002",
        name="Deep Nesting Detected",
        description="Code contains deeply nested blocks that reduce readability",
        category=EngineeringCategory.DEEP_NESTING,
        severity=Severity.LOW,
        recommendation="Flatten nested structures using early returns or guard clauses",
        mitigations=[
            "Use guard clauses for early exits",
            "Extract nested logic into separate functions",
            "Consider using polymorphism instead of conditionals",
        ],
        estimated_effort="low",
    ),
    EngineeringPattern(
        id="ENG-003",
        name="Long Functions",
        description="Functions exceed recommended length, making them hard to understand",
        category=EngineeringCategory.LONG_FUNCTIONS,
        severity=Severity.LOW,
        recommendation="Break down long functions into smaller, composable units",
        mitigations=[
            "Apply extract method refactoring",
            "Group related operations",
            "Create helper classes for complex operations",
        ],
        estimated_effort="low",
    ),
    EngineeringPattern(
        id="ENG-004",
        name="Large Files",
        description="Source files are too large, indicating poor module organization",
        category=EngineeringCategory.LARGE_FILES,
        severity=Severity.MEDIUM,
        recommendation="Split large files into focused modules",
        mitigations=[
            "Apply module extraction",
            "Group by feature or domain",
            "Create separate files for models, services, and utilities",
        ],
        estimated_effort="medium",
    ),
    
    # Technical Debt
    EngineeringPattern(
        id="ENG-010",
        name="High Technical Debt",
        description="Significant number of TODO/FIXME comments indicate unfinished work",
        category=EngineeringCategory.TODO_FIXME,
        severity=Severity.LOW,
        min_tech_debt_items=10,
        recommendation="Address technical debt items before adding new features",
        mitigations=[
            "Create tickets for each TODO item",
            "Prioritize debt items by impact",
            "Allocate time in each sprint for debt reduction",
        ],
        estimated_effort="medium",
    ),
    EngineeringPattern(
        id="ENG-011",
        name="Missing Error Handling",
        description="Insufficient error handling may cause runtime failures",
        category=EngineeringCategory.MISSING_ERROR_HANDLING,
        severity=Severity.HIGH,
        recommendation="Add comprehensive error handling to critical paths",
        mitigations=[
            "Wrap external calls in try-catch blocks",
            "Implement error boundaries",
            "Add logging for error scenarios",
            "Define error recovery strategies",
        ],
        estimated_effort="medium",
    ),
    
    # Testing
    EngineeringPattern(
        id="ENG-020",
        name="Low Test Coverage",
        description="Test coverage is insufficient for confident deployments",
        category=EngineeringCategory.LOW_TEST_COVERAGE,
        severity=Severity.HIGH,
        max_test_coverage=0.5,
        recommendation="Increase test coverage, especially for critical paths",
        mitigations=[
            "Add unit tests for business logic",
            "Add integration tests for API endpoints",
            "Implement test coverage requirements in CI",
        ],
        estimated_effort="high",
    ),
    EngineeringPattern(
        id="ENG-021",
        name="Missing Tests for Affected Code",
        description="Code changes affect areas without test coverage",
        category=EngineeringCategory.MISSING_TESTS,
        severity=Severity.MEDIUM,
        recommendation="Add tests before modifying untested code",
        mitigations=[
            "Write characterization tests first",
            "Add tests for the happy path",
            "Add edge case and error tests",
        ],
        estimated_effort="medium",
    ),
    
    # Documentation
    EngineeringPattern(
        id="ENG-030",
        name="Missing Documentation",
        description="Code lacks documentation making it difficult to understand",
        category=EngineeringCategory.MISSING_DOCUMENTATION,
        severity=Severity.LOW,
        recommendation="Add documentation for public APIs and complex logic",
        mitigations=[
            "Add docstrings to all public functions",
            "Document complex algorithms",
            "Create README for each module",
        ],
        estimated_effort="low",
    ),
    
    # Maintainability
    EngineeringPattern(
        id="ENG-040",
        name="Circular Dependencies",
        description="Circular dependencies detected between modules",
        category=EngineeringCategory.CIRCULAR_DEPENDENCIES,
        severity=Severity.HIGH,
        recommendation="Refactor to eliminate circular dependencies",
        mitigations=[
            "Extract shared code to a common module",
            "Apply dependency inversion principle",
            "Use dependency injection",
        ],
        estimated_effort="high",
    ),
    EngineeringPattern(
        id="ENG-041",
        name="Missing Type Hints",
        description="Code lacks type hints reducing IDE support and static analysis",
        category=EngineeringCategory.MISSING_TYPE_HINTS,
        severity=Severity.LOW,
        recommendation="Add type hints to improve code quality and maintainability",
        mitigations=[
            "Add type hints to function signatures",
            "Use mypy or similar for type checking",
            "Configure CI to enforce type checking",
        ],
        estimated_effort="low",
    ),
    
    # Observability
    EngineeringPattern(
        id="ENG-050",
        name="Insufficient Logging",
        description="Logging is insufficient for debugging and monitoring",
        category=EngineeringCategory.INSUFFICIENT_LOGGING,
        severity=Severity.MEDIUM,
        recommendation="Add structured logging for observability",
        mitigations=[
            "Add logging at key decision points",
            "Include correlation IDs",
            "Use structured logging format",
        ],
        estimated_effort="low",
    ),
    EngineeringPattern(
        id="ENG-051",
        name="No Health Checks",
        description="Service lacks health check endpoints for monitoring",
        category=EngineeringCategory.NO_HEALTH_CHECKS,
        severity=Severity.MEDIUM,
        recommendation="Implement health check endpoints",
        mitigations=[
            "Add /health or /healthz endpoint",
            "Include dependency health checks",
            "Configure readiness and liveness probes",
        ],
        estimated_effort="low",
    ),
    
    # CI/CD
    EngineeringPattern(
        id="ENG-060",
        name="No CI/CD Pipeline",
        description="Project lacks automated CI/CD pipeline",
        category=EngineeringCategory.NO_CI_CD,
        severity=Severity.HIGH,
        recommendation="Set up CI/CD pipeline for automated testing and deployment",
        mitigations=[
            "Configure GitHub Actions or similar",
            "Add automated test runs",
            "Implement deployment automation",
        ],
        estimated_effort="high",
    ),
    EngineeringPattern(
        id="ENG-061",
        name="No Linting Configuration",
        description="Project lacks linting configuration for code consistency",
        category=EngineeringCategory.NO_LINTING,
        severity=Severity.LOW,
        recommendation="Configure linting tools for consistent code style",
        mitigations=[
            "Add ESLint/Pylint/similar configuration",
            "Configure pre-commit hooks",
            "Add linting to CI pipeline",
        ],
        estimated_effort="low",
    ),
]


class EngineeringPatternMatcher:
    """
    Match codebase state against engineering patterns.
    
    Analyzes code quality, technical debt, and engineering practices.
    """
    
    def __init__(self, patterns: list[EngineeringPattern] | None = None) -> None:
        self.patterns = patterns or ENGINEERING_PATTERNS
    
    def match(
        self,
        delta_result: DeltaAnalysisResult,
        state: State | None = None,
        engineering_metrics: dict[str, Any] | None = None,
    ) -> list[EngineeringFinding]:
        """
        Match delta and state against engineering patterns.
        
        Args:
            delta_result: Delta analysis between intent and state
            state: Current codebase state
            engineering_metrics: Metrics from EngineeringAnalyzer
            
        Returns:
            List of EngineeringFindings
        """
        findings: list[EngineeringFinding] = []
        
        metrics = engineering_metrics or {}
        
        # Check each pattern
        for pattern in self.patterns:
            finding = self._check_pattern(pattern, delta_result, state, metrics)
            if finding:
                findings.append(finding)
        
        # Add findings based on metrics if available
        if metrics:
            findings.extend(self._analyze_metrics(metrics))
        
        return findings
    
    def _check_pattern(
        self,
        pattern: EngineeringPattern,
        delta_result: DeltaAnalysisResult,
        state: State | None,
        metrics: dict[str, Any],
    ) -> EngineeringFinding | None:
        """Check if a pattern matches the current state."""
        
        # Check complexity threshold
        if pattern.min_complexity_score > 0:
            avg_complexity = metrics.get("avg_cyclomatic_complexity", 0)
            if avg_complexity < pattern.min_complexity_score:
                return None
        
        # Check technical debt threshold
        if pattern.min_tech_debt_items > 0:
            total_debt = (
                metrics.get("total_todos", 0) + 
                metrics.get("total_fixmes", 0) +
                metrics.get("total_hacks", 0)
            )
            if total_debt < pattern.min_tech_debt_items:
                return None
        
        # Check test coverage threshold
        if pattern.max_test_coverage < 1.0:
            test_ratio = metrics.get("test_to_code_ratio", 1.0)
            if test_ratio >= pattern.max_test_coverage:
                return None
        
        # Pattern-specific checks
        if pattern.category == EngineeringCategory.NO_CI_CD:
            if metrics.get("has_ci_cd", True):
                return None
        
        elif pattern.category == EngineeringCategory.NO_LINTING:
            if metrics.get("has_linting_config", True):
                return None
        
        elif pattern.category == EngineeringCategory.CIRCULAR_DEPENDENCIES:
            if metrics.get("circular_dependency_risk", 0) == 0:
                return None
        
        elif pattern.category == EngineeringCategory.MISSING_TYPE_HINTS:
            type_hint_ratio = metrics.get("files_with_type_hints", 0) / max(metrics.get("source_files", 1), 1)
            if type_hint_ratio > 0.5:
                return None
        
        elif pattern.category == EngineeringCategory.MISSING_DOCUMENTATION:
            doc_ratio = metrics.get("files_with_docstrings", 0) / max(metrics.get("source_files", 1), 1)
            if doc_ratio > 0.5:
                return None
        
        # Only create finding if checks pass
        if self._should_create_finding(pattern, metrics):
            return self._create_finding(pattern, metrics)
        
        return None
    
    def _should_create_finding(
        self,
        pattern: EngineeringPattern,
        metrics: dict[str, Any],
    ) -> bool:
        """Determine if we should create a finding for this pattern."""
        category = pattern.category
        
        # Complexity findings
        if category == EngineeringCategory.HIGH_COMPLEXITY:
            return metrics.get("avg_cyclomatic_complexity", 0) > 20
        
        if category == EngineeringCategory.LARGE_FILES:
            return metrics.get("long_files", 0) > 3
        
        if category == EngineeringCategory.LONG_FUNCTIONS:
            return metrics.get("avg_function_length", 0) > 50
        
        # Technical debt
        if category == EngineeringCategory.TODO_FIXME:
            return (metrics.get("total_todos", 0) + metrics.get("total_fixmes", 0)) > 10
        
        # Testing
        if category == EngineeringCategory.LOW_TEST_COVERAGE:
            return metrics.get("test_to_code_ratio", 1.0) < 0.3
        
        if category == EngineeringCategory.MISSING_TESTS:
            return metrics.get("test_files", 0) == 0
        
        # CI/CD
        if category == EngineeringCategory.NO_CI_CD:
            return not metrics.get("has_ci_cd", False)
        
        if category == EngineeringCategory.NO_LINTING:
            return not metrics.get("has_linting_config", False)
        
        # Observability
        if category == EngineeringCategory.INSUFFICIENT_LOGGING:
            log_ratio = metrics.get("logging_statements", 0) / max(metrics.get("total_functions", 1), 1)
            return log_ratio < 0.1
        
        if category == EngineeringCategory.NO_HEALTH_CHECKS:
            controls = metrics.get("existing_controls", [])
            return "health_checks" not in controls
        
        return False
    
    def _create_finding(
        self,
        pattern: EngineeringPattern,
        metrics: dict[str, Any],
    ) -> EngineeringFinding:
        """Create an engineering finding from a matched pattern."""
        finding = EngineeringFinding(
            id=uuid4(),
            title=pattern.name,
            description=pattern.description,
            severity=pattern.severity,
            category=pattern.category,
            estimated_effort=pattern.estimated_effort,
            recommendation=pattern.recommendation,
            mitigations=pattern.mitigations.copy(),
            source_type="pattern",
            source_reference=pattern.id,
            confidence=0.8,
        )
        
        # Add metrics context
        if pattern.category == EngineeringCategory.HIGH_COMPLEXITY:
            finding.complexity_score = int(metrics.get("avg_cyclomatic_complexity", 0))
            finding.affected_files = metrics.get("high_complexity_files", [])[:5]
        
        elif pattern.category == EngineeringCategory.LOW_TEST_COVERAGE:
            finding.test_coverage_gap = 1.0 - metrics.get("test_to_code_ratio", 0)
        
        elif pattern.category == EngineeringCategory.TODO_FIXME:
            finding.tech_debt_items = (
                metrics.get("total_todos", 0) + 
                metrics.get("total_fixmes", 0) +
                metrics.get("total_hacks", 0)
            )
        
        return finding
    
    def _analyze_metrics(self, metrics: dict[str, Any]) -> list[EngineeringFinding]:
        """Generate additional findings from raw metrics."""
        findings: list[EngineeringFinding] = []
        
        # Check for missing error handling
        error_ratio = metrics.get("error_handlers", 0) / max(metrics.get("total_functions", 1), 1)
        if error_ratio < 0.2 and metrics.get("total_functions", 0) > 10:
            findings.append(EngineeringFinding(
                id=uuid4(),
                title="Missing Error Handling",
                description=f"Only {error_ratio:.0%} of functions have error handling",
                severity=Severity.MEDIUM,
                category=EngineeringCategory.MISSING_ERROR_HANDLING,
                estimated_effort="medium",
                recommendation="Add error handling to critical code paths",
                mitigations=[
                    "Add try-catch blocks around external calls",
                    "Implement error boundaries",
                    "Add logging for exceptions",
                ],
                source_type="metrics",
                confidence=0.7,
            ))
        
        # Check for high-risk files
        high_risk_files = metrics.get("high_complexity_files", [])
        if len(high_risk_files) > 5:
            findings.append(EngineeringFinding(
                id=uuid4(),
                title="Multiple High-Complexity Files",
                description=f"{len(high_risk_files)} files have high complexity scores",
                severity=Severity.MEDIUM,
                category=EngineeringCategory.HIGH_COMPLEXITY,
                affected_files=high_risk_files[:10],
                estimated_effort="high",
                recommendation="Prioritize refactoring of complex files",
                mitigations=[
                    "Start with most frequently modified files",
                    "Apply incremental refactoring",
                    "Add tests before refactoring",
                ],
                source_type="metrics",
                confidence=0.85,
            ))
        
        return findings

