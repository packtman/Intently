"""
TypeScript/JavaScript Codebase Analyzer.

Identifies:
- Express/Nest/Hono routes
- TypeORM/Prisma models
- Authentication middleware
- API endpoints
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from context_graph.core.models import Entity, EntityType
from context_graph.analyzers.codebase_analyzer import CodebaseAnalyzer, FileAnalysis


class TypeScriptAnalyzer(CodebaseAnalyzer):
    """Analyze TypeScript/JavaScript codebases."""
    
    def supported_extensions(self) -> list[str]:
        return [".ts", ".tsx", ".js", ".jsx"]
    
    def analyze_file(self, file_path: Path) -> FileAnalysis:
        """Analyze a TypeScript/JavaScript file."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return FileAnalysis(path=file_path, language="typescript")
        
        analysis = FileAnalysis(
            path=file_path,
            language="typescript",
            lines_of_code=len(content.split("\n")),
        )
        
        # Analyze patterns
        self._analyze_routes(content, file_path, analysis)
        self._analyze_models(content, file_path, analysis)
        self._analyze_auth_patterns(content, file_path, analysis)
        analysis.security_controls.extend(self._extract_security_patterns(content))
        
        return analysis
    
    def _analyze_routes(
        self, 
        content: str, 
        file_path: Path, 
        analysis: FileAnalysis
    ) -> None:
        """Analyze Express/Nest/Hono route patterns."""
        # Express patterns
        express_patterns = [
            r'(?:app|router)\.(get|post|put|patch|delete)\s*\(\s*[\'"`]([^\'"]+)[\'"`]',
            r'(?:app|router)\.(?:use|all)\s*\(\s*[\'"`]([^\'"]+)[\'"`]',
        ]
        
        for pattern in express_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                groups = match.groups()
                if len(groups) == 2:
                    method, path = groups
                else:
                    path = groups[0]
                    method = "ALL"
                
                endpoint = {
                    "path": path,
                    "method": method.upper(),
                    "framework": "express",
                    "file": str(file_path),
                }
                analysis.api_endpoints.append(endpoint)
                
                analysis.entities.append(Entity(
                    name=path,
                    entity_type=EntityType.ENDPOINT,
                    description=f"Express endpoint: {method.upper()} {path}",
                    source=str(file_path),
                ))
        
        # NestJS patterns
        nest_patterns = [
            r'@(Get|Post|Put|Patch|Delete)\s*\(\s*[\'"`]?([^\'")\s]*)[\'"`]?\s*\)',
            r'@Controller\s*\(\s*[\'"`]([^\'"]+)[\'"`]\s*\)',
        ]
        
        controller_prefix = ""
        for match in re.finditer(r'@Controller\s*\(\s*[\'"`]([^\'"]+)[\'"`]\s*\)', content):
            controller_prefix = match.group(1)
        
        for pattern in nest_patterns[:1]:  # Just route decorators
            for match in re.finditer(pattern, content):
                method = match.group(1)
                path = match.group(2) if match.group(2) else ""
                full_path = f"/{controller_prefix}/{path}".replace("//", "/")
                
                endpoint = {
                    "path": full_path,
                    "method": method.upper(),
                    "framework": "nestjs",
                    "file": str(file_path),
                }
                analysis.api_endpoints.append(endpoint)
        
        # Hono patterns
        hono_patterns = [
            r'(?:app|router)\.(get|post|put|patch|delete)\s*\(\s*[\'"`]([^\'"]+)[\'"`]',
        ]
        
        if "from 'hono'" in content or 'from "hono"' in content:
            for pattern in hono_patterns:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    method, path = match.groups()
                    
                    endpoint = {
                        "path": path,
                        "method": method.upper(),
                        "framework": "hono",
                        "file": str(file_path),
                    }
                    analysis.api_endpoints.append(endpoint)
    
    def _analyze_models(
        self, 
        content: str, 
        file_path: Path, 
        analysis: FileAnalysis
    ) -> None:
        """Analyze TypeORM/Prisma/Mongoose model patterns."""
        # TypeORM Entity pattern
        entity_pattern = r'@Entity\s*\([^\)]*\)\s*(?:export\s+)?class\s+(\w+)'
        for match in re.finditer(entity_pattern, content):
            model_name = match.group(1)
            
            model_info = {
                "name": model_name,
                "framework": "typeorm",
                "file": str(file_path),
                "fields": self._extract_typeorm_fields(content, model_name),
            }
            analysis.data_models.append(model_info)
            
            analysis.entities.append(Entity(
                name=model_name,
                entity_type=EntityType.DATA,
                description=f"TypeORM entity from {file_path.name}",
                source=str(file_path),
                is_sensitive=self._is_sensitive_model(model_name, model_info["fields"]),
            ))
        
        # Prisma model (usually in schema.prisma, but might be referenced)
        prisma_pattern = r'model\s+(\w+)\s*\{'
        for match in re.finditer(prisma_pattern, content):
            model_name = match.group(1)
            
            analysis.data_models.append({
                "name": model_name,
                "framework": "prisma",
                "file": str(file_path),
            })
        
        # Mongoose Schema
        mongoose_pattern = r'new\s+(?:mongoose\.)?Schema\s*\(\s*\{'
        if re.search(mongoose_pattern, content):
            # Try to find the variable name
            var_pattern = r'(?:const|let|var)\s+(\w+)(?:Schema)?\s*=\s*new\s+(?:mongoose\.)?Schema'
            for match in re.finditer(var_pattern, content):
                model_name = match.group(1)
                
                analysis.data_models.append({
                    "name": model_name,
                    "framework": "mongoose",
                    "file": str(file_path),
                })
        
        # Interface/Type definitions (potential DTOs)
        interface_pattern = r'(?:export\s+)?interface\s+(\w+)(?:DTO|Request|Response|Input|Output)'
        for match in re.finditer(interface_pattern, content):
            dto_name = match.group(1)
            
            analysis.data_models.append({
                "name": dto_name,
                "type": "dto",
                "file": str(file_path),
            })
    
    def _extract_typeorm_fields(self, content: str, entity_name: str) -> list[str]:
        """Extract fields from TypeORM entity."""
        fields: list[str] = []
        
        # Find the class body
        class_pattern = rf'class\s+{entity_name}\s*(?:extends[^{{]+)?\{{'
        match = re.search(class_pattern, content)
        if not match:
            return fields
        
        # Simple field extraction
        field_pattern = r'@Column[^\n]*\n\s*(\w+)\s*[?!]?\s*:'
        for field_match in re.finditer(field_pattern, content[match.end():]):
            fields.append(field_match.group(1))
            if len(fields) > 50:  # Limit
                break
        
        return fields
    
    def _analyze_auth_patterns(
        self, 
        content: str, 
        file_path: Path, 
        analysis: FileAnalysis
    ) -> None:
        """Analyze authentication patterns."""
        # Middleware patterns
        middleware_patterns = [
            (r'(?:use|app\.use)\s*\(\s*(?:auth|authenticate|requireAuth|isAuthenticated)', "middleware"),
            (r'@(?:UseGuards|Auth|Authenticated|RequireAuth)', "decorator"),
            (r'passport\.(authenticate|use)', "passport"),
            (r'jwt\.verify|jsonwebtoken', "jwt"),
            (r'(?:session|cookie)\s*\(', "session"),
        ]
        
        for pattern, auth_type in middleware_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                analysis.auth_patterns.append({
                    "type": auth_type,
                    "file": str(file_path),
                })
        
        # Guards (NestJS)
        guard_pattern = r'@UseGuards\s*\(\s*(\w+)'
        for match in re.finditer(guard_pattern, content):
            analysis.auth_patterns.append({
                "type": "guard",
                "name": match.group(1),
                "file": str(file_path),
            })
    
    def _is_sensitive_model(self, name: str, fields: list[str]) -> bool:
        """Check if model contains sensitive data."""
        sensitive_names = ["user", "account", "auth", "credential", "password", "payment"]
        sensitive_fields = ["password", "email", "ssn", "token", "secret", "creditCard"]
        
        name_lower = name.lower()
        for sens in sensitive_names:
            if sens in name_lower:
                return True
        
        for field in fields:
            field_lower = field.lower()
            for sens in sensitive_fields:
                if sens in field_lower:
                    return True
        
        return False

