"""
PRD Generator - Generate Product Requirement Documents from codebases.

This module analyzes existing codebases and generates comprehensive PRD documents
that describe the system's features, APIs, data models, and architecture.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from context_graph.analyzers import (
    MultiLanguageAnalyzer,
    PythonAnalyzer,
    KotlinAnalyzer,
    TypeScriptAnalyzer,
    YAMLAnalyzer,
    JSONAnalyzer,
)
from context_graph.core.models import State
from context_graph.config.features import get_features


@dataclass
class GeneratedSection:
    """A section of the generated PRD."""
    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    content: str = ""
    subsections: list["GeneratedSection"] = field(default_factory=list)
    source_files: list[str] = field(default_factory=list)
    confidence: float = 0.9


@dataclass
class Feature:
    """A detected feature in the codebase."""
    name: str = ""
    description: str = ""
    endpoints: list[str] = field(default_factory=list)
    models: list[str] = field(default_factory=list)


@dataclass
class APIEndpoint:
    """Documented API endpoint."""
    endpoint: str = ""
    method: str = "GET"
    description: str = ""
    parameters: list[dict[str, Any]] = field(default_factory=list)
    response: str = ""


@dataclass
class DataModel:
    """Documented data model."""
    name: str = ""
    fields: list[dict[str, Any]] = field(default_factory=list)
    relationships: list[str] = field(default_factory=list)


@dataclass
class Dependency:
    """A project dependency."""
    name: str = ""
    version: str = ""
    purpose: str = ""


@dataclass
class GeneratedPRD:
    """The complete generated PRD document."""
    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    summary: str = ""
    sections: list[GeneratedSection] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    features: list[Feature] = field(default_factory=list)
    api_documentation: list[APIEndpoint] = field(default_factory=list)
    data_models: list[DataModel] = field(default_factory=list)
    auth_requirements: list[str] = field(default_factory=list)
    technical_stack: list[str] = field(default_factory=list)
    dependencies: list[Dependency] = field(default_factory=list)
    output_file_path: str = ""  # Path where markdown was saved


@dataclass
class GenerationStatus:
    """Status of a PRD generation job."""
    status: str = "pending"  # pending, analyzing, generating, completed, failed
    progress: float = 0.0
    current_step: str = ""
    steps_completed: list[str] = field(default_factory=list)
    error_message: str = ""


@dataclass
class GeneratorConfig:
    """Configuration for PRD generation."""
    codebase_path: str = ""
    languages: list[str] = field(default_factory=list)
    focus_areas: list[str] = field(default_factory=list)
    include_api_docs: bool = True
    include_data_models: bool = True
    include_auth_flow: bool = True
    include_architecture: bool = True
    output_format: str = "markdown"
    detail_level: str = "detailed"  # overview, detailed, comprehensive
    output_directory: str = ""  # Directory to save generated PRD files
    auto_save: bool = True  # Automatically save to .md file


class PRDGenerator:
    """
    Generates comprehensive PRD documents from codebase analysis.
    
    This class orchestrates:
    1. Codebase scanning and analysis
    2. Feature detection
    3. API documentation extraction
    4. Data model discovery
    5. AI-powered PRD generation
    """
    
    def __init__(
        self,
        openai_api_key: str | None = None,
        anthropic_api_key: str | None = None,
    ):
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        
        # Storage for generation jobs
        self._generations: dict[str, GeneratedPRD] = {}
        self._statuses: dict[str, GenerationStatus] = {}
    
    def _get_analyzer(self, languages: list[str]) -> MultiLanguageAnalyzer:
        """Get multi-language analyzer for specified languages."""
        analyzer = MultiLanguageAnalyzer()
        
        use_all = "auto" in languages or "all" in languages
        
        if use_all or "python" in languages:
            analyzer.add_analyzer(PythonAnalyzer())
        if use_all or "kotlin" in languages:
            analyzer.add_analyzer(KotlinAnalyzer())
        if use_all or "typescript" in languages or "javascript" in languages:
            analyzer.add_analyzer(TypeScriptAnalyzer())
        if use_all or "yaml" in languages or "openapi" in languages:
            analyzer.add_analyzer(YAMLAnalyzer())
        if use_all or "json" in languages:
            analyzer.add_analyzer(JSONAnalyzer())
        
        return analyzer
    
    async def generate(
        self,
        config: GeneratorConfig,
        generation_id: str | None = None,
    ) -> str:
        """
        Start PRD generation from a codebase.
        
        Returns the generation ID for status polling.
        """
        gen_id = generation_id or str(uuid4())
        
        # Initialize status
        self._statuses[gen_id] = GenerationStatus(
            status="pending",
            progress=0.0,
            current_step="Initializing...",
        )
        
        # Run generation in background
        asyncio.create_task(self._run_generation(gen_id, config))
        
        return gen_id
    
    async def _run_generation(
        self,
        generation_id: str,
        config: GeneratorConfig,
    ) -> None:
        """Run the full PRD generation pipeline."""
        status = self._statuses[generation_id]
        start_time = datetime.now()
        
        try:
            # Step 1: Scan codebase
            status.status = "analyzing"
            status.current_step = "Scanning codebase..."
            status.progress = 0.1
            
            path = Path(config.codebase_path)
            if not path.exists():
                raise ValueError(f"Codebase path not found: {config.codebase_path}")
            
            status.steps_completed.append("scan")
            
            # Step 2: Parse source files
            status.current_step = "Parsing source files..."
            status.progress = 0.2
            
            analyzer = self._get_analyzer(config.languages)
            state = analyzer.analyze_codebase(path)
            
            status.steps_completed.append("parse")
            
            # Step 3: Extract features
            status.current_step = "Extracting features..."
            status.progress = 0.4
            
            features = self._extract_features(state, config)
            
            status.steps_completed.append("extract")
            
            # Step 4: Analyze architecture
            status.current_step = "Analyzing architecture..."
            status.progress = 0.5
            
            technical_stack = self._detect_tech_stack(path, state)
            dependencies = self._extract_dependencies(path)
            
            status.steps_completed.append("analyze")
            
            # Step 5: Generate PRD content using AI
            status.status = "generating"
            status.current_step = "Generating PRD..."
            status.progress = 0.6
            
            prd = await self._generate_prd_content(
                state=state,
                features=features,
                technical_stack=technical_stack,
                dependencies=dependencies,
                config=config,
            )
            
            status.steps_completed.append("generate")
            
            # Step 6: Format output
            status.current_step = "Formatting output..."
            status.progress = 0.9
            
            # Calculate metadata
            generation_time = (datetime.now() - start_time).total_seconds() * 1000
            prd.metadata = {
                "codebase_path": config.codebase_path,
                "files_analyzed": state.files_analyzed,
                "lines_of_code": state.lines_of_code,
                "languages": config.languages,
                "generated_at": datetime.now().isoformat(),
                "generation_time_ms": generation_time,
                "ai_provider": "anthropic" if self.anthropic_api_key else "openai" if self.openai_api_key else None,
            }
            
            status.steps_completed.append("format")
            
            # Step 7: Auto-save to file if enabled
            if config.auto_save:
                status.current_step = "Saving PRD to file..."
                output_path = self._save_prd_to_file(prd, config, generation_id)
                prd.output_file_path = output_path
                prd.metadata["output_file_path"] = output_path
                status.steps_completed.append("save")
            
            # Store result
            self._generations[generation_id] = prd
            
            status.status = "completed"
            status.current_step = "PRD generation completed"
            status.progress = 1.0
            
        except Exception as e:
            status.status = "failed"
            status.error_message = str(e)
            status.current_step = f"Failed: {str(e)}"
            import traceback
            traceback.print_exc()
    
    def _extract_features(
        self,
        state: State,
        config: GeneratorConfig,
    ) -> list[Feature]:
        """Extract features from codebase analysis."""
        features: list[Feature] = []
        
        # Group endpoints by path prefix to identify features
        endpoint_groups: dict[str, list[dict[str, Any]]] = {}
        
        for endpoint in state.api_endpoints:
            path = endpoint.get("path", "")
            if path:
                # Extract feature name from path (e.g., /api/users -> users)
                parts = path.strip("/").split("/")
                if len(parts) >= 2:
                    feature_name = parts[1] if parts[0] in ("api", "v1", "v2") else parts[0]
                else:
                    feature_name = parts[0] if parts else "root"
                
                if feature_name not in endpoint_groups:
                    endpoint_groups[feature_name] = []
                endpoint_groups[feature_name].append(endpoint)
        
        # Create features from endpoint groups
        for feature_name, endpoints in endpoint_groups.items():
            feature = Feature(
                name=feature_name.replace("_", " ").replace("-", " ").title(),
                description=f"Feature handling {feature_name} operations",
                endpoints=[e.get("path", "") for e in endpoints],
            )
            
            # Find related models
            for model in state.data_models:
                model_name = model.get("name", "").lower()
                if feature_name.lower() in model_name or model_name in feature_name.lower():
                    feature.models.append(model.get("name", ""))
            
            features.append(feature)
        
        # Add models that aren't associated with endpoints as data features
        associated_models = {m for f in features for m in f.models}
        for model in state.data_models:
            name = model.get("name", "")
            if name and name not in associated_models:
                features.append(Feature(
                    name=f"{name} Data Model",
                    description=f"Data model for {name}",
                    models=[name],
                ))
        
        return features
    
    def _detect_tech_stack(self, path: Path, state: State) -> list[str]:
        """Detect the technical stack from the codebase."""
        stack: set[str] = set()
        
        # Check for common framework files
        framework_markers = {
            "requirements.txt": ["Python"],
            "pyproject.toml": ["Python", "Poetry"],
            "setup.py": ["Python"],
            "package.json": ["Node.js"],
            "tsconfig.json": ["TypeScript"],
            "Cargo.toml": ["Rust"],
            "go.mod": ["Go"],
            "pom.xml": ["Java", "Maven"],
            "build.gradle": ["Java/Kotlin", "Gradle"],
            "Gemfile": ["Ruby"],
            "docker-compose.yml": ["Docker"],
            "Dockerfile": ["Docker"],
            "kubernetes/": ["Kubernetes"],
            ".github/workflows": ["GitHub Actions"],
            "Makefile": ["Make"],
        }
        
        for marker, techs in framework_markers.items():
            if (path / marker).exists():
                stack.update(techs)
        
        # Detect from code patterns
        for endpoint in state.api_endpoints:
            framework = endpoint.get("framework", "")
            if framework:
                if framework == "fastapi":
                    stack.add("FastAPI")
                elif framework == "flask":
                    stack.add("Flask")
                elif framework == "django":
                    stack.add("Django")
                elif framework == "express":
                    stack.add("Express.js")
        
        # Detect from security controls
        for control in state.existing_controls:
            if "jwt" in control.lower():
                stack.add("JWT Authentication")
            if "oauth" in control.lower():
                stack.add("OAuth")
            if "cors" in control.lower():
                stack.add("CORS")
        
        return sorted(list(stack))
    
    def _extract_dependencies(self, path: Path) -> list[Dependency]:
        """Extract project dependencies."""
        dependencies: list[Dependency] = []
        
        # Python requirements.txt
        req_file = path / "requirements.txt"
        if req_file.exists():
            try:
                content = req_file.read_text()
                for line in content.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # Parse package==version or package>=version
                        match = re.match(r'^([a-zA-Z0-9_-]+)([>=<]+)?(.+)?$', line)
                        if match:
                            name = match.group(1)
                            version = match.group(3) or "latest"
                            dependencies.append(Dependency(
                                name=name,
                                version=version,
                                purpose=self._guess_dependency_purpose(name),
                            ))
            except Exception:
                pass
        
        # Python pyproject.toml
        pyproject = path / "pyproject.toml"
        if pyproject.exists():
            try:
                content = pyproject.read_text()
                # Simple parsing for dependencies section
                in_deps = False
                for line in content.split("\n"):
                    if "[tool.poetry.dependencies]" in line or "[project.dependencies]" in line:
                        in_deps = True
                        continue
                    if in_deps and line.startswith("["):
                        break
                    if in_deps and "=" in line:
                        parts = line.split("=")
                        name = parts[0].strip().strip('"')
                        if name and name != "python":
                            version = parts[1].strip().strip('"').strip("^")
                            dependencies.append(Dependency(
                                name=name,
                                version=version,
                                purpose=self._guess_dependency_purpose(name),
                            ))
            except Exception:
                pass
        
        # Node.js package.json
        pkg_json = path / "package.json"
        if pkg_json.exists():
            try:
                content = json.loads(pkg_json.read_text())
                for dep_type in ["dependencies", "devDependencies"]:
                    deps = content.get(dep_type, {})
                    for name, version in deps.items():
                        dependencies.append(Dependency(
                            name=name,
                            version=version.strip("^~"),
                            purpose=self._guess_dependency_purpose(name),
                        ))
            except Exception:
                pass
        
        # Deduplicate by name
        seen: set[str] = set()
        unique_deps: list[Dependency] = []
        for dep in dependencies:
            if dep.name not in seen:
                seen.add(dep.name)
                unique_deps.append(dep)
        
        return unique_deps[:50]  # Limit to 50 dependencies
    
    def _guess_dependency_purpose(self, name: str) -> str:
        """Guess the purpose of a dependency from its name."""
        name_lower = name.lower()
        
        purposes = {
            "fastapi": "Web framework",
            "flask": "Web framework",
            "django": "Web framework",
            "express": "Web framework",
            "react": "UI framework",
            "vue": "UI framework",
            "angular": "UI framework",
            "pytest": "Testing",
            "jest": "Testing",
            "mocha": "Testing",
            "sqlalchemy": "ORM/Database",
            "prisma": "ORM/Database",
            "mongoose": "ORM/Database",
            "redis": "Caching",
            "celery": "Task queue",
            "pydantic": "Data validation",
            "bcrypt": "Authentication",
            "jwt": "Authentication",
            "passport": "Authentication",
            "axios": "HTTP client",
            "requests": "HTTP client",
            "boto3": "AWS SDK",
            "stripe": "Payments",
            "sentry": "Error tracking",
            "logging": "Logging",
            "winston": "Logging",
            "webpack": "Build tool",
            "vite": "Build tool",
            "eslint": "Linting",
            "prettier": "Formatting",
            "typescript": "Type checking",
        }
        
        for key, purpose in purposes.items():
            if key in name_lower:
                return purpose
        
        return "Utility"
    
    async def _generate_prd_content(
        self,
        state: State,
        features: list[Feature],
        technical_stack: list[str],
        dependencies: list[Dependency],
        config: GeneratorConfig,
    ) -> GeneratedPRD:
        """Generate PRD content using AI."""
        
        # Build context for AI
        context = self._build_generation_context(
            state, features, technical_stack, dependencies, config
        )
        
        # Generate with AI if available
        if self.anthropic_api_key or self.openai_api_key:
            prd = await self._generate_with_ai(context, config)
        else:
            # Fallback to template-based generation
            prd = self._generate_from_template(context, config)
        
        # Populate structured data
        prd.features = features
        prd.technical_stack = technical_stack
        prd.dependencies = dependencies
        
        # Extract API docs from state
        prd.api_documentation = [
            APIEndpoint(
                endpoint=ep.get("path", ""),
                method=ep.get("method", "GET"),
                description=f"Endpoint at {ep.get('path', '')}",
                parameters=[],
                response="",
            )
            for ep in state.api_endpoints[:30]  # Limit for size
        ]
        
        # Extract data models from state
        prd.data_models = [
            DataModel(
                name=model.get("name", ""),
                fields=[{"name": f, "type": "unknown"} for f in model.get("fields", [])],
                relationships=[],
            )
            for model in state.data_models[:20]  # Limit for size
        ]
        
        # Extract auth requirements
        prd.auth_requirements = list(set(
            pattern.get("name", "")
            for pattern in state.auth_patterns
            if pattern.get("name")
        ))
        
        return prd
    
    def _build_generation_context(
        self,
        state: State,
        features: list[Feature],
        technical_stack: list[str],
        dependencies: list[Dependency],
        config: GeneratorConfig,
    ) -> dict[str, Any]:
        """Build context dictionary for AI generation."""
        return {
            "codebase_path": config.codebase_path,
            "files_analyzed": state.files_analyzed,
            "lines_of_code": state.lines_of_code,
            "features": [
                {
                    "name": f.name,
                    "description": f.description,
                    "endpoints": f.endpoints[:5],
                    "models": f.models[:5],
                }
                for f in features[:15]
            ],
            "api_endpoints": [
                {
                    "path": ep.get("path", ""),
                    "method": ep.get("method", ""),
                    "function": ep.get("function", ""),
                }
                for ep in state.api_endpoints[:20]
            ],
            "data_models": [
                {
                    "name": model.get("name", ""),
                    "fields": model.get("fields", [])[:10],
                }
                for model in state.data_models[:15]
            ],
            "auth_patterns": state.auth_patterns[:10],
            "security_controls": state.existing_controls[:15],
            "technical_stack": technical_stack,
            "dependencies": [
                {"name": d.name, "purpose": d.purpose}
                for d in dependencies[:20]
            ],
            "focus_areas": config.focus_areas,
            "detail_level": config.detail_level,
        }
    
    async def _generate_with_ai(
        self,
        context: dict[str, Any],
        config: GeneratorConfig,
    ) -> GeneratedPRD:
        """Generate PRD content using AI (Anthropic or OpenAI)."""
        
        prompt = self._build_generation_prompt(context, config)
        
        try:
            if self.anthropic_api_key:
                content = await self._call_anthropic(prompt)
            elif self.openai_api_key:
                content = await self._call_openai(prompt)
            else:
                return self._generate_from_template(context, config)
            
            # Parse AI response
            return self._parse_ai_response(content, context)
            
        except Exception as e:
            print(f"AI generation failed: {e}, falling back to template")
            return self._generate_from_template(context, config)
    
    def _build_generation_prompt(
        self,
        context: dict[str, Any],
        config: GeneratorConfig,
    ) -> str:
        """Build the prompt for AI PRD generation."""
        
        detail_instructions = {
            "overview": "Provide a high-level overview, focusing on main features and architecture. Keep sections brief.",
            "detailed": "Provide detailed documentation including feature descriptions, API specifications, and data models.",
            "comprehensive": "Provide maximum detail including implementation specifics, edge cases, and technical considerations.",
        }
        
        return f"""You are a technical writer creating a Product Requirements Document (PRD) from codebase analysis.

