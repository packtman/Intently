"""
Architecture Analyzer - Analyze architectural patterns and system design.

Identifies:
- Service definitions and boundaries
- API contracts and interfaces
- Module dependencies and coupling
- Architectural patterns (microservices, monolith, etc.)
- Architecture Decision Records (ADRs)
- System documentation
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from context_graph.core.models import Entity, EntityType, Relationship, RelationshipType
from context_graph.analyzers.codebase_analyzer import CodebaseAnalyzer, FileAnalysis


@dataclass
class ArchitectureMetrics:
    """Metrics from architecture analysis."""
    
    services_identified: int = 0
    api_contracts: int = 0
    modules: int = 0
    adrs_found: int = 0
    external_dependencies: int = 0
    internal_dependencies: int = 0
    circular_dependency_risk: int = 0
    architectural_patterns: list[str] = field(default_factory=list)


class ArchitectureAnalyzer(CodebaseAnalyzer):
    """
    Analyze codebase for architectural patterns and system design.
    
    Identifies:
    - Service boundaries (microservices, modules)
    - API contracts (OpenAPI, GraphQL schemas, protobuf)
    - Dependency structure
    - Architecture Decision Records
    - System documentation
    - Communication patterns (sync, async, event-driven)
    """
    
    def __init__(
        self,
        exclude_patterns: list[str] | None = None,
    ) -> None:
        super().__init__(exclude_patterns)
        self.metrics = ArchitectureMetrics()
        self._discovered_services: list[str] = []
        self._discovered_dependencies: dict[str, list[str]] = {}
    
    def supported_extensions(self) -> list[str]:
        return [
            ".yaml", ".yml", ".json",  # API specs, configs
            ".proto",  # Protocol buffers
            ".graphql", ".gql",  # GraphQL schemas
            ".md", ".rst",  # Documentation
            ".py", ".ts", ".js", ".go", ".java", ".kt",  # Source for imports
            ".toml", ".gradle", ".xml",  # Dependency files
        ]
    
    def analyze_file(self, file_path: Path) -> FileAnalysis:
        """Analyze a file for architectural patterns."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return FileAnalysis(path=file_path, language="unknown")
        
        analysis = FileAnalysis(
            path=file_path,
            language=self._detect_file_type(file_path),
            lines_of_code=len(content.split("\n")),
        )
        
        file_name = file_path.name.lower()
        
        # Route to appropriate analyzer
        if self._is_api_contract(file_path, content):
            self._analyze_api_contract(content, file_path, analysis)
        elif self._is_adr(file_path):
            self._analyze_adr(content, file_path, analysis)
        elif self._is_dependency_file(file_path):
            self._analyze_dependency_file(content, file_path, analysis)
        elif self._is_service_definition(file_path, content):
            self._analyze_service_definition(content, file_path, analysis)
        elif file_path.suffix in [".proto"]:
            self._analyze_protobuf(content, file_path, analysis)
        elif file_path.suffix in [".graphql", ".gql"]:
            self._analyze_graphql(content, file_path, analysis)
        elif file_path.suffix in [".py", ".ts", ".js", ".go", ".java", ".kt"]:
            self._analyze_code_architecture(content, file_path, analysis)
        
        return analysis
    
    def _detect_file_type(self, file_path: Path) -> str:
        """Detect file type for architecture analysis."""
        ext_map = {
            ".yaml": "yaml", ".yml": "yaml",
            ".json": "json",
            ".proto": "protobuf",
            ".graphql": "graphql", ".gql": "graphql",
            ".md": "markdown", ".rst": "restructuredtext",
            ".py": "python", ".ts": "typescript", ".js": "javascript",
            ".go": "go", ".java": "java", ".kt": "kotlin",
            ".toml": "toml", ".gradle": "gradle", ".xml": "xml",
        }
        return ext_map.get(file_path.suffix.lower(), "unknown")
    
    def _is_api_contract(self, file_path: Path, content: str) -> bool:
        """Check if file is an API contract definition."""
        name = file_path.name.lower()
        
        # OpenAPI/Swagger
        if "openapi" in name or "swagger" in name:
            return True
        if "openapi:" in content or "swagger:" in content:
            return True
        
        # AsyncAPI
        if "asyncapi" in content.lower():
            return True
        
        # API definition patterns in filename
        api_patterns = ["api.", "-api.", "_api.", "api-spec", "api-schema"]
        return any(p in name for p in api_patterns)
    
    def _is_adr(self, file_path: Path) -> bool:
        """Check if file is an Architecture Decision Record."""
        path_str = str(file_path).lower()
        name = file_path.name.lower()
        
        adr_patterns = [
            "adr/", "adrs/", "decisions/", "architecture-decisions/",
            "adr-", "adr_",
        ]
        
        return any(p in path_str or p in name for p in adr_patterns)
    
    def _is_dependency_file(self, file_path: Path) -> bool:
        """Check if file is a dependency/build file."""
        dep_files = [
            "package.json", "requirements.txt", "pyproject.toml",
            "go.mod", "cargo.toml", "build.gradle", "pom.xml",
            "gemfile", "composer.json", "mix.exs",
        ]
        return file_path.name.lower() in dep_files
    
    def _is_service_definition(self, file_path: Path, content: str) -> bool:
        """Check if file defines a service."""
        name = file_path.name.lower()
        
        # Docker compose services
        if "docker-compose" in name and "services:" in content:
            return True
        
        # Kubernetes services
        if "kind: Service" in content or "kind: Deployment" in content:
            return True
        
        # Service configuration files
        service_patterns = ["service.", "-service.", "_service."]
        return any(p in name for p in service_patterns)
    
    def _analyze_api_contract(
        self,
        content: str,
        file_path: Path,
        analysis: FileAnalysis
    ) -> None:
        """Analyze API contract files (OpenAPI, AsyncAPI)."""
        self.metrics.api_contracts += 1
        
        # Determine contract type
        contract_type = "openapi"
        if "asyncapi" in content.lower():
            contract_type = "asyncapi"
            self.metrics.architectural_patterns.append("event_driven")
        
        # Extract API info
        title_match = re.search(r'title:\s*[\'"]?([^\'":\n]+)', content)
        version_match = re.search(r'version:\s*[\'"]?([^\'":\n]+)', content)
        
        title = title_match.group(1).strip() if title_match else file_path.stem
        version = version_match.group(1).strip() if version_match else "unknown"
        
        analysis.entities.append(Entity(
            name=f"API: {title}",
            entity_type=EntityType.API,
            description=f"{contract_type.upper()} contract v{version}",
            source=str(file_path),
            properties={
                "contract_type": contract_type,
                "version": version,
            }
        ))
        
        # Extract endpoints/channels
        if contract_type == "openapi":
            paths = re.findall(r'^\s{2}([\'"]?/[^:\'"]*[\'"]?):', content, re.MULTILINE)
            for path in paths:
                path_clean = path.strip("'\"")
                analysis.api_endpoints.append({
                    "path": path_clean,
                    "source": str(file_path),
                    "contract_type": contract_type,
                })
        
        elif contract_type == "asyncapi":
            channels = re.findall(r'^\s{2}([\'"]?[^:\'"]+[\'"]?):', content, re.MULTILINE)
            for channel in channels:
                if channel.strip("'\"") not in ["info", "servers", "components"]:
                    analysis.api_endpoints.append({
                        "channel": channel.strip("'\""),
                        "source": str(file_path),
                        "contract_type": contract_type,
                    })
        
        # Security schemes
        if re.search(r'securitySchemes:|security:', content):
            analysis.auth_patterns.append({
                "type": "api_security_scheme",
                "file": str(file_path),
            })
        
        analysis.security_controls.append(f"{contract_type}_documentation")
    
    def _analyze_adr(
        self,
        content: str,
        file_path: Path,
        analysis: FileAnalysis
    ) -> None:
        """Analyze Architecture Decision Records."""
        self.metrics.adrs_found += 1
        
        # Extract ADR title
        title_match = re.search(r'^#\s*(.+)$', content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else file_path.stem
        
        # Extract status
        status_match = re.search(r'Status[:\s]+(\w+)', content, re.IGNORECASE)
        status = status_match.group(1) if status_match else "unknown"
        
        # Look for architectural patterns mentioned
        patterns_found = []
        pattern_keywords = {
            "microservices": "microservices",
            "monolith": "monolith",
            "event-driven": "event_driven",
            "event sourcing": "event_sourcing",
            "cqrs": "cqrs",
            "saga": "saga_pattern",
            "api gateway": "api_gateway",
            "service mesh": "service_mesh",
            "serverless": "serverless",
            "pub/sub": "pubsub",
            "message queue": "message_queue",
        }
        
        content_lower = content.lower()
        for keyword, pattern in pattern_keywords.items():
            if keyword in content_lower:
                patterns_found.append(pattern)
                if pattern not in self.metrics.architectural_patterns:
                    self.metrics.architectural_patterns.append(pattern)
        
        analysis.entities.append(Entity(
            name=f"ADR: {title}",
            entity_type=EntityType.MODULE,
            description=f"Architecture Decision Record (Status: {status})",
            source=str(file_path),
            properties={
                "doc_type": "adr",
                "status": status,
                "patterns": patterns_found,
            }
        ))
        
        analysis.security_controls.append("architecture_documentation")
        
        # Check for security-related decisions
        security_keywords = [
            "authentication", "authorization", "encryption",
            "security", "access control", "audit",
        ]
        if any(k in content_lower for k in security_keywords):
            analysis.security_controls.append("security_architecture_decision")
    
    def _analyze_dependency_file(
        self,
        content: str,
        file_path: Path,
        analysis: FileAnalysis
    ) -> None:
        """Analyze dependency files for external dependencies."""
        file_name = file_path.name.lower()
        
        dependencies: list[str] = []
        
        if file_name == "package.json":
            # Extract npm dependencies
            deps_match = re.findall(r'"([^"]+)":\s*"[\^~]?[\d.]', content)
            dependencies.extend(deps_match)
        
        elif file_name == "requirements.txt":
            # Extract pip dependencies
            deps = re.findall(r'^([a-zA-Z0-9_-]+)', content, re.MULTILINE)
            dependencies.extend(deps)
        
        elif file_name == "pyproject.toml":
            # Extract poetry dependencies
            deps = re.findall(r'^([a-zA-Z0-9_-]+)\s*=', content, re.MULTILINE)
            dependencies.extend(deps)
        
        elif file_name == "go.mod":
            # Extract Go modules
            deps = re.findall(r'^\s*([a-zA-Z0-9./]+)\s+v', content, re.MULTILINE)
            dependencies.extend(deps)
        
        elif file_name == "cargo.toml":
            # Extract Rust crates
            deps = re.findall(r'^\[dependencies\.([^\]]+)\]', content, re.MULTILINE)
            deps.extend(re.findall(r'^([a-zA-Z0-9_-]+)\s*=', content, re.MULTILINE))
            dependencies.extend(deps)
        
        self.metrics.external_dependencies += len(dependencies)
        
        # Identify security-relevant dependencies
        security_deps = []
        security_keywords = [
            "auth", "jwt", "oauth", "passport", "bcrypt",
            "crypto", "helmet", "cors", "csrf", "security",
        ]
        
        for dep in dependencies:
            dep_lower = dep.lower()
            if any(k in dep_lower for k in security_keywords):
                security_deps.append(dep)
        
        if security_deps:
            analysis.entities.append(Entity(
                name=f"Security Dependencies",
                entity_type=EntityType.SECURITY_CONTROL,
                description=f"Security-related dependencies: {', '.join(security_deps[:5])}",
                source=str(file_path),
                properties={"dependencies": security_deps}
            ))
        
        analysis.entities.append(Entity(
            name=f"Dependencies: {file_path.name}",
            entity_type=EntityType.MODULE,
            description=f"{len(dependencies)} external dependencies",
            source=str(file_path),
            properties={
                "dependency_count": len(dependencies),
                "sample_deps": dependencies[:10],
            }
        ))
    
    def _analyze_service_definition(
        self,
        content: str,
        file_path: Path,
        analysis: FileAnalysis
    ) -> None:
        """Analyze service definition files."""
        # Extract service names from docker-compose
        services = re.findall(r'^\s{2}(\w+):\s*$', content, re.MULTILINE)
        
        for service in services:
            self.metrics.services_identified += 1
            self._discovered_services.append(service)
            
            analysis.entities.append(Entity(
                name=f"Service: {service}",
                entity_type=EntityType.SERVICE,
                description="Service definition",
                source=str(file_path),
                properties={"service_name": service}
            ))
        
        # Check for service dependencies
        if "depends_on:" in content:
            deps = re.findall(r'depends_on:[\s\S]*?(?=\n\s{2}\w+:|$)', content)
            if deps:
                analysis.security_controls.append("service_dependency_defined")
        
        # Check for health checks
        if "healthcheck:" in content:
            analysis.security_controls.append("service_healthcheck")
        
        # Check for network isolation
        if "networks:" in content:
            analysis.security_controls.append("network_isolation")
    
    def _analyze_protobuf(
        self,
        content: str,
        file_path: Path,
        analysis: FileAnalysis
    ) -> None:
        """Analyze Protocol Buffer definitions."""
        self.metrics.api_contracts += 1
        
        # Extract service definitions
        services = re.findall(r'service\s+(\w+)\s*\{', content)
        for service in services:
            self.metrics.services_identified += 1
            analysis.entities.append(Entity(
                name=f"gRPC: {service}",
                entity_type=EntityType.SERVICE,
                description="gRPC service definition",
                source=str(file_path),
                properties={"protocol": "grpc"}
            ))
        
        # Extract message types
        messages = re.findall(r'message\s+(\w+)\s*\{', content)
        for message in messages:
            analysis.data_models.append({
                "name": message,
                "type": "protobuf_message",
                "file": str(file_path),
            })
        
        # Extract RPC methods
        rpcs = re.findall(r'rpc\s+(\w+)\s*\(', content)
        for rpc in rpcs:
            analysis.api_endpoints.append({
                "method": rpc,
                "protocol": "grpc",
                "file": str(file_path),
            })
        
        if not self.metrics.architectural_patterns:
            self.metrics.architectural_patterns.append("grpc_services")
    
    def _analyze_graphql(
        self,
        content: str,
        file_path: Path,
        analysis: FileAnalysis
    ) -> None:
        """Analyze GraphQL schema definitions."""
        self.metrics.api_contracts += 1
        
        # Extract types
        types = re.findall(r'type\s+(\w+)\s*(?:implements\s+\w+\s*)?\{', content)
        for type_name in types:
            if type_name not in ["Query", "Mutation", "Subscription"]:
                analysis.data_models.append({
                    "name": type_name,
                    "type": "graphql_type",
                    "file": str(file_path),
                })
        
        # Extract queries
        query_match = re.search(r'type\s+Query\s*\{([^}]+)\}', content, re.DOTALL)
        if query_match:
            queries = re.findall(r'(\w+)\s*[\(:]', query_match.group(1))
            for query in queries:
                analysis.api_endpoints.append({
                    "operation": query,
                    "type": "query",
                    "protocol": "graphql",
                    "file": str(file_path),
                })
        
        # Extract mutations
        mutation_match = re.search(r'type\s+Mutation\s*\{([^}]+)\}', content, re.DOTALL)
        if mutation_match:
            mutations = re.findall(r'(\w+)\s*[\(:]', mutation_match.group(1))
            for mutation in mutations:
                analysis.api_endpoints.append({
                    "operation": mutation,
                    "type": "mutation",
                    "protocol": "graphql",
                    "file": str(file_path),
                })
        
        analysis.entities.append(Entity(
            name=f"GraphQL: {file_path.stem}",
            entity_type=EntityType.API,
            description="GraphQL schema",
            source=str(file_path),
            properties={"protocol": "graphql"}
        ))
        
        if "graphql" not in self.metrics.architectural_patterns:
            self.metrics.architectural_patterns.append("graphql")
    
    def _analyze_code_architecture(
        self,
        content: str,
        file_path: Path,
        analysis: FileAnalysis
    ) -> None:
        """Analyze source code for architectural patterns."""
        # Detect layered architecture patterns
        path_str = str(file_path).lower()
        
        layer_patterns = {
            "controllers/": "controller_layer",
            "handlers/": "handler_layer",
            "services/": "service_layer",
            "repositories/": "repository_layer",
            "models/": "model_layer",
            "domain/": "domain_layer",
            "infrastructure/": "infrastructure_layer",
            "adapters/": "adapter_layer",
            "ports/": "ports_layer",
            "usecases/": "usecase_layer",
            "application/": "application_layer",
        }
        
        for pattern, layer in layer_patterns.items():
            if pattern in path_str:
                if "layered_architecture" not in self.metrics.architectural_patterns:
                    self.metrics.architectural_patterns.append("layered_architecture")
                analysis.entities.append(Entity(
                    name=f"Layer: {layer}",
                    entity_type=EntityType.MODULE,
                    description=f"Architectural layer component",
                    source=str(file_path),
                    properties={"layer": layer}
                ))
                break
        
        # Detect hexagonal/clean architecture
        hex_patterns = ["ports/", "adapters/", "domain/", "application/"]
        if sum(1 for p in hex_patterns if p in path_str) >= 2:
            if "hexagonal_architecture" not in self.metrics.architectural_patterns:
                self.metrics.architectural_patterns.append("hexagonal_architecture")
        
        # Analyze imports for internal dependencies
        self._analyze_imports(content, file_path, analysis)
        
        # Detect design patterns in code
        self._detect_design_patterns(content, file_path, analysis)
    
    def _analyze_imports(
        self,
        content: str,
        file_path: Path,
        analysis: FileAnalysis
    ) -> None:
        """Analyze import statements for dependency analysis."""
        imports: list[str] = []
        
        # Python imports
        py_imports = re.findall(r'^(?:from|import)\s+([a-zA-Z_][a-zA-Z0-9_\.]*)', content, re.MULTILINE)
        imports.extend(py_imports)
        
        # JavaScript/TypeScript imports
        js_imports = re.findall(r'import\s+.*?from\s+[\'"]([^\'"]+)[\'"]', content)
        js_imports.extend(re.findall(r'require\s*\(\s*[\'"]([^\'"]+)[\'"]', content))
        imports.extend(js_imports)
        
        # Go imports
        go_imports = re.findall(r'"([^"]+)"', content)
        if file_path.suffix == ".go":
            imports.extend(go_imports)
        
        # Count internal vs external
        internal = 0
        external = 0
        
        for imp in imports:
            if imp.startswith(".") or imp.startswith("@/") or "/" not in imp:
                internal += 1
            else:
                external += 1
        
        self.metrics.internal_dependencies += internal
        
        # Store dependencies for circular detection
        file_key = str(file_path)
        self._discovered_dependencies[file_key] = imports
    
    def _detect_design_patterns(
        self,
        content: str,
        file_path: Path,
        analysis: FileAnalysis
    ) -> None:
        """Detect common design patterns in code."""
        patterns_detected = []
        
        # Singleton pattern
        if re.search(r'getInstance|_instance\s*=\s*None|static\s+instance', content):
            patterns_detected.append("singleton")
        
        # Factory pattern
        if re.search(r'Factory|create[A-Z]\w+\(|factory\s*=', content, re.IGNORECASE):
            patterns_detected.append("factory")
        
        # Repository pattern
        if re.search(r'Repository|\.find\(|\.save\(|\.delete\(', content):
            patterns_detected.append("repository")
        
        # Observer/Event pattern
        if re.search(r'addEventListener|subscribe|emit|publish|on\([\'"]', content):
            patterns_detected.append("observer")
            if "event_driven" not in self.metrics.architectural_patterns:
                self.metrics.architectural_patterns.append("event_driven")
        
        # Dependency injection
        if re.search(r'@Inject|@Autowired|constructor\s*\([^)]+\)', content):
            patterns_detected.append("dependency_injection")
        
        # Middleware pattern
        if re.search(r'middleware|use\s*\(\s*\w+\s*\)', content):
            patterns_detected.append("middleware")
        
        if patterns_detected:
            for pattern in patterns_detected:
                analysis.security_controls.append(f"pattern_{pattern}")
    
    def get_metrics(self) -> ArchitectureMetrics:
        """Return collected architecture metrics."""
        return self.metrics
    
    def reset_metrics(self) -> None:
        """Reset metrics for a new analysis."""
        self.metrics = ArchitectureMetrics()
        self._discovered_services = []
        self._discovered_dependencies = {}
    
    def get_discovered_services(self) -> list[str]:
        """Return list of discovered services."""
        return self._discovered_services
    
    def detect_circular_dependencies(self) -> list[tuple[str, str]]:
        """
        Detect potential circular dependencies.
        
        Returns list of (file1, file2) tuples indicating potential cycles.
        """
        circular: list[tuple[str, str]] = []
        
        for file_a, deps_a in self._discovered_dependencies.items():
            for file_b, deps_b in self._discovered_dependencies.items():
                if file_a != file_b:
                    # Simplified check - look for mutual references
                    a_refs_b = any(Path(file_b).stem in d for d in deps_a)
                    b_refs_a = any(Path(file_a).stem in d for d in deps_b)
                    
                    if a_refs_b and b_refs_a:
                        pair = tuple(sorted([file_a, file_b]))
                        if pair not in circular:
                            circular.append(pair)
                            self.metrics.circular_dependency_risk += 1
        
        return circular


