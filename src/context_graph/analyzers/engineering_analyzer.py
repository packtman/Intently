"""
Engineering Analyzer - Assess implementation complexity and engineering effort.

Evaluates:
- Code complexity metrics (cyclomatic complexity, nesting depth, function size)
- Technical debt indicators (TODOs, code smells, duplication patterns)
- Test coverage and quality
- Documentation coverage
- Coupling and cohesion
- Implementation effort estimation
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from context_graph.core.models import Entity, EntityType, Relationship, RelationshipType
from context_graph.analyzers.codebase_analyzer import CodebaseAnalyzer, FileAnalysis


class ImplementationEffort(str, Enum):
    """Estimated implementation effort levels."""
    
    TRIVIAL = "trivial"      # < 1 day, simple changes
    LOW = "low"              # 1-2 days, straightforward
    MEDIUM = "medium"        # 3-5 days, moderate complexity
    HIGH = "high"            # 1-2 weeks, significant effort
    VERY_HIGH = "very_high"  # 2+ weeks, major undertaking


@dataclass
class FileComplexity:
    """Complexity metrics for a single file."""
    
    path: str = ""
    lines_of_code: int = 0
    logical_lines: int = 0  # Non-blank, non-comment lines
    
    # Complexity indicators
    cyclomatic_complexity: int = 0  # Estimated from branches
    max_nesting_depth: int = 0
    avg_function_length: float = 0.0
    longest_function: int = 0
    function_count: int = 0
    class_count: int = 0
    
    # Coupling
    import_count: int = 0
    external_dependencies: int = 0
    internal_dependencies: int = 0
    
    # Technical debt
    todo_count: int = 0
    fixme_count: int = 0
    hack_count: int = 0
    magic_numbers: int = 0
    long_lines: int = 0  # Lines > 120 chars
    
    # Quality indicators
    has_tests: bool = False
    has_docstrings: bool = False
    has_type_hints: bool = False
    error_handling_ratio: float = 0.0  # try/catch per function
    
    # Risk score (0-100)
    complexity_score: int = 0


@dataclass
class EngineeringMetrics:
    """Aggregated metrics from engineering analysis."""
    
    # File counts
    total_files: int = 0
    test_files: int = 0
    source_files: int = 0
    config_files: int = 0
    documentation_files: int = 0
    
    # Code metrics
    total_lines: int = 0
    logical_lines: int = 0
    test_lines: int = 0
    
    # Complexity aggregates
    total_functions: int = 0
    total_classes: int = 0
    avg_cyclomatic_complexity: float = 0.0
    max_cyclomatic_complexity: int = 0
    avg_function_length: float = 0.0
    
    # Test coverage indicators
    test_functions: int = 0
    test_to_code_ratio: float = 0.0
    files_with_tests: int = 0
    files_without_tests: int = 0
    
    # Technical debt
    total_todos: int = 0
    total_fixmes: int = 0
    total_hacks: int = 0
    total_magic_numbers: int = 0
    long_files: int = 0  # Files > 500 lines
    complex_files: int = 0  # Files with high complexity
    
    # Quality
    files_with_docstrings: int = 0
    files_with_type_hints: int = 0
    error_handlers: int = 0
    logging_statements: int = 0
    
    # Infrastructure
    has_ci_cd: bool = False
    has_dependency_lock: bool = False
    has_linting_config: bool = False
    has_formatting_config: bool = False
    
    # High complexity files for attention
    high_complexity_files: list[str] = field(default_factory=list)
    
    # Overall assessment
    overall_effort: ImplementationEffort = ImplementationEffort.MEDIUM
    effort_factors: list[str] = field(default_factory=list)


@dataclass
class ImplementationAssessment:
    """Assessment of implementation difficulty for a feature/change."""
    
    effort_level: ImplementationEffort = ImplementationEffort.MEDIUM
    estimated_days: str = "3-5 days"
    confidence: float = 0.7
    
    # Factors affecting difficulty
    complexity_factors: list[str] = field(default_factory=list)
    risk_factors: list[str] = field(default_factory=list)
    mitigating_factors: list[str] = field(default_factory=list)
    
    # Affected areas
    high_risk_files: list[str] = field(default_factory=list)
    areas_needing_tests: list[str] = field(default_factory=list)
    areas_needing_docs: list[str] = field(default_factory=list)
    
    # Recommendations
    recommendations: list[str] = field(default_factory=list)
    
    # Summary
    summary: str = ""


class EngineeringAnalyzer(CodebaseAnalyzer):
    """
    Analyze codebases to assess implementation difficulty and engineering effort.
    
    Provides:
    - Complexity metrics per file and aggregate
    - Technical debt assessment
    - Test coverage indicators
    - Implementation effort estimation
    - Risk identification for changes
    """
    
    def __init__(
        self,
        exclude_patterns: list[str] | None = None,
    ) -> None:
        super().__init__(exclude_patterns)
        self.metrics = EngineeringMetrics()
        self._file_complexities: list[FileComplexity] = []
        self._test_file_mapping: dict[str, str] = {}  # source -> test file
    
    def supported_extensions(self) -> list[str]:
        return [
            ".py", ".js", ".ts", ".tsx", ".jsx",
            ".java", ".kt", ".go", ".rs", ".rb",
            ".md", ".rst", ".txt",
            ".yaml", ".yml", ".json", ".toml",
        ]
    
    def analyze_file(self, file_path: Path) -> FileAnalysis:
        """Analyze a file for engineering complexity and quality."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return FileAnalysis(path=file_path, language="unknown")
        
        language = self._detect_language(file_path)
        lines = content.split("\n")
        
        analysis = FileAnalysis(
            path=file_path,
            language=language,
            lines_of_code=len(lines),
        )
        
        self.metrics.total_files += 1
        self.metrics.total_lines += len(lines)
        
        # Route based on file type
        if self._is_test_file(file_path):
            self._analyze_test_file(content, file_path, analysis)
        elif self._is_config_file(file_path):
            self._analyze_config_file(content, file_path, analysis)
        elif self._is_ci_cd_file(file_path):
            self._analyze_ci_cd_file(content, file_path, analysis)
        elif self._is_documentation_file(file_path):
            self._analyze_documentation(content, file_path, analysis)
        elif language in ["python", "javascript", "typescript", "java", "kotlin", "go", "rust", "ruby"]:
            self._analyze_source_complexity(content, file_path, language, analysis)
        
        return analysis
    
    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language from file extension."""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".jsx": "javascript",
            ".java": "java",
            ".kt": "kotlin",
            ".go": "go",
            ".rs": "rust",
            ".rb": "ruby",
            ".md": "markdown",
            ".rst": "restructuredtext",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".json": "json",
            ".toml": "toml",
        }
        return ext_map.get(file_path.suffix.lower(), "unknown")
    
    def _is_test_file(self, file_path: Path) -> bool:
        """Check if file is a test file."""
        name = file_path.name.lower()
        path_str = str(file_path).lower()
        
        test_patterns = [
            "test_", "_test.", ".test.", ".spec.",
            "_spec.", "tests/", "/test/", "__tests__/",
        ]
        return any(p in name or p in path_str for p in test_patterns)
    
    def _is_config_file(self, file_path: Path) -> bool:
        """Check if file is a configuration file."""
        name = file_path.name.lower()
        config_files = [
            "config.", ".env", "settings.", "application.",
            "pyproject.toml", "package.json", "cargo.toml",
            "go.mod", "build.gradle", "pom.xml", "gemfile",
            "requirements.txt", "setup.py", "setup.cfg",
            ".eslintrc", ".prettierrc", "tsconfig", "jest.config",
            "webpack.config", "babel.config", "vite.config",
        ]
        return any(cf in name for cf in config_files)
    
    def _is_ci_cd_file(self, file_path: Path) -> bool:
        """Check if file is a CI/CD configuration."""
        path_str = str(file_path).lower()
        ci_patterns = [
            ".github/workflows/", ".gitlab-ci", "jenkinsfile",
            ".circleci/", "azure-pipelines", ".travis",
            "bitbucket-pipelines", ".drone", "cloudbuild",
            "buildkite", "appveyor",
        ]
        return any(p in path_str for p in ci_patterns)
    
    def _is_documentation_file(self, file_path: Path) -> bool:
        """Check if file is documentation."""
        name = file_path.name.lower()
        path_str = str(file_path).lower()
        
        doc_patterns = [
            "readme", "changelog", "contributing", "license",
            "authors", "history", "docs/", "documentation/",
            "adr/",
        ]
        if file_path.suffix.lower() in [".md", ".rst"]:
            return True
        return any(p in name or p in path_str for p in doc_patterns)
    
    def _analyze_source_complexity(
        self,
        content: str,
        file_path: Path,
        language: str,
        analysis: FileAnalysis
    ) -> None:
        """Analyze source code for complexity metrics."""
        self.metrics.source_files += 1
        lines = content.split("\n")
        
        complexity = FileComplexity(
            path=str(file_path),
            lines_of_code=len(lines),
        )
        
        # Calculate logical lines (non-blank, non-comment)
        complexity.logical_lines = self._count_logical_lines(content, language)
        self.metrics.logical_lines += complexity.logical_lines
        
        # Cyclomatic complexity estimation
        complexity.cyclomatic_complexity = self._estimate_cyclomatic_complexity(content, language)
        
        # Nesting depth
        complexity.max_nesting_depth = self._calculate_max_nesting(content, language)
        
        # Function/method analysis
        functions = self._extract_functions(content, language)
        complexity.function_count = len(functions)
        self.metrics.total_functions += len(functions)
        
        if functions:
            lengths = [f["length"] for f in functions]
            complexity.avg_function_length = sum(lengths) / len(lengths)
            complexity.longest_function = max(lengths)
            self.metrics.avg_function_length = (
                (self.metrics.avg_function_length * (self.metrics.total_functions - len(functions)) +
                 sum(lengths)) / self.metrics.total_functions
                if self.metrics.total_functions > 0 else 0
            )
        
        # Class count
        complexity.class_count = self._count_classes(content, language)
        self.metrics.total_classes += complexity.class_count
        
        # Import analysis
        imports = self._analyze_imports(content, language)
        complexity.import_count = imports["total"]
        complexity.external_dependencies = imports["external"]
        complexity.internal_dependencies = imports["internal"]
        
        # Technical debt indicators
        complexity.todo_count = len(re.findall(r'\bTODO\b', content, re.IGNORECASE))
        complexity.fixme_count = len(re.findall(r'\bFIXME\b', content, re.IGNORECASE))
        complexity.hack_count = len(re.findall(r'\bHACK\b|\bXXX\b', content, re.IGNORECASE))
        complexity.magic_numbers = self._count_magic_numbers(content, language)
        complexity.long_lines = sum(1 for line in lines if len(line) > 120)
        
        self.metrics.total_todos += complexity.todo_count
        self.metrics.total_fixmes += complexity.fixme_count
        self.metrics.total_hacks += complexity.hack_count
        self.metrics.total_magic_numbers += complexity.magic_numbers
        
        # Quality indicators
        complexity.has_docstrings = self._has_docstrings(content, language)
        complexity.has_type_hints = self._has_type_hints(content, language)
        
        if complexity.has_docstrings:
            self.metrics.files_with_docstrings += 1
        if complexity.has_type_hints:
            self.metrics.files_with_type_hints += 1
        
        # Error handling ratio
        error_handlers = self._count_error_handlers(content, language)
        self.metrics.error_handlers += error_handlers
        complexity.error_handling_ratio = (
            error_handlers / complexity.function_count
            if complexity.function_count > 0 else 0
        )
        
        # Logging statements
        log_count = self._count_logging(content, language)
        self.metrics.logging_statements += log_count
        
        # Calculate complexity score (0-100)
        complexity.complexity_score = self._calculate_complexity_score(complexity)
        
        # Track high complexity files
        if complexity.complexity_score > 70:
            self.metrics.complex_files += 1
            self.metrics.high_complexity_files.append(str(file_path))
        
        if len(lines) > 500:
            self.metrics.long_files += 1
        
        self._file_complexities.append(complexity)
        
        # Add entity with complexity data
        analysis.entities.append(Entity(
            name=f"Source: {file_path.name}",
            entity_type=EntityType.MODULE,
            description=f"Source file (complexity score: {complexity.complexity_score}/100)",
            source=str(file_path),
            properties={
                "complexity_score": complexity.complexity_score,
                "cyclomatic_complexity": complexity.cyclomatic_complexity,
                "function_count": complexity.function_count,
                "lines_of_code": complexity.lines_of_code,
                "technical_debt": complexity.todo_count + complexity.fixme_count + complexity.hack_count,
            }
        ))
        
        # Add security controls based on quality
        if complexity.has_type_hints:
            analysis.security_controls.append("type_safety")
        if complexity.error_handling_ratio > 0.5:
            analysis.security_controls.append("error_handling")
        if log_count > 0:
            analysis.security_controls.append("logging")
    
    def _count_logical_lines(self, content: str, language: str) -> int:
        """Count non-blank, non-comment lines."""
        lines = content.split("\n")
        logical = 0
        in_multiline_comment = False
        
        for line in lines:
            stripped = line.strip()
            
            # Skip blank lines
            if not stripped:
                continue
            
            # Handle multi-line comments
            if language in ["python"]:
                if '"""' in stripped or "'''" in stripped:
                    in_multiline_comment = not in_multiline_comment
                    continue
            elif language in ["javascript", "typescript", "java", "kotlin", "go"]:
                if "/*" in stripped:
                    in_multiline_comment = True
                if "*/" in stripped:
                    in_multiline_comment = False
                    continue
            
            if in_multiline_comment:
                continue
            
            # Skip single-line comments
            if language == "python" and stripped.startswith("#"):
                continue
            if language in ["javascript", "typescript", "java", "kotlin", "go", "rust"] and stripped.startswith("//"):
                continue
            if language == "ruby" and stripped.startswith("#"):
                continue
            
            logical += 1
        
        return logical
    
    def _estimate_cyclomatic_complexity(self, content: str, language: str) -> int:
        """Estimate cyclomatic complexity from branching statements."""
        complexity = 1  # Base complexity
        
        # Branching keywords by language
        branch_patterns = [
            r'\bif\b', r'\belif\b', r'\belse\b',
            r'\bfor\b', r'\bwhile\b',
            r'\band\b', r'\bor\b',
            r'\bcase\b', r'\bcatch\b', r'\bexcept\b',
            r'\?\s*:', r'\|\|', r'&&',  # Ternary and logical operators
        ]
        
        for pattern in branch_patterns:
            complexity += len(re.findall(pattern, content))
        
        return complexity
    
    def _calculate_max_nesting(self, content: str, language: str) -> int:
        """Calculate maximum nesting depth."""
        max_depth = 0
        current_depth = 0
        
        # Simple brace/indent counting
        if language == "python":
            # Use indentation
            lines = content.split("\n")
            for line in lines:
                if line.strip():
                    # Count leading spaces/tabs
                    indent = len(line) - len(line.lstrip())
                    depth = indent // 4  # Assume 4-space indent
                    max_depth = max(max_depth, depth)
        else:
            # Use braces
            for char in content:
                if char == "{":
                    current_depth += 1
                    max_depth = max(max_depth, current_depth)
                elif char == "}":
                    current_depth = max(0, current_depth - 1)
        
        return max_depth
    
    def _extract_functions(self, content: str, language: str) -> list[dict[str, Any]]:
        """Extract function definitions and their lengths."""
        functions = []
        
        # Language-specific function patterns
        patterns = {
            "python": r'(?:async\s+)?def\s+(\w+)\s*\([^)]*\)\s*(?:->.*?)?:',
            "javascript": r'(?:async\s+)?function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[^=])\s*=>',
            "typescript": r'(?:async\s+)?function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[^=])\s*=>',
            "java": r'(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+\w+)?\s*\{',
            "kotlin": r'(?:fun|suspend\s+fun)\s+(\w+)\s*\([^)]*\)',
            "go": r'func\s+(?:\([^)]+\)\s+)?(\w+)\s*\([^)]*\)',
            "rust": r'(?:pub\s+)?(?:async\s+)?fn\s+(\w+)',
            "ruby": r'def\s+(\w+)',
        }
        
        pattern = patterns.get(language)
        if not pattern:
            return functions
        
        lines = content.split("\n")
        matches = list(re.finditer(pattern, content))
        
        for i, match in enumerate(matches):
            func_name = match.group(1) or (match.group(2) if match.lastindex >= 2 else None)
            if not func_name:
                continue
            
            # Find start line
            start_pos = match.start()
            start_line = content[:start_pos].count("\n")
            
            # Estimate function length (until next function or end)
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(content)
            
            func_content = content[start_pos:end_pos]
            func_lines = len(func_content.split("\n"))
            
            functions.append({
                "name": func_name,
                "start_line": start_line,
                "length": func_lines,
            })
        
        return functions
    
    def _count_classes(self, content: str, language: str) -> int:
        """Count class definitions."""
        patterns = {
            "python": r'\bclass\s+\w+',
            "javascript": r'\bclass\s+\w+',
            "typescript": r'\bclass\s+\w+',
            "java": r'\bclass\s+\w+',
            "kotlin": r'\bclass\s+\w+',
            "rust": r'\bstruct\s+\w+|\bimpl\s+\w+',
            "ruby": r'\bclass\s+\w+',
        }
        
        pattern = patterns.get(language)
        if not pattern:
            return 0
        
        return len(re.findall(pattern, content))
    
    def _analyze_imports(self, content: str, language: str) -> dict[str, int]:
        """Analyze import statements."""
        result = {"total": 0, "external": 0, "internal": 0}
        
        # Extract imports based on language
        imports = []
        
        if language == "python":
            imports = re.findall(r'^(?:from|import)\s+([a-zA-Z_][a-zA-Z0-9_\.]*)', content, re.MULTILINE)
        elif language in ["javascript", "typescript"]:
            imports = re.findall(r'import\s+.*?from\s+[\'"]([^\'"]+)[\'"]', content)
            imports.extend(re.findall(r'require\s*\(\s*[\'"]([^\'"]+)[\'"]', content))
        elif language == "go":
            imports = re.findall(r'"([^"]+)"', content)
        elif language in ["java", "kotlin"]:
            imports = re.findall(r'^import\s+([a-zA-Z0-9_.]+)', content, re.MULTILINE)
        
        result["total"] = len(imports)
        
        for imp in imports:
            # Heuristic: external if contains "/" or is known package
            if "/" in imp or imp.startswith("@") or "." not in imp:
                result["external"] += 1
            else:
                result["internal"] += 1
        
        return result
    
    def _count_magic_numbers(self, content: str, language: str) -> int:
        """Count magic numbers (excluding common ones like 0, 1, 2)."""
        # Find numbers not in common acceptable patterns
        numbers = re.findall(r'\b(\d{2,})\b', content)
        
        # Exclude common acceptable values
        acceptable = {"10", "100", "1000", "60", "24", "365", "30", "31", "12"}
        
        magic = 0
        for num in numbers:
            if num not in acceptable:
                # Check if it's part of a constant definition
                # This is a simplified check
                magic += 1
        
        return min(magic, 50)  # Cap to avoid noise
    
    def _has_docstrings(self, content: str, language: str) -> bool:
        """Check if file has documentation strings."""
        if language == "python":
            return bool(re.search(r'"""[\s\S]*?"""', content) or re.search(r"'''[\s\S]*?'''", content))
        elif language in ["javascript", "typescript"]:
            return bool(re.search(r'/\*\*[\s\S]*?\*/', content))
        elif language in ["java", "kotlin"]:
            return bool(re.search(r'/\*\*[\s\S]*?\*/', content))
        elif language == "go":
            return bool(re.search(r'//\s*\w+\s+', content))  # Go doc comments
        return False
    
    def _has_type_hints(self, content: str, language: str) -> bool:
        """Check if file uses type hints/annotations."""
        if language == "python":
            return bool(re.search(r':\s*\w+\s*[=,)]|def\s+\w+\([^)]*:\s*\w+', content))
        elif language == "typescript":
            return True  # TypeScript inherently has types
        elif language in ["java", "kotlin", "go", "rust"]:
            return True  # Statically typed
        return False
    
    def _count_error_handlers(self, content: str, language: str) -> int:
        """Count error handling blocks."""
        patterns = [
            r'\btry\s*[:{]',
            r'\bcatch\s*\(',
            r'\bexcept\s*[\w(:]',
            r'\brescue\s',
            r'\brecover\s*\(',
        ]
        
        count = 0
        for pattern in patterns:
            count += len(re.findall(pattern, content))
        
        return count
    
    def _count_logging(self, content: str, language: str) -> int:
        """Count logging statements."""
        patterns = [
            r'logger\.',
            r'logging\.',
            r'console\.(log|error|warn|info|debug)',
            r'log\.(info|error|warn|debug|trace)',
            r'Log\.(d|e|w|i|v)',
            r'slog\.',
            r'println!|eprintln!',
        ]
        
        count = 0
        for pattern in patterns:
            count += len(re.findall(pattern, content, re.IGNORECASE))
        
        return count
    
    def _calculate_complexity_score(self, complexity: FileComplexity) -> int:
        """Calculate overall complexity score (0-100, higher = more complex)."""
        score = 0
        
        # Lines of code factor (0-20)
        if complexity.lines_of_code > 1000:
            score += 20
        elif complexity.lines_of_code > 500:
            score += 15
        elif complexity.lines_of_code > 300:
            score += 10
        elif complexity.lines_of_code > 100:
            score += 5
        
        # Cyclomatic complexity (0-25)
        if complexity.cyclomatic_complexity > 50:
            score += 25
        elif complexity.cyclomatic_complexity > 30:
            score += 20
        elif complexity.cyclomatic_complexity > 20:
            score += 15
        elif complexity.cyclomatic_complexity > 10:
            score += 10
        elif complexity.cyclomatic_complexity > 5:
            score += 5
        
        # Nesting depth (0-15)
        if complexity.max_nesting_depth > 6:
            score += 15
        elif complexity.max_nesting_depth > 4:
            score += 10
        elif complexity.max_nesting_depth > 3:
            score += 5
        
        # Function length (0-15)
        if complexity.longest_function > 100:
            score += 15
        elif complexity.longest_function > 50:
            score += 10
        elif complexity.longest_function > 30:
            score += 5
        
        # Technical debt (0-15)
        debt_count = complexity.todo_count + complexity.fixme_count + complexity.hack_count
        if debt_count > 10:
            score += 15
        elif debt_count > 5:
            score += 10
        elif debt_count > 2:
            score += 5
        
        # Lack of quality indicators (0-10)
        if not complexity.has_docstrings:
            score += 5
        if not complexity.has_type_hints:
            score += 5
        
        return min(score, 100)
    
    def _analyze_test_file(
        self,
        content: str,
        file_path: Path,
        analysis: FileAnalysis
    ) -> None:
        """Analyze test file."""
        self.metrics.test_files += 1
        self.metrics.test_lines += len(content.split("\n"))
        
        # Count test functions
        test_patterns = [
            r'def test_\w+',
            r'it\s*\([\'"]',
            r'@Test',
            r'func Test\w+',
            r'#\[test\]',
        ]
        
        test_count = 0
        for pattern in test_patterns:
            test_count += len(re.findall(pattern, content))
        
        self.metrics.test_functions += test_count
        
        # Try to map test file to source file
        source_name = file_path.stem.replace("test_", "").replace("_test", "").replace(".test", "").replace(".spec", "")
        self._test_file_mapping[source_name] = str(file_path)
        
        analysis.entities.append(Entity(
            name=f"Tests: {file_path.name}",
            entity_type=EntityType.MODULE,
            description=f"Test file with {test_count} tests",
            source=str(file_path),
            properties={"test_count": test_count}
        ))
        
        analysis.security_controls.append("has_tests")
    
    def _analyze_config_file(
        self,
        content: str,
        file_path: Path,
        analysis: FileAnalysis
    ) -> None:
        """Analyze configuration files."""
        self.metrics.config_files += 1
        name = file_path.name.lower()
        
        # Check for tooling configs
        if any(x in name for x in ["eslint", "prettier", "black", "ruff", "flake8"]):
            if "lint" in name or "eslint" in name:
                self.metrics.has_linting_config = True
            if "prettier" in name or "black" in name:
                self.metrics.has_formatting_config = True
        
        # Check for dependency locks
        lock_files = ["package-lock.json", "yarn.lock", "poetry.lock", 
                     "pipfile.lock", "cargo.lock", "gemfile.lock", "go.sum"]
        if name in lock_files:
            self.metrics.has_dependency_lock = True
            analysis.security_controls.append("dependency_lock")
        
        analysis.entities.append(Entity(
            name=f"Config: {file_path.name}",
            entity_type=EntityType.DATA,
            description="Configuration file",
            source=str(file_path),
        ))
    
    def _analyze_ci_cd_file(
        self,
        content: str,
        file_path: Path,
        analysis: FileAnalysis
    ) -> None:
        """Analyze CI/CD configuration."""
        self.metrics.has_ci_cd = True
        
        analysis.entities.append(Entity(
            name=f"CI/CD: {file_path.name}",
            entity_type=EntityType.SERVICE,
            description="CI/CD pipeline",
            source=str(file_path),
        ))
        
        # Check for quality gates
        quality_gates = [
            (r'snyk|dependabot|renovate', "dependency_scanning"),
            (r'sonar|codeclimate|codeql', "code_analysis"),
            (r'test|pytest|jest|rspec', "automated_testing"),
            (r'lint|eslint|pylint', "linting"),
            (r'coverage', "coverage_check"),
        ]
        
        for pattern, control in quality_gates:
            if re.search(pattern, content, re.IGNORECASE):
                analysis.security_controls.append(control)
    
    def _analyze_documentation(
        self,
        content: str,
        file_path: Path,
        analysis: FileAnalysis
    ) -> None:
        """Analyze documentation files."""
        self.metrics.documentation_files += 1
        
        analysis.entities.append(Entity(
            name=f"Doc: {file_path.name}",
            entity_type=EntityType.MODULE,
            description="Documentation",
            source=str(file_path),
        ))
        
        analysis.security_controls.append("has_documentation")
    
    def get_metrics(self) -> EngineeringMetrics:
        """Return aggregated engineering metrics."""
        # Calculate final aggregates
        if self.metrics.source_files > 0:
            total_complexity = sum(fc.cyclomatic_complexity for fc in self._file_complexities)
            self.metrics.avg_cyclomatic_complexity = total_complexity / self.metrics.source_files
            self.metrics.max_cyclomatic_complexity = max(
                (fc.cyclomatic_complexity for fc in self._file_complexities), default=0
            )
        
        if self.metrics.logical_lines > 0 and self.metrics.test_lines > 0:
            self.metrics.test_to_code_ratio = self.metrics.test_lines / self.metrics.logical_lines
        
        # Determine overall effort
        self._calculate_overall_effort()
        
        return self.metrics
    
    def _calculate_overall_effort(self) -> None:
        """Calculate overall implementation effort assessment."""
        factors = []
        score = 0
        
        # Complexity factors
        if self.metrics.avg_cyclomatic_complexity > 20:
            score += 3
            factors.append("High average cyclomatic complexity")
        elif self.metrics.avg_cyclomatic_complexity > 10:
            score += 2
            factors.append("Moderate cyclomatic complexity")
        
        if self.metrics.complex_files > 5:
            score += 2
            factors.append(f"{self.metrics.complex_files} high-complexity files")
        
        if self.metrics.long_files > 5:
            score += 1
            factors.append(f"{self.metrics.long_files} large files (>500 lines)")
        
        # Technical debt
        total_debt = self.metrics.total_todos + self.metrics.total_fixmes + self.metrics.total_hacks
        if total_debt > 50:
            score += 2
            factors.append(f"Significant technical debt ({total_debt} items)")
        elif total_debt > 20:
            score += 1
            factors.append(f"Moderate technical debt ({total_debt} items)")
        
        # Test coverage
        if self.metrics.test_to_code_ratio < 0.3:
            score += 2
            factors.append("Low test coverage ratio")
        elif self.metrics.test_to_code_ratio < 0.5:
            score += 1
            factors.append("Moderate test coverage")
        
        # Documentation
        if self.metrics.files_with_docstrings < self.metrics.source_files * 0.3:
            score += 1
            factors.append("Limited documentation in code")
        
        # Infrastructure
        if not self.metrics.has_ci_cd:
            score += 1
            factors.append("No CI/CD pipeline detected")
        
        if not self.metrics.has_dependency_lock:
            score += 1
            factors.append("No dependency lock file")
        
        # Determine effort level
        if score <= 2:
            self.metrics.overall_effort = ImplementationEffort.LOW
        elif score <= 5:
            self.metrics.overall_effort = ImplementationEffort.MEDIUM
        elif score <= 8:
            self.metrics.overall_effort = ImplementationEffort.HIGH
        else:
            self.metrics.overall_effort = ImplementationEffort.VERY_HIGH
        
        self.metrics.effort_factors = factors
    
    def assess_implementation_effort(
        self,
        affected_files: list[str] | None = None,
        feature_scope: str = "medium"
    ) -> ImplementationAssessment:
        """
        Assess implementation effort for a proposed change.
        
        Args:
            affected_files: List of files that would be affected (if known)
            feature_scope: "small", "medium", "large" indicating feature size
            
        Returns:
            ImplementationAssessment with effort estimation and recommendations
        """
        assessment = ImplementationAssessment()
        
        # Analyze affected files if specified
        affected_complexities = []
        if affected_files:
            for file_path in affected_files:
                for fc in self._file_complexities:
                    if file_path in fc.path or fc.path.endswith(file_path):
                        affected_complexities.append(fc)
                        if fc.complexity_score > 70:
                            assessment.high_risk_files.append(fc.path)
        else:
            affected_complexities = self._file_complexities
        
        # Calculate base effort from scope
        scope_base = {"small": 1, "medium": 3, "large": 7}.get(feature_scope, 3)
        effort_score = scope_base
        
        # Factor in codebase complexity
        if affected_complexities:
            avg_complexity = sum(fc.complexity_score for fc in affected_complexities) / len(affected_complexities)
            
            if avg_complexity > 70:
                effort_score += 4
                assessment.complexity_factors.append(f"High complexity in affected code (avg score: {avg_complexity:.0f}/100)")
            elif avg_complexity > 50:
                effort_score += 2
                assessment.complexity_factors.append(f"Moderate complexity in affected code (avg score: {avg_complexity:.0f}/100)")
            
            # Nesting depth
            max_nesting = max(fc.max_nesting_depth for fc in affected_complexities)
            if max_nesting > 5:
                effort_score += 1
                assessment.complexity_factors.append(f"Deep nesting detected (max depth: {max_nesting})")
        
        # Factor in technical debt
        total_debt = self.metrics.total_todos + self.metrics.total_fixmes
        if total_debt > 30:
            effort_score += 2
            assessment.risk_factors.append(f"High technical debt ({total_debt} TODO/FIXME items)")
        
        # Factor in test coverage
        if self.metrics.test_to_code_ratio < 0.3:
            effort_score += 2
            assessment.risk_factors.append("Low test coverage - changes may introduce regressions")
            assessment.areas_needing_tests.append("Most source files lack corresponding tests")
        
        # Check for mitigating factors
        if self.metrics.has_ci_cd:
            effort_score -= 1
            assessment.mitigating_factors.append("CI/CD pipeline will catch issues early")
        
        if self.metrics.has_dependency_lock:
            assessment.mitigating_factors.append("Dependency versions are locked")
        
        if self.metrics.files_with_type_hints > self.metrics.source_files * 0.5:
            assessment.mitigating_factors.append("Good type coverage provides safety net")
        
        if self.metrics.has_linting_config:
            assessment.mitigating_factors.append("Linting config ensures code quality")
        
        # Determine effort level and time estimate
        effort_score = max(1, effort_score)
        
        if effort_score <= 2:
            assessment.effort_level = ImplementationEffort.TRIVIAL
            assessment.estimated_days = "< 1 day"
        elif effort_score <= 4:
            assessment.effort_level = ImplementationEffort.LOW
            assessment.estimated_days = "1-2 days"
        elif effort_score <= 7:
            assessment.effort_level = ImplementationEffort.MEDIUM
            assessment.estimated_days = "3-5 days"
        elif effort_score <= 10:
            assessment.effort_level = ImplementationEffort.HIGH
            assessment.estimated_days = "1-2 weeks"
        else:
            assessment.effort_level = ImplementationEffort.VERY_HIGH
            assessment.estimated_days = "2+ weeks"
        
        # Generate recommendations
        if not self.metrics.has_ci_cd:
            assessment.recommendations.append("Set up CI/CD pipeline before major changes")
        
        if self.metrics.test_to_code_ratio < 0.5:
            assessment.recommendations.append("Add tests for critical paths before implementing")
        
        if assessment.high_risk_files:
            assessment.recommendations.append(f"Consider refactoring high-complexity files first: {', '.join(Path(f).name for f in assessment.high_risk_files[:3])}")
        
        if total_debt > 20:
            assessment.recommendations.append("Address some technical debt before adding new features")
        
        if self.metrics.files_with_docstrings < self.metrics.source_files * 0.3:
            assessment.recommendations.append("Improve documentation to aid implementation")
        
        # Confidence based on analysis coverage
        assessment.confidence = min(0.95, 0.5 + (len(self._file_complexities) / 100))
        
        # Generate summary
        assessment.summary = (
            f"Implementation effort: {assessment.effort_level.value.upper()} ({assessment.estimated_days}). "
            f"Codebase has {self.metrics.source_files} source files with "
            f"average complexity score of {self.metrics.avg_cyclomatic_complexity:.1f}. "
        )
        
        if assessment.risk_factors:
            assessment.summary += f"Key risks: {'; '.join(assessment.risk_factors[:2])}. "
        
        if assessment.mitigating_factors:
            assessment.summary += f"Positive factors: {'; '.join(assessment.mitigating_factors[:2])}."
        
        return assessment
    
    def get_file_complexities(self) -> list[FileComplexity]:
        """Return list of per-file complexity analysis."""
        return sorted(self._file_complexities, key=lambda x: x.complexity_score, reverse=True)
    
    def get_high_risk_files(self, threshold: int = 70) -> list[FileComplexity]:
        """Return files with complexity score above threshold."""
        return [fc for fc in self._file_complexities if fc.complexity_score >= threshold]
    
    def reset_metrics(self) -> None:
        """Reset all metrics for a new analysis."""
        self.metrics = EngineeringMetrics()
        self._file_complexities = []
        self._test_file_mapping = {}
