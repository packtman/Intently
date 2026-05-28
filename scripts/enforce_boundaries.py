#!/usr/bin/env python3
"""
Architectural Boundary Enforcer for Intently

Statically analyzes the source tree to detect:
1. Circular import dependencies between domains
2. Forbidden cross-domain imports (boundary violations)
3. Security invariant violations (hardcoded secrets, missing sanitization patterns)
4. Feature flag completeness

Outputs structured JSON so agents can parse failures and self-correct.

Usage:
    python scripts/enforce_boundaries.py [--json] [--fix-hints]
    
Exit codes:
    0 - All boundaries intact
    1 - Violations detected (details in output)
    2 - Script error (cannot parse source tree)
"""
from __future__ import annotations

import ast
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

SRC_ROOT = Path(__file__).parent.parent / "src" / "context_graph"

DOMAINS = [
    "parsers",
    "analyzers",
    "code_graph",
    "security",
    "pm",
    "api",
    "core",
    "llm",
    "governance",
    "storage",
    "config",
    "chat",
    "integrations",
    "reports",
    "tracing",
    "lsp",
    "tests",
]

FORBIDDEN_IMPORTS: dict[str, list[str]] = {
    "parsers": ["security", "pm", "api", "storage", "chat"],
    "analyzers": ["security", "pm", "api", "storage", "chat", "parsers"],
    "code_graph": ["security", "pm", "api", "storage", "chat", "parsers"],
    "pm": ["security", "api", "storage.sqlite", "chat", "parsers"],
    "core": ["security", "pm", "api", "storage", "chat", "parsers", "analyzers", "code_graph", "llm"],
}

SECURITY_PATTERNS = [
    {
        "id": "HARDCODED_SECRET",
        "pattern": r'(?:api_key|secret|token|password)\s*=\s*["\'][^"\']{8,}["\']',
        "severity": "critical",
        "message": "Potential hardcoded secret detected. Secrets must come from environment variables.",
        "fix": "Replace with os.environ.get('VARIABLE_NAME') or use python-dotenv.",
    },
    {
        "id": "BARE_EXCEPT",
        "pattern": r"except\s*:",
        "severity": "warning",
        "message": "Bare except clause catches all exceptions including SystemExit and KeyboardInterrupt.",
        "fix": "Use 'except Exception:' at minimum, or catch specific exception types.",
    },
    {
        "id": "RAW_HTML_INJECTION",
        "pattern": r'f["\'].*<(?:script|iframe|object|embed|link).*["\']',
        "severity": "critical",
        "message": "Potential XSS vulnerability: raw HTML tag in f-string output.",
        "fix": "Use a template engine with auto-escaping or html.escape() for user-supplied values.",
    },
    {
        "id": "OAUTH_WITHOUT_PKCE",
        "pattern": r"authorization_code.*(?!code_challenge)",
        "severity": "high",
        "message": "OAuth authorization code flow without PKCE code_challenge parameter.",
        "fix": "Add code_challenge and code_challenge_method parameters to the authorization request.",
    },
    {
        "id": "MISSING_TYPE_HINTS",
        "pattern": r"^def\s+\w+\([^)]*\)\s*:",
        "severity": "info",
        "message": "Function definition without return type annotation.",
        "fix": "Add return type annotation: def function_name(...) -> ReturnType:",
    },
]


@dataclass
class Violation:
    rule_id: str
    severity: str
    file: str
    line: int
    message: str
    fix: str
    domain: str = ""

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "file": str(self.file),
            "line": self.line,
            "message": self.message,
            "fix": self.fix,
            "domain": self.domain,
        }


@dataclass
class BoundaryReport:
    violations: list[Violation] = field(default_factory=list)
    files_scanned: int = 0
    domains_checked: list[str] = field(default_factory=list)

    @property
    def has_failures(self) -> bool:
        return any(v.severity in ("critical", "high") for v in self.violations)

    def to_dict(self) -> dict:
        return {
            "status": "FAIL" if self.has_failures else "PASS",
            "summary": {
                "files_scanned": self.files_scanned,
                "domains_checked": self.domains_checked,
                "total_violations": len(self.violations),
                "critical": sum(1 for v in self.violations if v.severity == "critical"),
                "high": sum(1 for v in self.violations if v.severity == "high"),
                "warning": sum(1 for v in self.violations if v.severity == "warning"),
                "info": sum(1 for v in self.violations if v.severity == "info"),
            },
            "violations": [v.to_dict() for v in self.violations],
        }


