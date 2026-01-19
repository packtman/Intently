"""
API Routes for PRD Generation.

Generates comprehensive PRD documents from codebase analysis.
"""

from __future__ import annotations

import os
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from context_graph.config.features import get_features


router = APIRouter(prefix="/prd-generator", tags=["prd-generator"])


# Request/Response Models

class GeneratorConfigInput(BaseModel):
    """Configuration for PRD generation."""
    codebase_path: str = Field(..., description="Path to codebase to analyze")
    languages: list[str] = Field(
        default=["auto"],
        description="Languages to analyze: auto, python, kotlin, typescript, etc."
    )
    focus_areas: list[str] = Field(
        default=[],
        description="Focus areas: api, security, data, auth, etc."
    )
    include_api_docs: bool = Field(True, description="Include API documentation")
    include_data_models: bool = Field(True, description="Include data model documentation")
    include_auth_flow: bool = Field(True, description="Include authentication flow")
    include_architecture: bool = Field(True, description="Include architecture documentation")
    detail_level: str = Field("detailed", description="Detail level: overview, detailed, comprehensive")
    output_directory: str | None = Field(None, description="Directory to save generated PRD")
    auto_save: bool = Field(True, description="Automatically save to .md file")


class GenerateRequest(BaseModel):
    """Request to generate a PRD."""
    config: GeneratorConfigInput
    openai_api_key: str | None = Field(None, description="OpenAI API key for AI generation")
    anthropic_api_key: str | None = Field(None, description="Anthropic API key for AI generation")


class GenerateResponse(BaseModel):
    """Response from PRD generation."""
    generation_id: str
    status: str
    message: str


class GenerationStatusResponse(BaseModel):
    """Status of a PRD generation job."""
    generation_id: str
    status: str
    progress: float
    current_step: str
    steps_completed: list[str]
    error_message: str | None = None


class GeneratedPRDResponse(BaseModel):
    """Generated PRD response."""
    id: str
    title: str
    summary: str
    sections: list[dict[str, Any]]
    metadata: dict[str, Any]
    features: list[dict[str, Any]]
    api_documentation: list[dict[str, Any]]
    data_models: list[dict[str, Any]]
    auth_requirements: list[str]
    technical_stack: list[str]
    dependencies: list[dict[str, Any]]
    output_file_path: str | None = None


# Routes

@router.post("/generate", response_model=GenerateResponse)
async def generate_prd(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
) -> GenerateResponse:
    """
    Start PRD generation from a codebase.
    
    Analyzes the codebase and generates a comprehensive PRD document.
    Returns immediately with a generation ID to poll for status.
    """
    features = get_features()
    
    if not features.enable_prd_generator:
        raise HTTPException(
            status_code=403,
            detail="PRD generator is not enabled. Set FEATURE_PRD_GENERATOR=true"
        )
    
    # Validate codebase path
    from pathlib import Path
    codebase_path = Path(request.config.codebase_path)
    if not codebase_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Codebase path not found: {request.config.codebase_path}"
        )
    
    generation_id = str(uuid4())
    
    # Get or create generator
    from context_graph.pm.prd_generator import get_generator, GeneratorConfig
    
    generator = get_generator()
    
    # Set API keys if provided
    if request.openai_api_key:
        generator.openai_api_key = request.openai_api_key
    elif os.getenv("OPENAI_API_KEY"):
        generator.openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if request.anthropic_api_key:
        generator.anthropic_api_key = request.anthropic_api_key
    elif os.getenv("ANTHROPIC_API_KEY"):
        generator.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    
    # Create config
    config = GeneratorConfig(
        codebase_path=request.config.codebase_path,
        languages=request.config.languages,
        focus_areas=request.config.focus_areas,
        include_api_docs=request.config.include_api_docs,
        include_data_models=request.config.include_data_models,
        include_auth_flow=request.config.include_auth_flow,
        include_architecture=request.config.include_architecture,
        detail_level=request.config.detail_level,
        output_directory=request.config.output_directory or "",
        auto_save=request.config.auto_save,
    )
    
    # Start generation in background
    background_tasks.add_task(
        _run_generation,
        generator,
        config,
        generation_id,
    )
    
    return GenerateResponse(
        generation_id=generation_id,
        status="pending",
        message=f"PRD generation started. Poll /api/prd-generator/status/{generation_id} for updates.",
    )


