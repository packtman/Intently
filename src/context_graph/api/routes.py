"""
API Routes for Context Graph.

Supports multi-dimension review (Security, Privacy, Compliance) in parallel.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any
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

# In-memory store for reviews (use Redis/DB in production)
reviews_store: dict[str, ReviewResult] = {}
review_status: dict[str, dict[str, Any]] = {}


# Request/Response Models

class PRDInput(BaseModel):
    """PRD content input."""
    content: str = Field(..., description="PRD content (markdown or plain text)")
    source_type: str = Field("markdown", description="Source type: markdown, notion, gdocs")
    title: str | None = Field(None, description="Optional title override")


class CodebaseInput(BaseModel):
    """Codebase path input."""
    path: str = Field(..., description="Path to codebase directory or GitHub URL (e.g., owner/repo)")
    languages: list[str] = Field(["python", "kotlin"], description="Languages to analyze")
    branch: str | None = Field(None, description="GitHub branch to analyze")
    pr: int | None = Field(None, description="GitHub PR number to analyze")
    github_token: str | None = Field(None, description="GitHub token for private repos")


class ReviewConfigInput(BaseModel):
    """Review configuration options."""
    use_llm: bool = Field(True, description="Use LLM for analysis (requires API keys)")
    dimensions: list[str] = Field(
        default=["security"], 
        description="Review dimensions: security, privacy, compliance, engineering, architecture"
    )
    compliance_frameworks: list[str] = Field(
        default=["soc2", "hipaa", "pci_dss"],
        description="Compliance frameworks to check: soc2, hipaa, pci_dss, iso_27001, gdpr, ccpa"
    )
    openai_api_key: str | None = Field(None, description="OpenAI API key (optional, uses env var if not provided)")
    anthropic_api_key: str | None = Field(None, description="Anthropic API key (optional, uses env var if not provided)")


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
    dimensions: list[str] = Field(default_factory=list, description="Dimensions being analyzed")
    result: dict[str, Any] | None = None


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
    
    # Initialize status
    review_status[review_id] = {
        "status": "pending",
        "progress": 0.0,
        "message": "Review queued",
    }
    
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
async def get_review_status(review_id: str) -> ReviewStatusResponse:
    """Get the status of a review."""
    if review_id not in review_status:
        raise HTTPException(status_code=404, detail="Review not found")
    
    status = review_status[review_id]
    result = None
    
    if status["status"] == "completed" and review_id in reviews_store:
        generator = JSONReportGenerator()
        result = generator.generate(reviews_store[review_id])
    
    return ReviewStatusResponse(
        review_id=review_id,
        status=status["status"],
        progress=status["progress"],
        message=status["message"],
        dimensions=status.get("dimensions", []),
        result=result,
    )


@router.get("/reviews/{review_id}")
async def get_review(review_id: str) -> dict[str, Any]:
    """Get the complete review result."""
    if review_id not in reviews_store:
        raise HTTPException(status_code=404, detail="Review not found")
    
    generator = JSONReportGenerator()
    return generator.generate(reviews_store[review_id])


@router.get("/reviews/{review_id}/dashboard")
async def get_review_dashboard(review_id: str) -> dict[str, Any]:
    """Get dashboard-formatted review data."""
    if review_id not in reviews_store:
        raise HTTPException(status_code=404, detail="Review not found")
    
    generator = DashboardDataGenerator()
    return generator.generate(reviews_store[review_id])


@router.get("/reviews/{review_id}/markdown")
async def get_review_markdown(review_id: str) -> dict[str, str]:
    """Get markdown report."""
    if review_id not in reviews_store:
        raise HTTPException(status_code=404, detail="Review not found")
    
    generator = MarkdownReportGenerator()
    markdown = generator.generate(reviews_store[review_id])
    return {"markdown": markdown}


@router.post("/parse-prd")
async def parse_prd(prd: PRDInput) -> dict[str, Any]:
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
async def analyze_codebase(codebase: CodebaseInput) -> dict[str, Any]:
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
async def list_reviews() -> list[dict[str, Any]]:
    """List all reviews."""
    return [
        {
            "review_id": review_id,
            "title": result.intent.title,
            "status": review_status.get(review_id, {}).get("status", "unknown"),
            "risk_rating": result.risk_rating,
            "findings_count": len(result.all_findings),
            "dimensions": [d.value for d in result.dimensions_analyzed],
            "security_findings": len(result.security_findings),
            "privacy_findings": len(result.privacy_findings),
            "compliance_findings": len(result.compliance_findings),
            "reviewed_at": result.reviewed_at.isoformat(),
        }
        for review_id, result in reviews_store.items()
    ]


# Background task

async def run_review(review_id: str, request: ReviewRequest) -> None:
    """Run the multi-dimension security review in background."""
    import logging
    cloned_repo: ClonedRepo | None = None
    
    try:
        # Parse dimensions from config
        logging.info(f"=== REVIEW {review_id} STARTED ===")
        logging.info(f"Raw dimensions from request: {request.config.dimensions}")
        requested_dimensions = _parse_dimensions(request.config.dimensions)
        dimension_names = [d.value for d in requested_dimensions]
        logging.info(f"Parsed dimensions: {dimension_names}")
        
        review_status[review_id] = {
            "status": "running",
            "progress": 0.1,
            "message": "Parsing PRD...",
            "dimensions": dimension_names,
        }
        
        # Parse PRD
        parser = _get_parser(request.prd.source_type)
        intent = parser.parse(request.prd.content, request.prd.title or "API Upload")
        
        review_status[review_id] = {
            "status": "running",
            "progress": 0.3,
            "message": "Analyzing codebase...",
            "dimensions": dimension_names,
        }
        
        # Resolve codebase path (local or GitHub)
        codebase_path = _normalize_github_url(request.codebase.path)
        
        if _is_github_url(codebase_path):
            review_status[review_id]["message"] = "Cloning from GitHub..."
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
        
        review_status[review_id]["message"] = "Analyzing codebase..."
        
        analyzer = _get_analyzer(request.codebase.languages)
        state = analyzer.analyze_codebase(path)
        
        review_status[review_id] = {
            "status": "running",
            "progress": 0.6,
            "message": f"Running {', '.join(dimension_names)} analysis...",
            "dimensions": dimension_names,
        }
        
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
            review_status[review_id]["message"] = "Warning: LLM requested but no API keys found. Using pattern-based analysis only."
        elif llm_enabled:
            review_status[review_id]["message"] = f"Running AI-powered {', '.join(dimension_names)} analysis..."
        
        engine = SecurityReviewEngine(config)
        
        review_status[review_id] = {
            "status": "running",
            "progress": 0.8,
            "message": "Generating findings across all dimensions...",
            "dimensions": dimension_names,
        }
        
        # Run review
        result = await engine.review(intent, state)
        
        # Store config and original PRD on result for re-analysis
        result.config = config  # Preserve original config for re-analysis
        result.original_prd_content = intent.raw_content  # Preserve original PRD
        
        # Store result
        reviews_store[review_id] = result
        
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
        
        review_status[review_id] = {
            "status": "completed",
            "progress": 1.0,
            "message": f"Review completed with {findings_summary}",
            "dimensions": dimension_names,
        }
        
    except Exception as e:
        review_status[review_id] = {
            "status": "failed",
            "progress": 0.0,
            "message": f"Review failed: {str(e)}",
            "dimensions": [],
        }
    
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


def _get_analyzer(languages: list[str]) -> MultiLanguageAnalyzer:
    """Get multi-language analyzer."""
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
    
    return analyzer


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

