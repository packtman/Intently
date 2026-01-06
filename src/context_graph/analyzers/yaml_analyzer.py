"""YAML/OpenAPI Analyzer for configuration and API specs."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from context_graph.core.models import Entity, EntityType
from context_graph.analyzers.codebase_analyzer import CodebaseAnalyzer, FileAnalysis


class YAMLAnalyzer(CodebaseAnalyzer):
    """Analyzer for YAML files including OpenAPI specs."""

    def supported_extensions(self) -> list[str]:
        return [".yaml", ".yml"]

    def analyze_file(self, file_path: Path) -> FileAnalysis:
        """Analyze a YAML file for API definitions and configurations."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return FileAnalysis(path=file_path, language="yaml")
        
        lines = content.split("\n")
        
        analysis = FileAnalysis(
            path=file_path,
            language="yaml",
            lines_of_code=len(lines),
        )

        # Detect if it's an OpenAPI spec
        is_openapi = "openapi:" in content or "swagger:" in content

        if is_openapi:
            self._analyze_openapi(content, lines, file_path, analysis)
        else:
            self._analyze_config(content, lines, file_path, analysis)
        
        analysis.security_controls.extend(self._extract_security_patterns(content))

        return analysis

    def _analyze_openapi(
        self, 
        content: str, 
        lines: list[str], 
        file_path: Path, 
        analysis: FileAnalysis
    ) -> None:
        """Extract OpenAPI spec information."""
        # Find paths/endpoints
        in_paths = False
        current_path = None

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Detect paths section
            if line.startswith("paths:"):
                in_paths = True
                continue

            if in_paths:
                # New path definition (e.g., /users:)
                path_match = re.match(r'^  ([\'"]?/[^:\'"]*[\'"]?):', line)
                if path_match:
                    current_path = path_match.group(1).strip("'\"")

                # HTTP methods
                method_match = re.match(r'^    (get|post|put|patch|delete|options|head):', line)
                if method_match and current_path:
                    method = method_match.group(1).upper()
                    
                    endpoint = {
                        "path": current_path,
                        "method": method,
                        "framework": "openapi",
                        "file": str(file_path),
                        "line": i + 1,
                    }
                    analysis.api_endpoints.append(endpoint)
                    
                    analysis.entities.append(Entity(
                        name=f"{method} {current_path}",
                        entity_type=EntityType.ENDPOINT,
                        description=f"OpenAPI endpoint: {method} {current_path}",
                        source=str(file_path),
                    ))

            # Find schemas/components
            schema_match = re.match(r'^    ([A-Z][a-zA-Z0-9_]+):', line)
            if schema_match:
                before_line = content[:content.find(line)]
                if "components:" in before_line or "definitions:" in before_line:
                    schema_name = schema_match.group(1)
                    
                    analysis.data_models.append({
                        "name": schema_name,
                        "framework": "openapi",
                        "file": str(file_path),
                        "line": i + 1,
                    })
                    
                    analysis.entities.append(Entity(
                        name=schema_name,
                        entity_type=EntityType.DATA,
                        description=f"OpenAPI schema: {schema_name}",
                        source=str(file_path),
                    ))

            # Security definitions
            if "securityschemes:" in stripped.lower():
                analysis.auth_patterns.append({
                    "type": "security_schemes",
                    "file": str(file_path),
                    "line": i + 1,
                })

            # Auth patterns
            if any(auth in stripped.lower() for auth in ["bearer", "oauth", "apikey", "api_key", "jwt"]):
                analysis.auth_patterns.append({
                    "type": "auth_config",
                    "file": str(file_path),
                    "line": i + 1,
                })

    def _analyze_config(
        self, 
        content: str, 
        lines: list[str], 
        file_path: Path, 
        analysis: FileAnalysis
    ) -> None:
        """Analyze general YAML configuration."""
        for i, line in enumerate(lines):
            stripped = line.strip()

            # Skip comments
            if stripped.startswith("#"):
                continue

            # Find security-sensitive configs
            if ":" in stripped and not stripped.endswith(":"):
                key = stripped.split(":")[0].strip()
                
                security_keywords = ["password", "secret", "key", "token", "auth", "credential", "api_key"]
                if any(kw in key.lower() for kw in security_keywords):
                    analysis.entities.append(Entity(
                        name=f"Config: {key}",
                        entity_type=EntityType.DATA,
                        description=f"Sensitive configuration: {key}",
                        source=str(file_path),
                        is_sensitive=True,
                    ))
