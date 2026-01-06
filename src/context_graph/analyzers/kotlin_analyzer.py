"""
Kotlin Codebase Analyzer - Extract security-relevant patterns from Kotlin code.

Identifies:
- Spring Boot / Ktor endpoints
- JPA/Exposed entities
- Security annotations
- API controllers
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from context_graph.core.models import Entity, EntityType, Relationship, RelationshipType
from context_graph.analyzers.codebase_analyzer import CodebaseAnalyzer, FileAnalysis


class KotlinAnalyzer(CodebaseAnalyzer):
    """Analyze Kotlin codebases for security-relevant patterns."""
    
    def supported_extensions(self) -> list[str]:
        return [".kt", ".kts"]
    
    def analyze_file(self, file_path: Path) -> FileAnalysis:
        """Analyze a Kotlin file."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return FileAnalysis(path=file_path, language="kotlin")
        
        analysis = FileAnalysis(
            path=file_path,
            language="kotlin",
            lines_of_code=len(content.split("\n")),
        )
        
        # Analyze patterns
        self._analyze_spring_endpoints(content, file_path, analysis)
        self._analyze_ktor_routes(content, file_path, analysis)
        self._analyze_data_classes(content, file_path, analysis)
        self._analyze_jpa_entities(content, file_path, analysis)
        self._analyze_security_annotations(content, file_path, analysis)
        analysis.security_controls.extend(self._extract_security_patterns(content))
        
        return analysis
    
    def _analyze_spring_endpoints(
        self, 
        content: str, 
        file_path: Path, 
        analysis: FileAnalysis
    ) -> None:
        """Analyze Spring Boot controller endpoints."""
        # Check if it's a Spring controller
        is_controller = any(
            annotation in content 
            for annotation in ["@RestController", "@Controller", "@RequestMapping"]
        )
        
        if not is_controller:
            return
        
        # Extract base path from class-level @RequestMapping
        base_path = ""
        class_mapping = re.search(
            r'@RequestMapping\s*\(\s*(?:value\s*=\s*)?["\']([^"\']+)["\']',
            content
        )
        if class_mapping:
            base_path = class_mapping.group(1)
        
        # Find endpoint methods
        endpoint_patterns = [
            (r'@GetMapping\s*\(\s*(?:value\s*=\s*)?["\']([^"\']*)["\']?\s*\)', "GET"),
            (r'@PostMapping\s*\(\s*(?:value\s*=\s*)?["\']([^"\']*)["\']?\s*\)', "POST"),
            (r'@PutMapping\s*\(\s*(?:value\s*=\s*)?["\']([^"\']*)["\']?\s*\)', "PUT"),
            (r'@DeleteMapping\s*\(\s*(?:value\s*=\s*)?["\']([^"\']*)["\']?\s*\)', "DELETE"),
            (r'@PatchMapping\s*\(\s*(?:value\s*=\s*)?["\']([^"\']*)["\']?\s*\)', "PATCH"),
            (r'@GetMapping(?!\s*\()', "GET"),  # No path specified
            (r'@PostMapping(?!\s*\()', "POST"),
            (r'@PutMapping(?!\s*\()', "PUT"),
            (r'@DeleteMapping(?!\s*\()', "DELETE"),
        ]
        
        for pattern, method in endpoint_patterns:
            for match in re.finditer(pattern, content):
                path = match.group(1) if match.lastindex else ""
                full_path = f"{base_path}{path}".replace("//", "/")
                if not full_path:
                    full_path = base_path or "/"
                
                # Check for security annotations near this endpoint
                # Look backwards for @PreAuthorize, @Secured, etc.
                match_pos = match.start()
                context_start = max(0, match_pos - 500)
                context = content[context_start:match_pos]
                
                requires_auth = any(
                    ann in context
                    for ann in ["@PreAuthorize", "@Secured", "@RolesAllowed", "@AuthenticationPrincipal"]
                )
                
                endpoint = {
                    "path": full_path,
                    "method": method,
                    "framework": "spring",
                    "file": str(file_path),
                    "requires_auth": requires_auth,
                }
                analysis.api_endpoints.append(endpoint)
                
                analysis.entities.append(Entity(
                    name=full_path,
                    entity_type=EntityType.ENDPOINT,
                    description=f"Spring Boot endpoint: {method} {full_path}",
                    source=str(file_path),
                    requires_auth=requires_auth,
                ))
    
    def _analyze_ktor_routes(
        self, 
        content: str, 
        file_path: Path, 
        analysis: FileAnalysis
    ) -> None:
        """Analyze Ktor routes."""
        # Check if it's using Ktor
        if "import io.ktor" not in content:
            return
        
        # Ktor route patterns
        route_patterns = [
            (r'get\s*\(\s*["\']([^"\']+)["\']', "GET"),
            (r'post\s*\(\s*["\']([^"\']+)["\']', "POST"),
            (r'put\s*\(\s*["\']([^"\']+)["\']', "PUT"),
            (r'delete\s*\(\s*["\']([^"\']+)["\']', "DELETE"),
            (r'patch\s*\(\s*["\']([^"\']+)["\']', "PATCH"),
        ]
        
        # Find route blocks
        route_block_pattern = r'route\s*\(\s*["\']([^"\']+)["\']'
        base_routes: list[str] = []
        for match in re.finditer(route_block_pattern, content):
            base_routes.append(match.group(1))
        
        for pattern, method in route_patterns:
            for match in re.finditer(pattern, content):
                path = match.group(1)
                
                # Check for authentication in context
                match_pos = match.start()
                context_start = max(0, match_pos - 300)
                context = content[context_start:match_pos]
                
                requires_auth = any(
                    auth in context
                    for auth in ["authenticate", "jwt", "session", "principal"]
                )
                
                endpoint = {
                    "path": path,
                    "method": method,
                    "framework": "ktor",
                    "file": str(file_path),
                    "requires_auth": requires_auth,
                }
                analysis.api_endpoints.append(endpoint)
    
    def _analyze_data_classes(
        self, 
        content: str, 
        file_path: Path, 
        analysis: FileAnalysis
    ) -> None:
        """Analyze Kotlin data classes for sensitive data."""
        # Find data classes
        data_class_pattern = r'data\s+class\s+(\w+)\s*\(([^)]+)\)'
        
        for match in re.finditer(data_class_pattern, content):
            class_name = match.group(1)
            params = match.group(2)
            
            # Extract fields
            fields: list[str] = []
            field_pattern = r'(?:val|var)\s+(\w+)\s*:'
            for field_match in re.finditer(field_pattern, params):
                fields.append(field_match.group(1))
            
            # Check if it's a DTO/Request/Response
            is_dto = any(
                suffix in class_name
                for suffix in ["DTO", "Dto", "Request", "Response", "Input", "Output"]
            )
            
            model_info = {
                "name": class_name,
                "type": "data_class",
                "fields": fields,
                "is_dto": is_dto,
                "file": str(file_path),
            }
            analysis.data_models.append(model_info)
            
            # Check for sensitive fields
            is_sensitive = self._has_sensitive_fields(class_name, fields)
            
            if is_sensitive:
                analysis.entities.append(Entity(
                    name=class_name,
                    entity_type=EntityType.DATA,
                    description=f"Kotlin data class from {file_path.name}",
                    source=str(file_path),
                    is_sensitive=True,
                ))
    
    def _analyze_jpa_entities(
        self, 
        content: str, 
        file_path: Path, 
        analysis: FileAnalysis
    ) -> None:
        """Analyze JPA/Hibernate entities."""
        # Find @Entity annotated classes
        entity_pattern = r'@Entity[^c]*class\s+(\w+)'
        
        for match in re.finditer(entity_pattern, content):
            entity_name = match.group(1)
            
            # Extract fields (look for @Column annotations)
            fields: list[str] = []
            
            # Find the class body
            class_start = match.end()
            brace_count = 0
            class_end = class_start
            started = False
            
            for i, char in enumerate(content[class_start:], class_start):
                if char == '{':
                    brace_count += 1
                    started = True
                elif char == '}':
                    brace_count -= 1
                if started and brace_count == 0:
                    class_end = i
                    break
            
            class_body = content[class_start:class_end]
            
            # Find fields
            field_pattern = r'(?:@Column[^v]*)?(?:val|var)\s+(\w+)\s*:'
            for field_match in re.finditer(field_pattern, class_body):
                fields.append(field_match.group(1))
            
            model_info = {
                "name": entity_name,
                "type": "jpa_entity",
                "fields": fields,
                "file": str(file_path),
            }
            analysis.data_models.append(model_info)
            
            is_sensitive = self._has_sensitive_fields(entity_name, fields)
            
            analysis.entities.append(Entity(
                name=entity_name,
                entity_type=EntityType.DATA,
                description=f"JPA Entity from {file_path.name}",
                source=str(file_path),
                is_sensitive=is_sensitive,
            ))
    
    def _analyze_security_annotations(
        self, 
        content: str, 
        file_path: Path, 
        analysis: FileAnalysis
    ) -> None:
        """Analyze Spring Security annotations."""
        security_patterns = [
            (r'@PreAuthorize\s*\(\s*["\']([^"\']+)["\']', "pre_authorize"),
            (r'@Secured\s*\(\s*\[?["\']([^"\']+)["\']', "secured"),
            (r'@RolesAllowed\s*\(\s*\[?["\']([^"\']+)["\']', "roles_allowed"),
            (r'@EnableWebSecurity', "web_security"),
            (r'@EnableGlobalMethodSecurity', "method_security"),
        ]
        
        for pattern, auth_type in security_patterns:
            for match in re.finditer(pattern, content):
                auth_info = {
                    "type": auth_type,
                    "file": str(file_path),
                }
                if match.lastindex:
                    auth_info["expression"] = match.group(1)
                
                analysis.auth_patterns.append(auth_info)
        
        # Check for security configuration classes
        if "@Configuration" in content and "Security" in content:
            analysis.security_controls.append("security_configuration")
        
        # Check for JWT usage
        if "jwt" in content.lower() or "JwtToken" in content:
            analysis.security_controls.append("jwt_authentication")
        
        # Check for password encoding
        if "PasswordEncoder" in content or "BCrypt" in content:
            analysis.security_controls.append("password_encoding")
    
    def _has_sensitive_fields(self, class_name: str, fields: list[str]) -> bool:
        """Check if class/fields contain sensitive data."""
        sensitive_class_patterns = [
            "user", "account", "auth", "credential", "password",
            "payment", "billing", "personal", "customer"
        ]
        
        sensitive_field_patterns = [
            "password", "email", "ssn", "phone", "token",
            "secret", "key", "credential", "cardnumber", "cvv"
        ]
        
        class_lower = class_name.lower()
        for pattern in sensitive_class_patterns:
            if pattern in class_lower:
                return True
        
        for field in fields:
            field_lower = field.lower()
            for pattern in sensitive_field_patterns:
                if pattern in field_lower:
                    return True
        
        return False