def get_domain(filepath: Path) -> Optional[str]:
    """Extract domain name from file path relative to src/context_graph/."""
    try:
        rel = filepath.relative_to(SRC_ROOT)
        parts = rel.parts
        if len(parts) > 1 and parts[0] in DOMAINS:
            return parts[0]
    except ValueError:
        pass
    return None


def extract_imports(filepath: Path) -> list[tuple[int, str]]:
    """Parse a Python file and extract all context_graph imports with line numbers."""
    imports = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return imports

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith("context_graph."):
                imports.append((node.lineno, node.module))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("context_graph."):
                    imports.append((node.lineno, alias.name))
    return imports


def get_imported_domain(module_path: str) -> Optional[str]:
    """Extract the domain from a module import path like 'context_graph.security.foo'."""
    parts = module_path.split(".")
    if len(parts) >= 2 and parts[0] == "context_graph":
        candidate = parts[1]
        if candidate in DOMAINS:
            return candidate
    return None


def check_boundary_violations(report: BoundaryReport) -> None:
    """Check for forbidden cross-domain imports."""
    for py_file in SRC_ROOT.rglob("*.py"):
        domain = get_domain(py_file)
        if domain is None or domain not in FORBIDDEN_IMPORTS:
            continue

        forbidden = FORBIDDEN_IMPORTS[domain]
        imports = extract_imports(py_file)

        for line_no, module_path in imports:
            imported_domain = get_imported_domain(module_path)
            if imported_domain and imported_domain in forbidden:
                rel_path = py_file.relative_to(SRC_ROOT.parent.parent)
                report.violations.append(
                    Violation(
                        rule_id="BOUNDARY_VIOLATION",
                        severity="high",
                        file=str(rel_path),
                        line=line_no,
                        message=(
                            f"Domain '{domain}' must not import from '{imported_domain}'. "
                            f"Import: {module_path}"
                        ),
                        fix=(
                            f"Move shared types/interfaces to 'core/' or use dependency injection. "
                            f"If '{domain}' needs data from '{imported_domain}', pass it as a parameter "
                            f"from the API/orchestration layer instead of importing directly."
                        ),
                        domain=domain,
                    )
                )


def check_circular_imports(report: BoundaryReport) -> None:
    """Detect circular import chains between domains."""
    domain_deps: dict[str, set[str]] = {d: set() for d in DOMAINS}

    for py_file in SRC_ROOT.rglob("*.py"):
        domain = get_domain(py_file)
        if domain is None:
            continue

        imports = extract_imports(py_file)
        for _, module_path in imports:
            imported_domain = get_imported_domain(module_path)
            if imported_domain and imported_domain != domain:
                domain_deps[domain].add(imported_domain)

    for domain_a in DOMAINS:
        for domain_b in domain_deps.get(domain_a, set()):
            if domain_a in domain_deps.get(domain_b, set()):
                if domain_a < domain_b:  # Report each pair only once
                    report.violations.append(
                        Violation(
                            rule_id="CIRCULAR_DEPENDENCY",
                            severity="warning",
                            file=f"src/context_graph/{domain_a}/ <-> src/context_graph/{domain_b}/",
                            line=0,
                            message=(
                                f"Circular dependency detected: '{domain_a}' imports from '{domain_b}' "
                                f"AND '{domain_b}' imports from '{domain_a}'."
                            ),
                            fix=(
                                f"Break the cycle by extracting shared interfaces into 'core/'. "
                                f"One domain should depend on the other, not both on each other. "
                                f"Consider which domain owns the shared concept."
                            ),
                            domain=f"{domain_a},{domain_b}",
                        )
                    )