## Codebase Analysis Results

**Files Analyzed:** {context['files_analyzed']}
**Lines of Code:** {context['lines_of_code']}
**Technical Stack:** {', '.join(context['technical_stack'])}

### Detected Features
{json.dumps(context['features'], indent=2)}

### API Endpoints
{json.dumps(context['api_endpoints'], indent=2)}

### Data Models
{json.dumps(context['data_models'], indent=2)}

### Authentication Patterns
{json.dumps(context['auth_patterns'], indent=2)}

### Security Controls
{json.dumps(context['security_controls'], indent=2)}

## Instructions

{detail_instructions.get(config.detail_level, detail_instructions['detailed'])}

Generate a comprehensive PRD document in JSON format with the following structure:
{{
    "title": "Project name/title",
    "summary": "Executive summary of the project",
    "sections": [
        {{
            "id": "unique-id",
            "title": "Section Title",
            "content": "Section content in markdown format",
            "confidence": 0.9
        }}
    ]
}}

Include these sections:
1. **Overview** - Project purpose and scope
2. **Features** - Core features and functionality
3. **Technical Architecture** - System design and patterns
4. **API Documentation** - Endpoint specifications (if include_api_docs is true)
5. **Data Models** - Entity definitions and relationships (if include_data_models is true)
6. **Authentication & Authorization** - Security flows (if include_auth_flow is true)
7. **Dependencies** - External libraries and services
8. **Non-Functional Requirements** - Performance, scalability, security considerations

