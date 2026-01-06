"""
Codebase Analyzer - Extract security-relevant state from codebases.

Analyzes source code to build a map of:
- API endpoints
- Data models
- Authentication patterns
- Trust boundaries
- Security controls
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from context_graph.core.models import (
    State,
    Entity,
    EntityType,
    Relationship,
    RelationshipType,
)


@dataclass
class FileAnalysis:
    """Analysis result for a single file."""
    
    path: Path
    language: str
    entities: list[Entity] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    api_endpoints: list[dict[str, Any]] = field(default_factory=list)
    data_models: list[dict[str, Any]] = field(default_factory=list)
    auth_patterns: list[dict[str, Any]] = field(default_factory=list)
    security_controls: list[str] = field(default_factory=list)
    lines_of_code: int = 0


class CodebaseAnalyzer(ABC):
    """
    Abstract base class for codebase analyzers.
    
    Subclass for specific languages (Python, TypeScript, etc.)
    """
    
    def __init__(
        self,
        exclude_patterns: list[str] | None = None,
    ) -> None:
        self.exclude_patterns = exclude_patterns or [
            "node_modules",
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            "dist",
            "build",
            ".pytest_cache",
            "*.pyc",
            "*.egg-info",
        ]
    
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Return list of file extensions this analyzer supports."""
        pass
    
    @abstractmethod
    def analyze_file(self, file_path: Path) -> FileAnalysis:
        """Analyze a single file."""
        pass
    
    def analyze_codebase(self, root_path: Path) -> State:
        """
        Analyze an entire codebase.
        
        Args:
            root_path: Root directory of the codebase
            
        Returns:
            State object representing current codebase state
        """
        state = State(codebase_path=str(root_path))
        
        files = self._discover_files(root_path)
        
        for file_path in files:
            try:
                analysis = self.analyze_file(file_path)
                
                state.entities.extend(analysis.entities)
                state.relationships.extend(analysis.relationships)
                state.api_endpoints.extend(analysis.api_endpoints)
                state.data_models.extend(analysis.data_models)
                state.auth_patterns.extend(analysis.auth_patterns)
                state.existing_controls.extend(analysis.security_controls)
                state.lines_of_code += analysis.lines_of_code
                state.files_analyzed += 1
                
            except Exception as e:
                # Log error but continue with other files
                print(f"Warning: Failed to analyze {file_path}: {e}")
        
        # Deduplicate
        state.existing_controls = list(set(state.existing_controls))
        
        return state
    
    def _discover_files(self, root_path: Path) -> list[Path]:
        """Discover all analyzable files in a directory."""
        files: list[Path] = []
        extensions = self.supported_extensions()
        
        for ext in extensions:
            for file_path in root_path.rglob(f"*{ext}"):
                if not self._should_exclude(file_path):
                    files.append(file_path)
        
        return files
    
    def _should_exclude(self, path: Path) -> bool:
        """Check if a path should be excluded from analysis."""
        path_str = str(path)
        
        for pattern in self.exclude_patterns:
            if pattern.startswith("*"):
                # Glob pattern
                if path_str.endswith(pattern[1:]):
                    return True
            else:
                # Directory/file name
                if pattern in path_str:
                    return True
        
        return False
    
    def _extract_security_patterns(self, content: str) -> list[str]:
        """Extract common security control patterns from code."""
        controls: list[str] = []
        
        patterns = {
            "authentication": [
                r'@login_required',
                r'@authenticated',
                r'requireAuth',
                r'isAuthenticated',
                r'jwt\.verify',
                r'passport\.',
            ],
            "authorization": [
                r'@permission',
                r'@role',
                r'hasPermission',
                r'checkRole',
                r'can\(',
                r'authorize',
            ],
            "input_validation": [
                r'@validate',
                r'validator\.',
                r'\.validate\(',
                r'sanitize',
                r'escape',
                r'Joi\.',
                r'zod\.',
            ],
            "encryption": [
                r'encrypt',
                r'decrypt',
                r'bcrypt',
                r'argon2',
                r'crypto\.',
                r'hashlib',
            ],
            "rate_limiting": [
                r'rateLimit',
                r'throttle',
                r'@rate_limit',
            ],
            "csrf_protection": [
                r'csrf',
                r'@csrf',
                r'csrfToken',
            ],
            "cors": [
                r'cors\(',
                r'CORS',
                r'Access-Control',
            ],
            "logging": [
                r'logger\.',
                r'logging\.',
                r'audit',
                r'\.log\(',
            ],
        }
        
        for control_type, regexes in patterns.items():
            for regex in regexes:
                if re.search(regex, content, re.IGNORECASE):
                    controls.append(control_type)
                    break
        
        return controls


class MultiLanguageAnalyzer(CodebaseAnalyzer):
    """
    Analyzer that combines multiple language-specific analyzers.
    """
    
    def __init__(
        self,
        analyzers: list[CodebaseAnalyzer] | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> None:
        super().__init__(exclude_patterns)
        self._analyzers = analyzers or []
    
    def add_analyzer(self, analyzer: CodebaseAnalyzer) -> None:
        """Add a language-specific analyzer."""
        self._analyzers.append(analyzer)
    
    def supported_extensions(self) -> list[str]:
        """Return all supported extensions."""
        extensions: list[str] = []
        for analyzer in self._analyzers:
            extensions.extend(analyzer.supported_extensions())
        return list(set(extensions))
    
    def analyze_file(self, file_path: Path) -> FileAnalysis:
        """Analyze a file using the appropriate analyzer."""
        suffix = file_path.suffix
        
        for analyzer in self._analyzers:
            if suffix in analyzer.supported_extensions():
                return analyzer.analyze_file(file_path)
        
        # Fallback: basic analysis
        return self._basic_analysis(file_path)
    
    def _basic_analysis(self, file_path: Path) -> FileAnalysis:
        """Basic analysis when no specific analyzer matches."""
        try:
            content = file_path.read_text(encoding="utf-8")
            lines = len(content.split("\n"))
            security_controls = self._extract_security_patterns(content)
            
            return FileAnalysis(
                path=file_path,
                language="unknown",
                security_controls=security_controls,
                lines_of_code=lines,
            )
        except Exception:
            return FileAnalysis(path=file_path, language="unknown")
    
    def analyze_codebase(self, root_path: Path) -> State:
        """Analyze codebase with all registered analyzers."""
        state = State(codebase_path=str(root_path))
        
        for analyzer in self._analyzers:
            partial_state = analyzer.analyze_codebase(root_path)
            
            state.entities.extend(partial_state.entities)
            state.relationships.extend(partial_state.relationships)
            state.api_endpoints.extend(partial_state.api_endpoints)
            state.data_models.extend(partial_state.data_models)
            state.auth_patterns.extend(partial_state.auth_patterns)
            state.existing_controls.extend(partial_state.existing_controls)
            state.lines_of_code += partial_state.lines_of_code
            state.files_analyzed += partial_state.files_analyzed
        
        # Deduplicate controls
        state.existing_controls = list(set(state.existing_controls))
        
        return state