def check_security_patterns(report: BoundaryReport) -> None:
    """Scan source files for security anti-patterns."""
    for py_file in SRC_ROOT.rglob("*.py"):
        domain = get_domain(py_file)
        if domain == "tests":
            continue

        try:
            with open(py_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except (UnicodeDecodeError, IOError):
            continue

        rel_path = py_file.relative_to(SRC_ROOT.parent.parent)

        for pattern_def in SECURITY_PATTERNS:
            if pattern_def["id"] == "MISSING_TYPE_HINTS":
                continue  # Skip info-level in default mode

            regex = re.compile(pattern_def["pattern"], re.IGNORECASE)
            for i, line in enumerate(lines, start=1):
                if line.strip().startswith("#"):
                    continue
                if regex.search(line):
                    report.violations.append(
                        Violation(
                            rule_id=pattern_def["id"],
                            severity=pattern_def["severity"],
                            file=str(rel_path),
                            line=i,
                            message=pattern_def["message"],
                            fix=pattern_def["fix"],
                            domain=domain or "",
                        )
                    )


def check_feature_flag_completeness(report: BoundaryReport) -> None:
    """Verify feature flags are defined in all required locations."""
    features_file = SRC_ROOT / "config" / "features.py"
    collab_routes_file = SRC_ROOT / "api" / "collaboration_routes.py"

    if not features_file.exists():
        return

    try:
        with open(features_file, "r", encoding="utf-8") as f:
            features_content = f.read()
    except IOError:
        return

    class_flags = set(re.findall(r"(\w+_enabled)\s*[:=]", features_content))
    from_env_flags = set(re.findall(r'os\.environ\.get\(["\']FEATURE_(\w+)', features_content, re.IGNORECASE))
    all_enabled_flags = set()
    to_dict_flags = set()

    all_enabled_match = re.search(r"def all_enabled\(.*?\n(.*?)(?=\n    def |\nclass |\Z)", features_content, re.DOTALL)
    if all_enabled_match:
        all_enabled_flags = set(re.findall(r"(\w+_enabled)\s*=", all_enabled_match.group(1)))

    to_dict_match = re.search(r"def to_dict\(.*?\n(.*?)(?=\n    def |\nclass |\Z)", features_content, re.DOTALL)
    if to_dict_match:
        to_dict_flags = set(re.findall(r'["\'](\w+_enabled)["\']', to_dict_match.group(1)))

    for flag in class_flags:
        if flag not in from_env_flags and flag.upper().replace("_ENABLED", "") not in from_env_flags:
            report.violations.append(
                Violation(
                    rule_id="INCOMPLETE_FEATURE_FLAG",
                    severity="warning",
                    file="src/context_graph/config/features.py",
                    line=0,
                    message=f"Feature flag '{flag}' may be missing from from_env() method.",
                    fix=f"Add FEATURE_{flag.upper().replace('_ENABLED', '')} to the from_env() classmethod.",
                    domain="config",
                )
            )


def scan_files(report: BoundaryReport) -> None:
    """Count and track scanned files."""
    count = 0
    for py_file in SRC_ROOT.rglob("*.py"):
        count += 1
    report.files_scanned = count
    report.domains_checked = [d for d in DOMAINS if (SRC_ROOT / d).is_dir()]


def main() -> int:
    json_output = "--json" in sys.argv

    if not SRC_ROOT.exists():
        print(json.dumps({"status": "ERROR", "message": f"Source root not found: {SRC_ROOT}"}), file=sys.stderr)
        return 2

    report = BoundaryReport()
    scan_files(report)
    check_boundary_violations(report)
    check_circular_imports(report)
    check_security_patterns(report)
    check_feature_flag_completeness(report)

    result = report.to_dict()

    if json_output:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"  INTENTLY BOUNDARY ENFORCEMENT REPORT")
        print(f"{'='*60}")
        print(f"  Status: {result['status']}")
        print(f"  Files scanned: {result['summary']['files_scanned']}")
        print(f"  Domains checked: {', '.join(result['summary']['domains_checked'])}")
        print(f"  Violations: {result['summary']['total_violations']}")
        print(f"    Critical: {result['summary']['critical']}")
        print(f"    High: {result['summary']['high']}")
        print(f"    Warning: {result['summary']['warning']}")
        print(f"    Info: {result['summary']['info']}")
        print(f"{'='*60}\n")

        for v in report.violations:
            icon = {"critical": "🚨", "high": "❌", "warning": "⚠️", "info": "ℹ️"}.get(v.severity, "?")
            print(f"  {icon} [{v.rule_id}] {v.file}:{v.line}")
            print(f"     {v.message}")
            print(f"     FIX: {v.fix}")
            print()

    return 1 if report.has_failures else 0


if __name__ == "__main__":
    sys.exit(main())