Focus areas: {', '.join(config.focus_areas)}

Respond ONLY with valid JSON, no additional text."""
    
    async def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic API for generation."""
        import httpx
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-opus-4-5-20251101",
                    "max_tokens": 8000,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"]
    
    async def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API for generation."""
        import httpx
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-5.2",
                    # GPT-5 family expects `max_completion_tokens` instead of `max_tokens`
                    "max_completion_tokens": 8000,
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    
    def _parse_ai_response(
        self,
        content: str,
        context: dict[str, Any],
    ) -> GeneratedPRD:
        """Parse AI response into GeneratedPRD structure."""
        try:
            # Try to parse as JSON
            data = json.loads(content)
            
            prd = GeneratedPRD(
                title=data.get("title", "Generated PRD"),
                summary=data.get("summary", ""),
            )
            
            # Parse sections
            for section_data in data.get("sections", []):
                section = GeneratedSection(
                    id=section_data.get("id", str(uuid4())),
                    title=section_data.get("title", ""),
                    content=section_data.get("content", ""),
                    confidence=section_data.get("confidence", 0.9),
                )
                prd.sections.append(section)
            
            return prd
            
        except json.JSONDecodeError:
            # If JSON parsing fails, treat as markdown
            return self._parse_markdown_response(content, context)
    
    def _parse_markdown_response(
        self,
        content: str,
        context: dict[str, Any],
    ) -> GeneratedPRD:
        """Parse markdown response into GeneratedPRD structure."""
        prd = GeneratedPRD(
            title="Generated PRD",
            summary="",
        )
        
        # Split by headers
        current_section: GeneratedSection | None = None
        current_content: list[str] = []
        
        for line in content.split("\n"):
            if line.startswith("# "):
                prd.title = line[2:].strip()
            elif line.startswith("## "):
                # Save previous section
                if current_section:
                    current_section.content = "\n".join(current_content).strip()
                    prd.sections.append(current_section)
                
                # Start new section
                current_section = GeneratedSection(
                    title=line[3:].strip(),
                )
                current_content = []
            elif current_section:
                current_content.append(line)
            elif not prd.summary and line.strip():
                prd.summary = line.strip()
        
        # Save last section
        if current_section:
            current_section.content = "\n".join(current_content).strip()
            prd.sections.append(current_section)
        
        return prd
    
    def _generate_from_template(
        self,
        context: dict[str, Any],
        config: GeneratorConfig,
    ) -> GeneratedPRD:
        """Generate PRD from template when AI is not available."""
        
        # Infer project name from path
        path_parts = context["codebase_path"].split("/")
        project_name = path_parts[-1] if path_parts else "Project"
        project_name = project_name.replace("-", " ").replace("_", " ").title()
        
        prd = GeneratedPRD(
            title=f"{project_name} - Product Requirements Document",
            summary=f"This document describes the product requirements for {project_name}, "
                    f"a software system consisting of {context['files_analyzed']} files "
                    f"and approximately {context['lines_of_code']:,} lines of code.",
        )
        
        # Overview section
        prd.sections.append(GeneratedSection(
            title="Overview",
            content=f"""## Purpose

