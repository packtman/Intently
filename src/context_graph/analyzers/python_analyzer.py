"""
Python Codebase Analyzer - Extract security-relevant patterns from Python code.

Identifies:
- Flask/FastAPI/Django endpoints
- SQLAlchemy/Django models
- Authentication decorators
- Database queries
- Sensitive data handling
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

from context_graph.core.models import Entity, EntityType, Relationship, RelationshipType
from context_graph.analyzers.codebase_analyzer import CodebaseAnalyzer, FileAnalysis


class PythonAnalyzer(CodebaseAnalyzer):
    """Analyze Python codebases for security-relevant patterns."""
    
    def supported_extensions(self) -> list[str]:
        return [".py"]
    
    def analyze_file(self, file_path: Path) -> FileAnalysis:
        """Analyze a Python file."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return FileAnalysis(path=file_path, language="python")
        
        analysis = FileAnalysis(
            path=file_path,
            language="python",
            lines_of_code=len(content.split("\n")),
        )
        
        # Try AST parsing
        try:
            tree = ast.parse(content)
            self._analyze_ast(tree, file_path, analysis)
        except SyntaxError:
            # Fall back to regex-based analysis
            pass
        
        # Always do regex-based analysis for patterns AST might miss
        self._analyze_patterns(content, file_path, analysis)
        
        return analysis
    
    def _analyze_ast(
        self, 
        tree: ast.AST, 
        file_path: Path, 
        analysis: FileAnalysis
    ) -> None:
        """Analyze Python AST for security-relevant patterns."""
        for node in ast.walk(tree):
            # Find classes (potential data models)
            if isinstance(node, ast.ClassDef):
                self._analyze_class(node, file_path, analysis)
            
            # Find functions (potential endpoints)
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                self._analyze_function(node, file_path, analysis)
    
    def _analyze_class(
        self, 
        node: ast.ClassDef, 
        file_path: Path, 
        analysis: FileAnalysis
    ) -> None:
        """Analyze a class definition."""
        # Check for ORM model patterns
        base_names = [
            self._get_name(base) for base in node.bases
        ]
        
        is_model = any(
            name in ["Base", "Model", "db.Model", "BaseModel", "Document"]
            for name in base_names
        )
        
        if is_model:
            model_info = {
                "name": node.name,
                "file": str(file_path),
                "line": node.lineno,
                "fields": [],
            }
            
            # Extract fields
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and item.target:
                    field_name = self._get_name(item.target)
                    if field_name:
                        model_info["fields"].append(field_name)
                elif isinstance(item, ast.Assign):
                    for target in item.targets:
                        field_name = self._get_name(target)
                        if field_name:
                            model_info["fields"].append(field_name)
            
            analysis.data_models.append(model_info)
            
            # Create entity
            entity = Entity(
                name=node.name,
                entity_type=EntityType.DATA,
                description=f"Data model from {file_path.name}",
                source=str(file_path),
                is_sensitive=self._is_sensitive_model(node.name, model_info["fields"]),
            )
            analysis.entities.append(entity)
    
    def _analyze_function(
        self, 
        node: ast.FunctionDef | ast.AsyncFunctionDef, 
        file_path: Path, 
        analysis: FileAnalysis
    ) -> None:
        """Analyze a function definition."""
        # Check decorators for route/endpoint patterns
        for decorator in node.decorator_list:
            decorator_name = self._get_decorator_name(decorator)
            
            # Flask/FastAPI route patterns
            if decorator_name in ["route", "get", "post", "put", "patch", "delete", "api_view"]:
                endpoint_info = self._extract_endpoint_info(decorator, node, file_path)
                if endpoint_info:
                    analysis.api_endpoints.append(endpoint_info)
                    
                    # Create entity
                    entity = Entity(
                        name=endpoint_info.get("path", node.name),
                        entity_type=EntityType.ENDPOINT,
                        description=f"API endpoint from {file_path.name}",
                        source=str(file_path),
                        requires_auth=endpoint_info.get("requires_auth", False),
                    )
                    analysis.entities.append(entity)
            
            # Auth decorators
            elif decorator_name in [
                "login_required", "authenticated", "permission_required",
                "requires_auth", "jwt_required", "token_required"
            ]:
                analysis.auth_patterns.append({
                    "type": "decorator",
                    "name": decorator_name,
                    "function": node.name,
                    "file": str(file_path),
                    "line": node.lineno,
                })
    
    def _get_decorator_name(self, decorator: ast.expr) -> str:
        """Extract decorator name from AST node."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return decorator.attr
        elif isinstance(decorator, ast.Call):
            return self._get_decorator_name(decorator.func)
        return ""
    
    def _extract_endpoint_info(
        self, 
        decorator: ast.expr, 
        func: ast.FunctionDef | ast.AsyncFunctionDef,
        file_path: Path
    ) -> dict[str, Any] | None:
        """Extract endpoint information from a route decorator."""
        info: dict[str, Any] = {
            "function": func.name,
            "file": str(file_path),
            "line": func.lineno,
            "requires_auth": False,
        }
        
        # Get path from decorator arguments
        if isinstance(decorator, ast.Call) and decorator.args:
            first_arg = decorator.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                info["path"] = first_arg.value
        
        # Get method from decorator name or keywords
        decorator_name = self._get_decorator_name(decorator)
        if decorator_name in ["get", "post", "put", "patch", "delete"]:
            info["method"] = decorator_name.upper()
        elif isinstance(decorator, ast.Call):
            for keyword in decorator.keywords:
                if keyword.arg == "methods" and isinstance(keyword.value, ast.List):
                    methods = []
                    for elt in keyword.value.elts:
                        if isinstance(elt, ast.Constant):
                            methods.append(str(elt.value))
                    info["methods"] = methods
        
        # Check if function has auth decorators
        for dec in func.decorator_list:
            dec_name = self._get_decorator_name(dec)
            if dec_name in ["login_required", "authenticated", "requires_auth"]:
                info["requires_auth"] = True
                break
        
        return info if "path" in info or "method" in info else None
    
    def _get_name(self, node: ast.expr | None) -> str:
        """Get name from various AST node types."""
        if node is None:
            return ""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return ""
    
    def _is_sensitive_model(self, name: str, fields: list[str]) -> bool:
        """Check if a model contains sensitive data."""
        sensitive_patterns = [
            "user", "account", "auth", "credential", "password",
            "token", "secret", "payment", "billing", "personal",
        ]
        
        name_lower = name.lower()
        for pattern in sensitive_patterns:
            if pattern in name_lower:
                return True
        
        sensitive_fields = [
            "password", "email", "ssn", "phone", "address",
            "credit_card", "token", "secret", "api_key",
        ]
        
        for field in fields:
            field_lower = field.lower()
            for sensitive in sensitive_fields:
                if sensitive in field_lower:
                    return True
        
        return False
    
    def _analyze_patterns(
        self, 
        content: str, 
        file_path: Path, 
        analysis: FileAnalysis
    ) -> None:
        """Regex-based analysis for patterns AST might miss."""
        # Security controls
        analysis.security_controls.extend(self._extract_security_patterns(content))
        
        # SQL injection patterns (potential vulnerabilities)
        sql_patterns = [
            r'execute\s*\(\s*[\'"].*%s',  # String formatting in SQL
            r'execute\s*\(\s*f[\'"]',      # f-string in execute
            r'\.format\(.*\).*execute',     # format then execute
        ]
        
        for pattern in sql_patterns:
            if re.search(pattern, content):
                analysis.security_controls.append("potential_sql_injection")
                break
        
        # Hardcoded secrets patterns
        secret_patterns = [
            r'(?:password|secret|api_key|token)\s*=\s*[\'"][^\'"]+[\'"]',
            r'(?:AWS|AZURE|GCP)_(?:SECRET|KEY)\s*=\s*[\'"][^\'"]+[\'"]',
        ]
        
        for pattern in secret_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                analysis.security_controls.append("potential_hardcoded_secret")
                break
        
        # FastAPI/Flask endpoint patterns not caught by AST
        endpoint_patterns = [
            (r'@app\.(get|post|put|patch|delete)\s*\(\s*[\'"]([^\'"]+)[\'"]', "fastapi"),
            (r'@router\.(get|post|put|patch|delete)\s*\(\s*[\'"]([^\'"]+)[\'"]', "fastapi"),
            (r'@app\.route\s*\(\s*[\'"]([^\'"]+)[\'"]', "flask"),
            (r'@blueprint\.route\s*\(\s*[\'"]([^\'"]+)[\'"]', "flask"),
        ]
        
        for pattern, framework in endpoint_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                if framework == "fastapi":
                    method, path = match.groups()
                else:
                    path = match.group(1)
                    method = "GET"  # Default
                
                # Avoid duplicates
                if not any(e.get("path") == path for e in analysis.api_endpoints):
                    analysis.api_endpoints.append({
                        "path": path,
                        "method": method.upper() if framework == "fastapi" else None,
                        "framework": framework,
                        "file": str(file_path),
                    })

