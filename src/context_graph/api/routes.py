"""
API Routes for Context Graph.

Supports multi-dimension review (Security, Privacy, Compliance) in parallel.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel, Field

from context_graph.parsers import MarkdownPRDParser, NotionPRDParser, GoogleDocsPRDParser
from context_graph.analyzers import (
    MultiLanguageAnalyzer, 
    PythonAnalyzer, 
    KotlinAnalyzer,
    TypeScriptAnalyzer,
    YAMLAnalyzer,
    JSONAnalyzer,
)
from context_graph.security.review_engine import SecurityReviewEngine, ReviewConfig, ReviewResult
from context_graph.security.delta_analyzer import DeltaAnalyzer
from context_graph.reports.json_report import JSONReportGenerator, DashboardDataGenerator
from context_graph.reports.markdown_report import MarkdownReportGenerator
from context_graph.integrations.github import GitHubIntegration, ClonedRepo
from context_graph.core.models import ReviewDimension, ComplianceFramework
from context_graph.storage.config import get_review_storage


def _normalize_github_url(path: str) -> str:
    """Normalize GitHub URL, fixing common typos."""
    path = path.strip()
    # Fix common typos like https:/github.com (single slash)
    path = path.replace("https:/github.com", "https://github.com")
    path = path.replace("http:/github.com", "https://github.com")
    return path


def _is_github_url(path: str) -> bool:
    """Check if a path is a GitHub URL or owner/repo format."""
    path = _normalize_github_url(path)
    
    return (
        path.startswith("https://github.com") or
        path.startswith("http://github.com") or
        path.startswith("github.com") or
        # owner/repo format (not a local path)
        ("/" in path and not path.startswith("/") and not path.startswith(".") and not Path(path).exists())
    )


router = APIRouter(tags=["security-review"])


# Request/Response Models

class PRDInput(BaseModel):
    """PRD content input."""
    content: str = Field(..., description="PRD content (markdown or plain text)")
    source_type: str = Field("markdown", description="Source type: markdown, notion, gdocs")
    title: Optional[str] = Field(None, description="Optional title override")


class CodebaseInput(BaseModel):
    """Codebase path input."""
    path: str = Field(..., description="Path to codebase directory or GitHub URL (e.g., owner/repo)")
    languages: List[str] = Field(["python", "kotlin"], description="Languages to analyze")
    branch: Optional[str] = Field(None, description="GitHub branch to analyze")
    pr: Optional[int] = Field(None, description="GitHub PR number to analyze")
    github_token: Optional[str] = Field(None, description="GitHub token for private repos")
    use_hybrid: bool = Field(True, description="Use hybrid analyzer (AST fast + LSP on-demand)")


class ReviewConfigInput(BaseModel):
    """Review configuration options."""
    use_llm: bool = Field(True, description="Use LLM for analysis (requires API keys)")
    dimensions: List[str] = Field(
        default=["security"], 
        description="Review dimensions: security, privacy, compliance, engineering, architecture"
    )
    compliance_frameworks: List[str] = Field(
        default=["soc2", "hipaa", "pci_dss"],
        description="Compliance frameworks to check: soc2, hipaa, pci_dss, iso_27001, gdpr, ccpa"
    )
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key (optional, uses env var if not provided)")
    anthropic_api_key: Optional[str] = Field(None, description="Anthropic API key (optional, uses env var if not provided)")


class ReviewRequest(BaseModel):
    """Complete review request."""
    prd: PRDInput
    codebase: CodebaseInput
    config: ReviewConfigInput = Field(default_factory=ReviewConfigInput, description="Review configuration")


class ReviewResponse(BaseModel):
    """Review response."""
    review_id: str
    status: str
    message: str


class ReviewStatusResponse(BaseModel):
    """Review status response."""
    review_id: str
    status: str
    progress: float
    message: str
    dimensions: List[str] = Field(default_factory=list, description="Dimensions being analyzed")
    result: Optional[Dict[str, Any]] = None


# Routes

@router.post("/reviews", response_model=ReviewResponse)
async def create_review(
    request: ReviewRequest,
    background_tasks: BackgroundTasks,
) -> ReviewResponse:
    """
    Create a new security review.
    
    Starts async analysis of PRD against codebase.
    """
    review_id = str(uuid4())
    storage = get_review_storage()
    
    # Initialize status
    await storage.update_review_status(
        review_id=review_id,
        status="pending",
        progress=0.0,
        message="Review queued",
    )
    
    # Run review in background
    background_tasks.add_task(
        run_review,
        review_id,
        request,
    )
    
    return ReviewResponse(
        review_id=review_id,
        status="pending",
        message="Review started. Poll /api/reviews/{review_id}/status for updates.",
    )


@router.get("/reviews/{review_id}/status", response_model=ReviewStatusResponse)
async def get_review_status_endpoint(review_id: str) -> ReviewStatusResponse:
    """Get the status of a review."""
    storage = get_review_storage()
    status = await storage.get_review_status(review_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Review not found")
    
    result = None
    
    if status["status"] == "completed":
        review = await storage.get_review(review_id)
        if review:
            generator = JSONReportGenerator()
            result = generator.generate(review)
    
    return ReviewStatusResponse(
        review_id=review_id,
        status=status["status"],
        progress=status["progress"],
        message=status["message"],
        dimensions=status.get("dimensions", []),
        result=result,
    )


@router.get("/reviews/{review_id}")
async def get_review(review_id: str) -> Dict[str, Any]:
    """Get the complete review result."""
    storage = get_review_storage()
    review = await storage.get_review(review_id)
    
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    generator = JSONReportGenerator()
    return generator.generate(review)


@router.get("/reviews/{review_id}/dashboard")
async def get_review_dashboard(review_id: str) -> Dict[str, Any]:
    """Get dashboard-formatted review data."""
    storage = get_review_storage()
    review = await storage.get_review(review_id)
    
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    generator = DashboardDataGenerator()
    return generator.generate(review)


@router.get("/reviews/{review_id}/markdown")
async def get_review_markdown(review_id: str) -> Dict[str, str]:
    """Get markdown report."""
    storage = get_review_storage()
    review = await storage.get_review(review_id)
    
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    generator = MarkdownReportGenerator()
    markdown = generator.generate(review)
    return {"markdown": markdown}


@router.post("/parse-prd")
async def parse_prd(prd: PRDInput) -> Dict[str, Any]:
    """Parse a PRD and extract intent (without full review)."""
    parser = _get_parser(prd.source_type)
    intent = parser.parse(prd.content, prd.title or "API Upload")
    
    return {
        "title": intent.title,
        "summary": intent.summary,
        "features": intent.features,
        "user_stories": intent.user_stories,
        "data_entities": [
            {
                "name": e.name,
                "type": e.entity_type.value,
                "is_sensitive": e.is_sensitive,
            }
            for e in intent.data_entities
        ],
        "api_changes": intent.api_changes,
        "auth_requirements": intent.auth_requirements,
        "external_integrations": intent.external_integrations,
    }


@router.post("/analyze-codebase")
async def analyze_codebase(codebase: CodebaseInput) -> Dict[str, Any]:
    """Analyze a codebase and extract state (without full review)."""
    cloned_repo = None
    codebase_path = _normalize_github_url(codebase.path)
    
    try:
        if _is_github_url(codebase_path):
            github = GitHubIntegration(
                token=codebase.github_token or os.getenv("GITHUB_TOKEN")
            )
            cloned_repo = github.clone(
                codebase_path,
                branch=codebase.branch,
                pr=codebase.pr,
            )
            path = cloned_repo.path
        else:
            path = Path(codebase_path)
            if not path.exists():
                raise HTTPException(status_code=400, detail=f"Path not found: {codebase_path}")
        
        # Use hybrid analyzer if requested (AST fast + LSP on-demand)
        if codebase.use_hybrid:
            print("🚀 Using HYBRID analyzer (AST fast + LSP on-demand)", flush=True)
            state = _get_hybrid_state(path, codebase.languages)
            if hasattr(state, '_hybrid_analysis'):
                meta = state._hybrid_analysis
                print(f"   AST analysis: {meta['ast_time_ms']:.0f}ms, {meta['files_analyzed']} files", flush=True)
                print(f"   Pending LSP queries: {meta['pending_lsp_queries']}", flush=True)
        else:
            print("📊 Using TRADITIONAL analyzer (regex + Python AST)", flush=True)
            analyzer = _get_analyzer(codebase.languages)
            state = analyzer.analyze_codebase(path)
        
        return {
            "path": state.codebase_path,
            "files_analyzed": state.files_analyzed,
            "lines_of_code": state.lines_of_code,
            "api_endpoints": state.api_endpoints[:50],  # Limit response size
            "data_models": state.data_models[:50],
            "auth_patterns": state.auth_patterns,
            "existing_controls": state.existing_controls,
        }
    finally:
        if cloned_repo:
            cloned_repo.cleanup()


@router.get("/reviews")
async def list_reviews() -> List[Dict[str, Any]]:
    """List all reviews."""
    storage = get_review_storage()
    return await storage.list_reviews()


# Background task

async def run_review(review_id: str, request: ReviewRequest) -> None:
    """Run the multi-dimension security review in background."""
    import logging
    cloned_repo: ClonedRepo | None = None
    storage = get_review_storage()
    
    try:
        # Parse dimensions from config
        logging.info(f"=== REVIEW {review_id} STARTED ===")
        logging.info(f"Raw dimensions from request: {request.config.dimensions}")
        requested_dimensions = _parse_dimensions(request.config.dimensions)
        dimension_names = [d.value for d in requested_dimensions]
        logging.info(f"Parsed dimensions: {dimension_names}")
        
        await storage.update_review_status(
            review_id=review_id,
            status="running",
            progress=0.1,
            message="Parsing PRD...",
            dimensions=dimension_names,
        )
        
        # Parse PRD
        parser = _get_parser(request.prd.source_type)
        intent = parser.parse(request.prd.content, request.prd.title or "API Upload")
        
        await storage.update_review_status(
            review_id=review_id,
            status="running",
            progress=0.3,
            message="Analyzing codebase...",
            dimensions=dimension_names,
        )
        
        # Resolve codebase path (local or GitHub)
        codebase_path = _normalize_github_url(request.codebase.path)
        
        if _is_github_url(codebase_path):
            await storage.update_review_status(
                review_id=review_id,
                status="running",
                progress=0.35,
                message="Cloning from GitHub...",
                dimensions=dimension_names,
            )
            github = GitHubIntegration(
                token=request.codebase.github_token or os.getenv("GITHUB_TOKEN")
            )
            cloned_repo = github.clone(
                codebase_path,
                branch=request.codebase.branch,
                pr=request.codebase.pr,
            )
            path = cloned_repo.path
        else:
            path = Path(codebase_path)
            if not path.exists():
                raise ValueError(f"Codebase path not found: {path}")
        
        await storage.update_review_status(
            review_id=review_id,
            status="running",
            progress=0.4,
            message="Analyzing codebase...",
            dimensions=dimension_names,
        )
        
        # Use hybrid analyzer if requested (AST fast + LSP on-demand)
        if request.codebase.use_hybrid:
            print(f"🚀 [Review {review_id}] Using HYBRID analyzer (AST fast + LSP on-demand)", flush=True)
            state = _get_hybrid_state(path, request.codebase.languages)
            if hasattr(state, '_hybrid_analysis'):
                meta = state._hybrid_analysis
                print(f"   AST analysis: {meta['ast_time_ms']:.0f}ms, {meta['files_analyzed']} files", flush=True)
                print(f"   Pending LSP queries: {meta['pending_lsp_queries']}", flush=True)
        else:
            print(f"📊 [Review {review_id}] Using TRADITIONAL analyzer (regex + Python AST)", flush=True)
            analyzer = _get_analyzer(request.codebase.languages)
            state = analyzer.analyze_codebase(path)
        
        await storage.update_review_status(
            review_id=review_id,
            status="running",
            progress=0.6,
            message=f"Running {', '.join(dimension_names)} analysis...",
            dimensions=dimension_names,
        )
        
        # Configure review engine with multi-dimension support
        openai_key = request.config.openai_api_key or os.getenv("OPENAI_API_KEY")
        anthropic_key = request.config.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        has_api_keys = bool(openai_key or anthropic_key)
        
        # Only enable LLM if user wants it AND API keys are available
        use_llm_requested = request.config.use_llm
        llm_enabled = use_llm_requested and has_api_keys
        
        # Parse compliance frameworks
        compliance_frameworks = _parse_compliance_frameworks(request.config.compliance_frameworks)
        
        config = ReviewConfig(
            openai_api_key=openai_key,
            anthropic_api_key=anthropic_key,
            use_llm=llm_enabled,
            llm_only=llm_enabled,  # When LLM is enabled, only use LLM findings for detailed AI analysis
            use_pattern_matching=not llm_enabled,  # Disable pattern matching when using LLM
            use_graph_analysis=not llm_enabled,    # Disable graph analysis when using LLM
            dimensions=requested_dimensions,
            compliance_frameworks=compliance_frameworks,
        )
        
        logging.info(f"Config created with dimensions: {[d.value for d in config.dimensions]}")
        logging.info(f"LLM enabled: {llm_enabled}, pattern_matching: {config.use_pattern_matching}")
        
        # Log status for debugging
        if use_llm_requested and not has_api_keys:
            await storage.update_review_status(
                review_id=review_id,
                status="running",
                progress=0.65,
                message="Warning: LLM requested but no API keys found. Using pattern-based analysis only.",
                dimensions=dimension_names,
            )
        elif llm_enabled:
            await storage.update_review_status(
                review_id=review_id,
                status="running",
                progress=0.65,
                message=f"Running AI-powered {', '.join(dimension_names)} analysis...",
                dimensions=dimension_names,
            )
        
        engine = SecurityReviewEngine(config)
        
        await storage.update_review_status(
            review_id=review_id,
            status="running",
            progress=0.8,
            message="Generating findings across all dimensions...",
            dimensions=dimension_names,
        )
        
        # Run review
        result = await engine.review(intent, state)
        
        # Store config and original PRD on result for re-analysis
        result.config = config  # Preserve original config for re-analysis
        result.original_prd_content = intent.raw_content  # Preserve original PRD
        
        # Store result in persistent storage
        await storage.save_review(review_id, result)
        
        # Build completion message with dimension breakdown
        import logging
        logging.info(f"Review completed. All findings: {len(result.all_findings)}")
        logging.info(f"  Security: {len(result.security_findings)}")
        logging.info(f"  Privacy: {len(result.privacy_findings)}")
        logging.info(f"  Compliance: {len(result.compliance_findings)}")
        logging.info(f"  Engineering: {len(result.engineering_findings)}")
        logging.info(f"  Architecture: {len(result.architecture_findings)}")
        
        breakdowns = []
        if ReviewDimension.SECURITY in requested_dimensions:
            breakdowns.append(f"{len(result.security_findings)} security")
        if ReviewDimension.PRIVACY in requested_dimensions:
            breakdowns.append(f"{len(result.privacy_findings)} privacy")
        if ReviewDimension.COMPLIANCE in requested_dimensions:
            breakdowns.append(f"{len(result.compliance_findings)} compliance")
        if ReviewDimension.ENGINEERING in requested_dimensions:
            breakdowns.append(f"{len(result.engineering_findings)} engineering")
        if ReviewDimension.ARCHITECTURE in requested_dimensions:
            breakdowns.append(f"{len(result.architecture_findings)} architecture")
        findings_summary = f"{len(result.all_findings)} findings ({', '.join(breakdowns)})"
        
        await storage.update_review_status(
            review_id=review_id,
            status="completed",
            progress=1.0,
            message=f"Review completed with {findings_summary}",
            dimensions=dimension_names,
        )
        
    except Exception as e:
        await storage.update_review_status(
            review_id=review_id,
            status="failed",
            progress=0.0,
            message=f"Review failed: {str(e)}",
            dimensions=[],
        )
    
    finally:
        # Cleanup cloned repo if any
        if cloned_repo:
            cloned_repo.cleanup()


# Helpers

def _get_parser(source_type: str):
    """Get appropriate parser for source type."""
    parsers = {
        "markdown": MarkdownPRDParser,
        "notion": NotionPRDParser,
        "gdocs": GoogleDocsPRDParser,
    }
    parser_class = parsers.get(source_type, MarkdownPRDParser)
    return parser_class()


def _get_analyzer(languages: list[str], use_hybrid: bool = False) -> MultiLanguageAnalyzer:
    """Get multi-language analyzer.
    
    Args:
        languages: List of languages to analyze
        use_hybrid: If True, uses HybridAnalyzer (AST fast + LSP on-demand)
    """
    analyzer = MultiLanguageAnalyzer()
    
    # Auto-detect all languages
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
    
    # Set hybrid mode flag (used by enhanced analysis)
    analyzer._use_hybrid = use_hybrid
    
    return analyzer


def _get_hybrid_state(path: Path, languages: list[str]) -> State:
    """Get state using HybridAnalyzer (AST fast + LSP on-demand).
    
    This gives you:
    - Fast AST analysis (80%) - classes, functions, imports
    - LSP on-demand (20%) - cross-file refs, types, diagnostics
    """
    from context_graph.code_graph import HybridAnalyzer
    from context_graph.core.models import State, Entity, EntityType
    
    analyzer = HybridAnalyzer(path)
    result = analyzer.analyze_fast(languages=languages)
    
    # Convert HybridResult to State
    state = State(codebase_path=str(path))
    
    for rel_path, ast_result in result.ast_results.items():
        file_path = path / rel_path
        
        # Add classes as entities
        for cls in ast_result.classes:
            entity = Entity(
                name=cls["name"],
                entity_type=EntityType.DATA if "model" in cls["name"].lower() else EntityType.CLASS,
                source=str(file_path),
            )
            state.entities.append(entity)
            
            # Check if it looks like a data model
            if any(base in ["BaseModel", "Model", "Entity"] for base in cls.get("bases", [])):
                state.data_models.append({
                    "name": cls["name"],
                    "file": str(file_path),
                    "line": cls.get("line", 0),
                })
        
        # Add functions as entities
        for func in ast_result.functions:
            entity = Entity(
                name=func["name"],
                entity_type=EntityType.FUNCTION,
                source=str(file_path),
            )
            state.entities.append(entity)
            
            # Check for endpoint decorators
            decorators = func.get("decorators", [])
            if any(d in ["get", "post", "put", "delete", "patch", "route", "Get", "Post", "Put", "Delete"] for d in decorators):
                state.api_endpoints.append({
                    "path": func["name"],
                    "method": next((d.upper() for d in decorators if d.lower() in ["get", "post", "put", "delete", "patch"]), "GET"),
                    "file": str(file_path),
                    "line": func.get("line", 0),
                })
        
        state.files_analyzed += 1
    
    # Store hybrid metadata for tracing
    state._hybrid_analysis = {
        "ast_time_ms": result.ast_time_ms,
        "files_analyzed": result.files_analyzed,
        "pending_lsp_queries": len(result.pending_queries),
    }
    
    return state


def _parse_dimensions(dimension_strings: list[str]) -> list[ReviewDimension]:
    """Parse dimension strings to ReviewDimension enums."""
    dimension_map = {
        "security": ReviewDimension.SECURITY,
        "privacy": ReviewDimension.PRIVACY,
        "compliance": ReviewDimension.COMPLIANCE,
        "engineering": ReviewDimension.ENGINEERING,
        "architecture": ReviewDimension.ARCHITECTURE,
    }
    
    dimensions = []
    for dim_str in dimension_strings:
        dim_lower = dim_str.lower().strip()
        if dim_lower in dimension_map:
            dimensions.append(dimension_map[dim_lower])
    
    # Default to security if no valid dimensions specified
    if not dimensions:
        dimensions = [ReviewDimension.SECURITY]
    
    return dimensions


def _parse_compliance_frameworks(framework_strings: list[str]) -> list[ComplianceFramework]:
    """Parse compliance framework strings to ComplianceFramework enums."""
    framework_map = {
        "soc2": ComplianceFramework.SOC2,
        "hipaa": ComplianceFramework.HIPAA,
        "pci_dss": ComplianceFramework.PCI_DSS,
        "pci-dss": ComplianceFramework.PCI_DSS,
        "pcidss": ComplianceFramework.PCI_DSS,
        "iso_27001": ComplianceFramework.ISO_27001,
        "iso-27001": ComplianceFramework.ISO_27001,
        "iso27001": ComplianceFramework.ISO_27001,
        "gdpr": ComplianceFramework.GDPR,
        "ccpa": ComplianceFramework.CCPA,
    }
    
    frameworks = []
    for fw_str in framework_strings:
        fw_lower = fw_str.lower().strip()
        if fw_lower in framework_map:
            frameworks.append(framework_map[fw_lower])
    
    # Default frameworks if none specified
    if not frameworks:
        frameworks = [
            ComplianceFramework.SOC2,
            ComplianceFramework.HIPAA,
            ComplianceFramework.PCI_DSS,
        ]
    
    return frameworks