{project_name} is a software system built with {', '.join(context['technical_stack'][:5]) or 'various technologies'}.

## Scope

This document covers:
- Core features and functionality
- API specifications
- Data models and relationships
- Authentication and authorization
- Technical architecture

## Metrics

- **Files Analyzed:** {context['files_analyzed']}
- **Lines of Code:** {context['lines_of_code']:,}
- **API Endpoints:** {len(context['api_endpoints'])}
- **Data Models:** {len(context['data_models'])}
""",
            confidence=0.95,
        ))
        
        # Features section
        features_content = "## Core Features\n\n"
        for feature in context["features"][:10]:
            features_content += f"### {feature['name']}\n\n"
            features_content += f"{feature['description']}\n\n"
            if feature["endpoints"]:
                features_content += "**Endpoints:**\n"
                for ep in feature["endpoints"][:3]:
                    features_content += f"- `{ep}`\n"
                features_content += "\n"
            if feature["models"]:
                features_content += "**Related Models:** " + ", ".join(feature["models"][:3]) + "\n\n"
        
        prd.sections.append(GeneratedSection(
            title="Features",
            content=features_content,
            confidence=0.85,
        ))
        
        # API Documentation section
        if config.include_api_docs and context["api_endpoints"]:
            api_content = "## API Endpoints\n\n"
            api_content += "| Method | Endpoint | Description |\n"
            api_content += "|--------|----------|-------------|\n"
            for ep in context["api_endpoints"][:15]:
                method = ep.get("method", "GET")
                path = ep.get("path", "")
                func = ep.get("function", "")
                api_content += f"| {method} | `{path}` | {func} |\n"
            
            prd.sections.append(GeneratedSection(
                title="API Documentation",
                content=api_content,
                confidence=0.9,
            ))
        
        # Data Models section
        if config.include_data_models and context["data_models"]:
            models_content = "## Data Models\n\n"
            for model in context["data_models"][:10]:
                name = model.get("name", "Unknown")
                models_content += f"### {name}\n\n"
                fields = model.get("fields", [])
                if fields:
                    models_content += "**Fields:**\n"
                    for field in fields[:10]:
                        models_content += f"- `{field}`\n"
                    models_content += "\n"
            
            prd.sections.append(GeneratedSection(
                title="Data Models",
                content=models_content,
                confidence=0.85,
            ))
        
        # Authentication section
        if config.include_auth_flow and context["auth_patterns"]:
            auth_content = "## Authentication & Authorization\n\n"
            auth_content += "### Detected Authentication Patterns\n\n"
            for pattern in context["auth_patterns"][:10]:
                name = pattern.get("name", "Unknown")
                ptype = pattern.get("type", "")
                auth_content += f"- **{name}** ({ptype})\n"
            
            auth_content += "\n### Security Controls\n\n"
            for control in context["security_controls"][:10]:
                auth_content += f"- {control.replace('_', ' ').title()}\n"
            
            prd.sections.append(GeneratedSection(
                title="Authentication & Authorization",
                content=auth_content,
                confidence=0.8,
            ))
        
        # Technical Architecture section
        if config.include_architecture:
            arch_content = "## Technical Architecture\n\n"
            arch_content += "### Technology Stack\n\n"
            for tech in context["technical_stack"]:
                arch_content += f"- {tech}\n"
            
            arch_content += "\n### Key Dependencies\n\n"
            arch_content += "| Package | Purpose |\n"
            arch_content += "|---------|----------|\n"
            for dep in context["dependencies"][:15]:
                arch_content += f"| {dep['name']} | {dep['purpose']} |\n"
            
            prd.sections.append(GeneratedSection(
                title="Technical Architecture",
                content=arch_content,
                confidence=0.9,
            ))
        
        return prd
    
    def _save_prd_to_file(
        self,
        prd: GeneratedPRD,
        config: GeneratorConfig,
        generation_id: str,
    ) -> str:
        """Save the generated PRD to a markdown file."""
        # Determine output directory
        if config.output_directory:
            output_dir = Path(config.output_directory)
        else:
            # Default: create 'generated-prds' folder in the codebase directory
            codebase_path = Path(config.codebase_path)
            if codebase_path.is_dir():
                output_dir = codebase_path / "generated-prds"
            else:
                output_dir = codebase_path.parent / "generated-prds"
        
        # Create directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename from title
        safe_title = re.sub(r'[^\w\s-]', '', prd.title).strip()
        safe_title = re.sub(r'[-\s]+', '-', safe_title)[:50]
        if not safe_title:
            safe_title = f"PRD-{generation_id[:8]}"
        
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"PRD-{safe_title}-{timestamp}.md"
        output_path = output_dir / filename
        
        # Generate markdown content
        markdown = self._generate_full_markdown(prd)
        
        # Write to file
        output_path.write_text(markdown, encoding="utf-8")
        
        return str(output_path)
    
    def _generate_full_markdown(self, prd: GeneratedPRD) -> str:
        """Generate comprehensive markdown content for the PRD."""
        lines = []
        
        # Header
        lines.append(f"# {prd.title}")
        lines.append("")
        lines.append(f"> **Generated by:** Context Graph PRD Generator")
        lines.append(f"> **Generated at:** {prd.metadata.get('generated_at', 'Unknown')}")
        lines.append(f"> **Codebase:** `{prd.metadata.get('codebase_path', 'Unknown')}`")
        lines.append(f"> **Files Analyzed:** {prd.metadata.get('files_analyzed', 0):,}")
        lines.append(f"> **Lines of Code:** {prd.metadata.get('lines_of_code', 0):,}")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Executive Summary
        lines.append("## Executive Summary")
        lines.append("")
        lines.append(prd.summary if prd.summary else "_No summary available._")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Table of Contents
        lines.append("## Table of Contents")
        lines.append("")
        toc_num = 1
        for section in prd.sections:
            lines.append(f"{toc_num}. [{section.title}](#{section.title.lower().replace(' ', '-')})")
            toc_num += 1
        if prd.features:
            lines.append(f"{toc_num}. [Detected Features](#detected-features)")
            toc_num += 1
        if prd.api_documentation:
            lines.append(f"{toc_num}. [API Documentation](#api-documentation)")
            toc_num += 1
        if prd.data_models:
            lines.append(f"{toc_num}. [Data Models](#data-models)")
            toc_num += 1
        if prd.technical_stack:
            lines.append(f"{toc_num}. [Technical Stack](#technical-stack)")
            toc_num += 1
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Sections
        for section in prd.sections:
            lines.append(f"## {section.title}")
            lines.append("")
            lines.append(section.content)
            lines.append("")
            if section.source_files:
                lines.append(f"_Source files: {', '.join(section.source_files[:5])}_")
                lines.append("")
            lines.append("---")
            lines.append("")
        
        # Features
        if prd.features:
            lines.append("## Detected Features")
            lines.append("")
            lines.append(f"The following **{len(prd.features)} features** were detected in the codebase:")
            lines.append("")
            for i, feature in enumerate(prd.features, 1):
                lines.append(f"### {i}. {feature.name}")
                lines.append("")
                lines.append(feature.description)
                lines.append("")
                if feature.endpoints:
                    lines.append("**Endpoints:**")
                    for ep in feature.endpoints[:5]:
                        lines.append(f"- `{ep}`")
                    lines.append("")
                if feature.models:
                    lines.append(f"**Related Models:** {', '.join(feature.models[:5])}")
                    lines.append("")
            lines.append("---")
            lines.append("")
        
        # API Documentation
        if prd.api_documentation:
            lines.append("## API Documentation")
            lines.append("")
            lines.append("| Method | Endpoint | Description |")
            lines.append("|--------|----------|-------------|")
            for api in prd.api_documentation[:30]:
                lines.append(f"| {api.method} | `{api.endpoint}` | {api.description} |")
            lines.append("")
            if len(prd.api_documentation) > 30:
                lines.append(f"_... and {len(prd.api_documentation) - 30} more endpoints_")
                lines.append("")
            lines.append("---")
            lines.append("")
        
        # Data Models
        if prd.data_models:
            lines.append("## Data Models")
            lines.append("")
            for model in prd.data_models[:15]:
                lines.append(f"### {model.name}")
                lines.append("")
                if model.fields:
                    lines.append("**Fields:**")
                    lines.append("")
                    lines.append("| Field | Type |")
                    lines.append("|-------|------|")
                    for field in model.fields[:15]:
                        name = field.get("name", "unknown")
                        ftype = field.get("type", "unknown")
                        lines.append(f"| `{name}` | {ftype} |")
                    lines.append("")
                if model.relationships:
                    lines.append(f"**Relationships:** {', '.join(model.relationships)}")
                    lines.append("")
            lines.append("---")
            lines.append("")
        
        # Technical Stack
        if prd.technical_stack:
            lines.append("## Technical Stack")
            lines.append("")
            for tech in prd.technical_stack:
                lines.append(f"- {tech}")
            lines.append("")
            lines.append("---")
            lines.append("")
        
        # Dependencies
        if prd.dependencies:
            lines.append("## Dependencies")
            lines.append("")
            lines.append("| Package | Version | Purpose |")
            lines.append("|---------|---------|---------|")
            for dep in prd.dependencies[:30]:
                lines.append(f"| {dep.name} | {dep.version} | {dep.purpose} |")
            lines.append("")
            lines.append("---")
            lines.append("")
        
        # Auth Requirements
        if prd.auth_requirements:
            lines.append("## Authentication Requirements")
            lines.append("")
            for auth in prd.auth_requirements:
                lines.append(f"- {auth}")
            lines.append("")
            lines.append("---")
            lines.append("")
        
        # Footer
        lines.append("---")
        lines.append("")
        lines.append("*Document generated by Context Graph PRD Generator*")
        lines.append("")
        
        return "\n".join(lines)
    
    def get_status(self, generation_id: str) -> GenerationStatus | None:
        """Get the status of a generation job."""
        return self._statuses.get(generation_id)
    
    def get_result(self, generation_id: str) -> GeneratedPRD | None:
        """Get the generated PRD result."""
        return self._generations.get(generation_id)
    
    def list_generations(self) -> list[dict[str, Any]]:
        """List all generated PRDs."""
        return [
            {
                "id": prd.id,
                "title": prd.title,
                "codebase_path": prd.metadata.get("codebase_path", ""),
                "generated_at": prd.metadata.get("generated_at", ""),
                "sections_count": len(prd.sections),
            }
            for prd in self._generations.values()
        ]
    
    def delete_generation(self, generation_id: str) -> bool:
        """Delete a generated PRD."""
        if generation_id in self._generations:
            del self._generations[generation_id]
            if generation_id in self._statuses:
                del self._statuses[generation_id]
            return True
        return False
    
    def update_section(
        self,
        generation_id: str,
        section_id: str,
        content: str,
    ) -> bool:
        """Update a section's content."""
        prd = self._generations.get(generation_id)
        if not prd:
            return False
        
        def update_in_sections(sections: list[GeneratedSection]) -> bool:
            for section in sections:
                if section.id == section_id:
                    section.content = content
                    return True
                if section.subsections:
                    if update_in_sections(section.subsections):
                        return True
            return False
        
        return update_in_sections(prd.sections)
    
    def export_to_markdown(self, generation_id: str) -> str:
        """Export generated PRD to markdown format."""
        prd = self._generations.get(generation_id)
        if not prd:
            return ""
        
        md = f"# {prd.title}\n\n"
        md += f"{prd.summary}\n\n"
        md += f"---\n\n"
        md += f"**Generated:** {prd.metadata.get('generated_at', 'Unknown')}\n"
        md += f"**Files Analyzed:** {prd.metadata.get('files_analyzed', 0)}\n"
        md += f"**Lines of Code:** {prd.metadata.get('lines_of_code', 0):,}\n\n"
        md += "---\n\n"
        
        for section in prd.sections:
            md += f"## {section.title}\n\n"
            md += f"{section.content}\n\n"
        
        return md
    
    def export_to_json(self, generation_id: str) -> str:
        """Export generated PRD to JSON format."""
        prd = self._generations.get(generation_id)
        if not prd:
            return "{}"
        
        def section_to_dict(section: GeneratedSection) -> dict[str, Any]:
            return {
                "id": section.id,
                "title": section.title,
                "content": section.content,
                "confidence": section.confidence,
                "source_files": section.source_files,
                "subsections": [section_to_dict(s) for s in section.subsections],
            }
        
        return json.dumps({
            "id": prd.id,
            "title": prd.title,
            "summary": prd.summary,
            "metadata": prd.metadata,
            "sections": [section_to_dict(s) for s in prd.sections],
            "features": [
                {
                    "name": f.name,
                    "description": f.description,
                    "endpoints": f.endpoints,
                    "models": f.models,
                }
                for f in prd.features
            ],
            "api_documentation": [
                {
                    "endpoint": ep.endpoint,
                    "method": ep.method,
                    "description": ep.description,
                }
                for ep in prd.api_documentation
            ],
            "data_models": [
                {
                    "name": dm.name,
                    "fields": dm.fields,
                    "relationships": dm.relationships,
                }
                for dm in prd.data_models
            ],
            "auth_requirements": prd.auth_requirements,
            "technical_stack": prd.technical_stack,
            "dependencies": [
                {"name": d.name, "version": d.version, "purpose": d.purpose}
                for d in prd.dependencies
            ],
        }, indent=2)
    
    def export_to_html(self, generation_id: str) -> str:
        """Export generated PRD to HTML format."""
        prd = self._generations.get(generation_id)
        if not prd:
            return ""
        
        # Convert markdown to basic HTML
        import html as html_lib
        
        def md_to_html(md: str) -> str:
            """Simple markdown to HTML conversion."""
            # Escape HTML
            text = html_lib.escape(md)
            
            # Headers
            text = re.sub(r'^### (.+)$', r'<h4>\1</h4>', text, flags=re.MULTILINE)
            text = re.sub(r'^## (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
            text = re.sub(r'^# (.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
            
            # Bold and italic
            text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
            text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
            
            # Code
            text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
            
            # Lists
            text = re.sub(r'^- (.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
            text = re.sub(r'(<li>.*</li>)', r'<ul>\1</ul>', text, flags=re.DOTALL)
            
            # Paragraphs
            text = re.sub(r'\n\n', '</p><p>', text)
            text = f'<p>{text}</p>'
            
            return text
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html_lib.escape(prd.title)}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 900px; margin: 0 auto; padding: 2rem; line-height: 1.6; }}
        h1 {{ color: #1a1a2e; border-bottom: 2px solid #16213e; padding-bottom: 0.5rem; }}
        h2 {{ color: #16213e; margin-top: 2rem; }}
        h3 {{ color: #0f3460; }}
        code {{ background: #f4f4f4; padding: 0.2rem 0.4rem; border-radius: 4px; font-size: 0.9em; }}
        pre {{ background: #f4f4f4; padding: 1rem; border-radius: 8px; overflow-x: auto; }}
        table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
        th, td {{ border: 1px solid #ddd; padding: 0.75rem; text-align: left; }}
        th {{ background: #f4f4f4; }}
        .metadata {{ background: #f8f9fa; padding: 1rem; border-radius: 8px; margin-bottom: 2rem; }}
        .section {{ margin-bottom: 2rem; }}
    </style>
</head>
<body>
    <h1>{html_lib.escape(prd.title)}</h1>
    <p class="summary">{html_lib.escape(prd.summary)}</p>
    
    <div class="metadata">
        <strong>Generated:</strong> {prd.metadata.get('generated_at', 'Unknown')}<br>
        <strong>Files Analyzed:</strong> {prd.metadata.get('files_analyzed', 0)}<br>
        <strong>Lines of Code:</strong> {prd.metadata.get('lines_of_code', 0):,}
    </div>
"""
        
        for section in prd.sections:
            html += f"""
    <div class="section">
        <h2>{html_lib.escape(section.title)}</h2>
        {md_to_html(section.content)}
    </div>
"""
        
        html += """
</body>
</html>
"""
        
        return html


# Global instance for API routes
_generator: PRDGenerator | None = None


def get_generator() -> PRDGenerator:
    """Get or create the PRD generator instance."""
    global _generator
    if _generator is None:
        _generator = PRDGenerator()
    return _generator