@router.get("/status/{generation_id}", response_model=GenerationStatusResponse)
async def get_generation_status(generation_id: str) -> GenerationStatusResponse:
    """Get the status of a PRD generation job."""
    from context_graph.pm.prd_generator import get_generator
    
    generator = get_generator()
    status = generator.get_status(generation_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Generation not found")
    
    return GenerationStatusResponse(
        generation_id=generation_id,
        status=status.status,
        progress=status.progress,
        current_step=status.current_step,
        steps_completed=status.steps_completed,
        error_message=status.error_message or None,
    )


@router.get("/result/{generation_id}", response_model=GeneratedPRDResponse)
async def get_generation_result(generation_id: str) -> GeneratedPRDResponse:
    """Get the generated PRD result."""
    from context_graph.pm.prd_generator import get_generator
    
    generator = get_generator()
    prd = generator.get_result(generation_id)
    
    if not prd:
        status = generator.get_status(generation_id)
        if status and status.status != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Generation not completed. Status: {status.status}"
            )
        raise HTTPException(status_code=404, detail="Generation not found")
    
    return GeneratedPRDResponse(
        id=prd.id,
        title=prd.title,
        summary=prd.summary,
        sections=[
            {
                "id": s.id,
                "title": s.title,
                "content": s.content,
                "confidence": s.confidence,
                "source_files": s.source_files,
            }
            for s in prd.sections
        ],
        metadata=prd.metadata,
        features=[
            {
                "name": f.name,
                "description": f.description,
                "endpoints": f.endpoints,
                "models": f.models,
            }
            for f in prd.features
        ],
        api_documentation=[
            {
                "endpoint": ep.endpoint,
                "method": ep.method,
                "description": ep.description,
                "parameters": ep.parameters,
                "response": ep.response,
            }
            for ep in prd.api_documentation
        ],
        data_models=[
            {
                "name": dm.name,
                "fields": dm.fields,
                "relationships": dm.relationships,
            }
            for dm in prd.data_models
        ],
        auth_requirements=prd.auth_requirements,
        technical_stack=prd.technical_stack,
        dependencies=[
            {
                "name": d.name,
                "version": d.version,
                "purpose": d.purpose,
            }
            for d in prd.dependencies
        ],
        output_file_path=prd.output_file_path or None,
    )


@router.get("/result/{generation_id}/markdown")
async def get_generation_markdown(generation_id: str) -> dict[str, str]:
    """Get the generated PRD as markdown."""
    from context_graph.pm.prd_generator import get_generator
    
    generator = get_generator()
    markdown = generator.export_to_markdown(generation_id)
    
    if not markdown:
        raise HTTPException(status_code=404, detail="Generation not found")
    
    return {"markdown": markdown}


@router.get("/result/{generation_id}/json")
async def get_generation_json(generation_id: str) -> dict[str, Any]:
    """Get the generated PRD as JSON."""
    from context_graph.pm.prd_generator import get_generator
    import json
    
    generator = get_generator()
    json_str = generator.export_to_json(generation_id)
    
    if not json_str or json_str == "{}":
        raise HTTPException(status_code=404, detail="Generation not found")
    
    return json.loads(json_str)


@router.get("/result/{generation_id}/html")
async def get_generation_html(generation_id: str) -> dict[str, str]:
    """Get the generated PRD as HTML."""
    from context_graph.pm.prd_generator import get_generator
    
    generator = get_generator()
    html = generator.export_to_html(generation_id)
    
    if not html:
        raise HTTPException(status_code=404, detail="Generation not found")
    
    return {"html": html}


@router.get("/list")
async def list_generations() -> list[dict[str, Any]]:
    """List all generated PRDs."""
    from context_graph.pm.prd_generator import get_generator
    
    generator = get_generator()
    return generator.list_generations()


@router.delete("/{generation_id}")
async def delete_generation(generation_id: str) -> dict[str, Any]:
    """Delete a generated PRD."""
    from context_graph.pm.prd_generator import get_generator
    
    generator = get_generator()
    success = generator.delete_generation(generation_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Generation not found")
    
    return {"success": True, "message": "Generation deleted"}


@router.patch("/{generation_id}/section/{section_id}")
async def update_section(
    generation_id: str,
    section_id: str,
    content: str,
) -> dict[str, Any]:
    """Update a section's content in a generated PRD."""
    from context_graph.pm.prd_generator import get_generator
    
    generator = get_generator()
    success = generator.update_section(generation_id, section_id, content)
    
    if not success:
        raise HTTPException(status_code=404, detail="Generation or section not found")
    
    return {"success": True, "message": "Section updated"}


# Background task

async def _run_generation(
    generator: Any,
    config: Any,
    generation_id: str,
) -> None:
    """Run PRD generation."""
    await generator.generate(config, generation_id)
