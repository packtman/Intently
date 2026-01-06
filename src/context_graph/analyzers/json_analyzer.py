"""JSON/JSON Schema Analyzer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from context_graph.core.models import Entity, EntityType
from context_graph.analyzers.codebase_analyzer import CodebaseAnalyzer, FileAnalysis


class JSONAnalyzer(CodebaseAnalyzer):
    """Analyzer for JSON files including JSON Schema."""

    def supported_extensions(self) -> list[str]:
        return [".json"]

    def analyze_file(self, file_path: Path) -> FileAnalysis:
        """Analyze a JSON file."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return FileAnalysis(path=file_path, language="json")
        
        lines = content.split("\n")
        
        analysis = FileAnalysis(
            path=file_path,
            language="json",
            lines_of_code=len(lines),
        )

        try:
            data = json.loads(content)
            
            # Check if it's a JSON Schema
            if "$schema" in data or "type" in data or "properties" in data:
                self._analyze_json_schema(data, file_path, analysis)
            else:
                self._analyze_json_data(data, file_path, analysis)
                
        except json.JSONDecodeError:
            # Invalid JSON, just do basic security check
            analysis.security_controls.extend(self._extract_security_patterns(content))

        return analysis

    def _analyze_json_schema(
        self, 
        data: dict, 
        file_path: Path, 
        analysis: FileAnalysis
    ) -> None:
        """Analyze JSON Schema definitions."""
        # Get schema title/name
        schema_name = data.get("title", file_path.stem)
        
        analysis.data_models.append({
            "name": schema_name,
            "type": data.get("type", "object"),
            "framework": "json_schema",
            "file": str(file_path),
        })
        
        analysis.entities.append(Entity(
            name=schema_name,
            entity_type=EntityType.DATA,
            description=f"JSON Schema: {schema_name}",
            source=str(file_path),
        ))

        # Extract properties
        if "properties" in data:
            for prop_name, prop_def in data["properties"].items():
                is_sensitive = self._is_sensitive_field(prop_name)
                
                analysis.entities.append(Entity(
                    name=f"{schema_name}.{prop_name}",
                    entity_type=EntityType.DATA,
                    description=f"Property: {prop_name} ({prop_def.get('type', 'any')})",
                    source=str(file_path),
                    is_sensitive=is_sensitive,
                ))

        # Check definitions/components
        definitions = data.get("definitions", data.get("$defs", {}))
        for def_name, def_schema in definitions.items():
            analysis.data_models.append({
                "name": def_name,
                "type": def_schema.get("type", "object"),
                "framework": "json_schema",
                "file": str(file_path),
            })
            
            analysis.entities.append(Entity(
                name=def_name,
                entity_type=EntityType.DATA,
                description=f"JSON Schema definition: {def_name}",
                source=str(file_path),
            ))

    def _analyze_json_data(
        self, 
        data: Any, 
        file_path: Path, 
        analysis: FileAnalysis
    ) -> None:
        """Analyze regular JSON data/config."""
        def check_sensitive(obj: Any, path: str = "") -> None:
            """Recursively check for sensitive data."""
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    
                    if self._is_sensitive_field(key):
                        analysis.entities.append(Entity(
                            name=f"Config: {current_path}",
                            entity_type=EntityType.DATA,
                            description=f"Sensitive config at: {current_path}",
                            source=str(file_path),
                            is_sensitive=True,
                        ))
                    
                    check_sensitive(value, current_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_sensitive(item, f"{path}[{i}]")

        check_sensitive(data)

    def _is_sensitive_field(self, field_name: str) -> bool:
        """Check if a field name suggests sensitive data."""
        sensitive_keywords = [
            "password", "secret", "key", "token", "auth", 
            "credential", "api_key", "private", "ssn", "credit"
        ]
        field_lower = field_name.lower()
        return any(kw in field_lower for kw in sensitive_keywords)
