"""
API Routes for Bulk PRD Analysis.

Supports analyzing up to 20 PRD files in parallel across multiple review dimensions.
"""

from __future__ import annotations

import os
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from context_graph.config.features import get_features
from context_graph.core.models import ReviewDimension
from context_graph.tracing import get_collector


router = APIRouter(prefix="/bulk", tags=["bulk-prd-analysis"])


# In-memory store for bulk analysis results
bulk_results_store: dict[str, Any] = {}
bulk_status_store: dict[str, dict[str, Any]] = {}


# Request/Response Models

class PRDFileInput(BaseModel):
    """Single PRD file input for bulk analysis."""
    file_path: str = Field("", description="Original file path")
    file_name: str = Field("", description="File name for display")
    content: str = Field(..., description="PRD content")
    codebase_path: str | None = Field(None, description="Codebase path for this PRD")


class BulkAnalysisRequest(BaseModel):
    """Request to analyze multiple PRDs in bulk."""
    prds: list[PRDFileInput] = Field(..., description="List of PRD files to analyze")
    default_codebase_path: str | None = Field(None, description="Default codebase path")
    dimensions: list[str] = Field(
        default=["security", "privacy", "compliance", "engineering", "architecture"],
        description="Review dimensions to analyze"
    )
    use_llm: bool = Field(True, description="Use LLM for analysis")
    openai_api_key: str | None = Field(None, description="OpenAI API key")
    anthropic_api_key: str | None = Field(None, description="Anthropic API key")
    max_parallel_reviews: int | None = Field(None, description="Max parallel workers")


class BulkAnalysisResponse(BaseModel):
    """Response from bulk analysis."""
    id: str
    status: str
    message: str
    total_prds: int


class BulkStatusResponse(BaseModel):
    """Status response for bulk analysis."""
    id: str
    status: str
    progress: float
    message: str
    total_prds: int
    successful_prds: int
    failed_prds: int
    current_prd: str | None = None


class BulkResultResponse(BaseModel):
    """Full result response for bulk analysis."""
    id: str
    total_prds: int
    successful_prds: int
    failed_prds: int
    success_rate: float
    total_findings: int
    findings_by_severity: dict[str, int]
    findings_by_dimension: dict[str, int]
    prd_results: list[dict[str, Any]]
    codebases_analyzed: list[str]
    default_codebase: str | None
    codebase_selection_counts: dict[str, int]
    parallel_workers_used: int
    total_duration_ms: float
    started_at: str | None
    completed_at: str | None


# Routes

@router.get("/config")
async def get_bulk_config() -> dict[str, Any]:
    """
    Get bulk PRD analysis configuration.
    
    Returns feature flags and limits for bulk analysis.
    """
    features = get_features()
    
    # Get codebase suggestions
    codebase_suggestions = []
    try:
        from context_graph.pm.bulk_prd_analyzer import get_codebase_tracker
        tracker = get_codebase_tracker()
        suggestions = tracker.get_all_selections()
        codebase_suggestions = [
            {
                "path": s.path,
                "name": s.display_name,
                "selection_count": s.selection_count,
                "is_default": s.path == tracker.current_default,
                "last_selected_at": s.last_selected_at.isoformat(),
            }
            for s in suggestions
        ]
    except Exception:
        pass
    
    return {
        "enabled": features.enable_bulk_prd_analysis,
        "max_files": features.bulk_prd_max_files,
        "max_parallel_reviews": features.bulk_prd_max_parallel_reviews,
        "smart_codebase_default": features.enable_bulk_prd_smart_codebase_default,
        "codebase_auto_default_threshold": features.bulk_prd_codebase_auto_default_threshold,
        "codebase_suggestions": codebase_suggestions,
        "default_codebase_path": None,  # Will be set by tracker
    }


@router.post("/analyze", response_model=BulkResultResponse)
async def analyze_bulk_prds(
    request: BulkAnalysisRequest,
    trace_id: str | None = None,
) -> BulkResultResponse:
    """
    Analyze multiple PRDs in bulk.
    
    This endpoint analyzes up to 20 PRD files in parallel across the specified
    review dimensions. Returns results synchronously (waits for completion).
    
    Pass ``trace_id`` query param to enable real-time trace streaming via
    ``GET /api/bulk/traces/{trace_id}``.
    """
    features = get_features()
    tc = get_collector(trace_id) if trace_id else None
    
    try:
        # Check feature flag
        if not features.enable_bulk_prd_analysis:
            raise HTTPException(
                status_code=403,
                detail="Bulk PRD analysis is not enabled. Set FEATURE_BULK_PRD_ANALYSIS=true"
            )
        
        # Validate PRD count
        max_files = min(features.bulk_prd_max_files, 20)
        if len(request.prds) > max_files:
            raise HTTPException(
                status_code=400,
                detail=f"Too many PRD files. Maximum allowed: {max_files}"
            )
        
        if len(request.prds) == 0:
            raise HTTPException(
                status_code=400,
                detail="No PRD files provided"
            )
        
        if tc:
            tc.emit("info", "bulk", f"Bulk scan started — {len(request.prds)} PRDs")
        
        # Parse dimensions
        dimension_map = {
            "security": ReviewDimension.SECURITY,
            "privacy": ReviewDimension.PRIVACY,
            "compliance": ReviewDimension.COMPLIANCE,
            "engineering": ReviewDimension.ENGINEERING,
            "architecture": ReviewDimension.ARCHITECTURE,
        }
        
        dimensions = []
        for dim_str in request.dimensions:
            if dim_str.lower() in dimension_map:
                dimensions.append(dimension_map[dim_str.lower()])
        
        if not dimensions:
            dimensions = [ReviewDimension.SECURITY]
        
        if tc:
            dim_names = [d.value for d in dimensions]
            tc.emit("info", "bulk", f"Dimensions: {', '.join(dim_names)}", dimensions=dim_names)
        
        # Get API keys
        openai_key = request.openai_api_key or os.getenv("OPENAI_API_KEY")
        anthropic_key = request.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        
        # Import and run bulk analyzer
        from context_graph.pm.bulk_prd_analyzer import (
            BulkPRDAnalyzer,
            BulkAnalysisRequest as InternalRequest,
            PRDFile,
        )
        
        # Create PRD file objects
        prd_files = []
        for prd_input in request.prds:
            prd_files.append(PRDFile(
                file_path=prd_input.file_path,
                file_name=prd_input.file_name,
                content=prd_input.content,
                codebase_path=prd_input.codebase_path,
                dimensions=dimensions,
            ))
        
        # Create internal request
        internal_request = InternalRequest(
            prds=prd_files,
            default_codebase_path=request.default_codebase_path,
            default_dimensions=dimensions,
            max_parallel_reviews=request.max_parallel_reviews,
            use_llm=request.use_llm and bool(openai_key or anthropic_key),
        )
        
        # Run analysis
        analyzer = BulkPRDAnalyzer(
            openai_api_key=openai_key,
            anthropic_api_key=anthropic_key,
            trace_collector=tc,
        )
        
        if tc:
            tc.emit("info", "bulk", f"Starting analysis of {len(prd_files)} PRDs...")
        result = await analyzer.analyze(internal_request)
        
        # Store results for individual PRD access using the storage backend
        from context_graph.storage.config import get_review_storage
        storage = get_review_storage()
        
        for idx, prd_result in enumerate(result.prd_results, 1):
            if prd_result.success and prd_result.review_result:
                await storage.save_review(prd_result.review_id, prd_result.review_result)
                await storage.update_review_status(
                    review_id=prd_result.review_id,
                    status="completed",
                    progress=1.0,
                    message=f"Review completed with {prd_result.total_findings} findings",
                )
                if tc:
                    tc.emit("info", "bulk",
                            f"PRD {idx}/{result.total_prds} '{prd_result.prd_file_name}' complete — "
                            f"{prd_result.total_findings} findings",
                            prd=prd_result.prd_file_name, findings=prd_result.total_findings)
            elif not prd_result.success and tc:
                tc.emit("error", "bulk",
                        f"PRD '{prd_result.prd_file_name}' failed: {prd_result.error_message}",
                        prd=prd_result.prd_file_name)
        
        if tc:
            tc.emit("info", "bulk",
                    f"Bulk scan complete: {result.successful_prds}/{result.total_prds} successful, "
                    f"{result.total_findings} total findings",
                    successful=result.successful_prds, failed=result.failed_prds,
                    total_findings=result.total_findings)
        
        # Convert to response
        return BulkResultResponse(
        id=str(result.id),
        total_prds=result.total_prds,
        successful_prds=result.successful_prds,
        failed_prds=result.failed_prds,
        success_rate=result.success_rate,
        total_findings=result.total_findings,
        findings_by_severity=result.findings_by_severity,
        findings_by_dimension=result.findings_by_dimension,
        prd_results=[
            {
                "prd_id": str(pr.prd_id),
                "prd_file_name": pr.prd_file_name,
                "codebase_path": pr.codebase_path,
                "success": pr.success,
                "error_message": pr.error_message,
                "total_findings": pr.total_findings,
                "findings_by_severity": pr.findings_by_severity,
                "findings_by_dimension": pr.findings_by_dimension,
                "review_id": pr.review_id,
                "duration_ms": pr.duration_ms,
            }
            for pr in result.prd_results
        ],
        codebases_analyzed=result.codebases_analyzed,
        default_codebase=result.default_codebase,
        codebase_selection_counts=result.codebase_selection_counts,
        parallel_workers_used=result.parallel_workers_used,
        total_duration_ms=result.total_duration_ms,
        started_at=result.started_at.isoformat() if result.started_at else None,
        completed_at=result.completed_at.isoformat() if result.completed_at else None,
    )
    finally:
        if tc:
            tc.close()


@router.post("/analyze/async", response_model=BulkAnalysisResponse)
async def analyze_bulk_prds_async(
    request: BulkAnalysisRequest,
    background_tasks: BackgroundTasks,
) -> BulkAnalysisResponse:
    """
    Start async bulk PRD analysis.
    
    Returns immediately with an ID to poll for status.
    """
    features = get_features()
    
    if not features.enable_bulk_prd_analysis:
        raise HTTPException(
            status_code=403,
            detail="Bulk PRD analysis is not enabled"
        )
    
    if len(request.prds) > 20:
        raise HTTPException(
            status_code=400,
            detail="Too many PRD files. Maximum: 20"
        )
    
    bulk_id = str(uuid4())
    
    # Initialize status
    bulk_status_store[bulk_id] = {
        "status": "pending",
        "progress": 0.0,
        "message": "Analysis queued",
        "total_prds": len(request.prds),
        "successful_prds": 0,
        "failed_prds": 0,
        "current_prd": None,
    }
    
    # Run in background
    background_tasks.add_task(
        _run_bulk_analysis_background,
        bulk_id,
        request,
    )
    
    return BulkAnalysisResponse(
        id=bulk_id,
        status="pending",
        message=f"Bulk analysis started for {len(request.prds)} PRDs",
        total_prds=len(request.prds),
    )


@router.get("/status/{bulk_id}", response_model=BulkStatusResponse)
async def get_bulk_status(bulk_id: str) -> BulkStatusResponse:
    """Get status of a bulk analysis job."""
    if bulk_id not in bulk_status_store:
        raise HTTPException(status_code=404, detail="Bulk analysis not found")
    
    status = bulk_status_store[bulk_id]
    
    return BulkStatusResponse(
        id=bulk_id,
        status=status["status"],
        progress=status["progress"],
        message=status["message"],
        total_prds=status["total_prds"],
        successful_prds=status["successful_prds"],
        failed_prds=status["failed_prds"],
        current_prd=status.get("current_prd"),
    )


@router.get("/traces/{bulk_id}")
async def stream_bulk_traces(bulk_id: str):
    """Stream trace events for a running bulk analysis via Server-Sent Events.

    Requires the ``enable_scan_tracing`` feature flag.
    """
    if not get_features().enable_scan_tracing:
        raise HTTPException(status_code=404, detail="Scan tracing is not enabled")

    import json as _json

    collector = get_collector(bulk_id)

    async def _event_stream():
        cursor = 0
        while True:
            new_events = collector.events_since(cursor)
            for evt in new_events:
                yield f"data: {_json.dumps(evt.to_dict())}\n\n"
                cursor += 1

            if collector.is_closed:
                yield "event: done\ndata: {}\n\n"
                return

            await collector.wait_for_new(timeout=2.0)

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/results/{bulk_id}", response_model=BulkResultResponse)
async def get_bulk_result(bulk_id: str) -> BulkResultResponse:
    """Get full results of a completed bulk analysis."""
    if bulk_id not in bulk_results_store:
        if bulk_id in bulk_status_store:
            status = bulk_status_store[bulk_id]
            if status["status"] != "completed":
                raise HTTPException(
                    status_code=400,
                    detail=f"Analysis not completed. Status: {status['status']}"
                )
        raise HTTPException(status_code=404, detail="Bulk analysis not found")
    
    return bulk_results_store[bulk_id]


@router.get("/codebase/suggestions")
async def get_codebase_suggestions() -> list[dict[str, Any]]:
    """Get codebase suggestions based on usage patterns."""
    from context_graph.pm.bulk_prd_analyzer import get_codebase_tracker
    
    tracker = get_codebase_tracker()
    suggestions = tracker.get_all_selections()
    
    return [
        {
            "path": s.path,
            "name": s.display_name,
            "selection_count": s.selection_count,
            "is_default": s.path == tracker.current_default,
            "last_selected_at": s.last_selected_at.isoformat(),
        }
        for s in suggestions
    ]


@router.post("/codebase/default")
async def set_default_codebase(request: dict[str, Any] = None) -> dict[str, Any]:
    """Set or clear the default codebase."""
    from context_graph.pm.bulk_prd_analyzer import get_codebase_tracker
    
    path = request.get("codebase_path") if request else None
    tracker = get_codebase_tracker()
    tracker.set_default(path)
    
    return {
        "set": True,
        "default_codebase_path": tracker.current_default,
        "message": "Default codebase updated" if path else "Default codebase cleared",
    }


# Background task

async def _run_bulk_analysis_background(
    bulk_id: str,
    request: BulkAnalysisRequest,
) -> None:
    """Run bulk analysis in background."""
    import logging
    tc = get_collector(bulk_id)
    
    try:
        bulk_status_store[bulk_id]["status"] = "running"
        bulk_status_store[bulk_id]["message"] = "Starting analysis..."
        tc.emit("info", "bulk", f"Bulk scan {bulk_id} started — {len(request.prds)} PRDs")
        
        # Parse dimensions
        dimension_map = {
            "security": ReviewDimension.SECURITY,
            "privacy": ReviewDimension.PRIVACY,
            "compliance": ReviewDimension.COMPLIANCE,
            "engineering": ReviewDimension.ENGINEERING,
            "architecture": ReviewDimension.ARCHITECTURE,
        }
        
        dimensions = [
            dimension_map[d.lower()]
            for d in request.dimensions
            if d.lower() in dimension_map
        ] or [ReviewDimension.SECURITY]
        
        dim_names = [d.value for d in dimensions]
        tc.emit("info", "bulk", f"Dimensions: {', '.join(dim_names)}", dimensions=dim_names)
        
        # Get API keys
        openai_key = request.openai_api_key or os.getenv("OPENAI_API_KEY")
        anthropic_key = request.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        
        from context_graph.pm.bulk_prd_analyzer import (
            BulkPRDAnalyzer,
            BulkAnalysisRequest as InternalRequest,
            PRDFile,
        )
        
        # Create PRD files
        prd_files = [
            PRDFile(
                file_path=prd.file_path,
                file_name=prd.file_name,
                content=prd.content,
                codebase_path=prd.codebase_path,
                dimensions=dimensions,
            )
            for prd in request.prds
        ]
        
        internal_request = InternalRequest(
            prds=prd_files,
            default_codebase_path=request.default_codebase_path,
            default_dimensions=dimensions,
            max_parallel_reviews=request.max_parallel_reviews,
            use_llm=request.use_llm and bool(openai_key or anthropic_key),
        )
        
        analyzer = BulkPRDAnalyzer(
            openai_api_key=openai_key,
            anthropic_api_key=anthropic_key,
        )
        
        tc.emit("info", "bulk", f"Starting bulk analysis of {len(prd_files)} PRDs...")
        result = await analyzer.analyze(internal_request)
        
        # Store results
        bulk_results_store[bulk_id] = BulkResultResponse(
            id=str(result.id),
            total_prds=result.total_prds,
            successful_prds=result.successful_prds,
            failed_prds=result.failed_prds,
            success_rate=result.success_rate,
            total_findings=result.total_findings,
            findings_by_severity=result.findings_by_severity,
            findings_by_dimension=result.findings_by_dimension,
            prd_results=[
                {
                    "prd_id": str(pr.prd_id),
                    "prd_file_name": pr.prd_file_name,
                    "codebase_path": pr.codebase_path,
                    "success": pr.success,
                    "error_message": pr.error_message,
                    "total_findings": pr.total_findings,
                    "findings_by_severity": pr.findings_by_severity,
                    "findings_by_dimension": pr.findings_by_dimension,
                    "review_id": pr.review_id,
                    "duration_ms": pr.duration_ms,
                }
                for pr in result.prd_results
            ],
            codebases_analyzed=result.codebases_analyzed,
            default_codebase=result.default_codebase,
            codebase_selection_counts=result.codebase_selection_counts,
            parallel_workers_used=result.parallel_workers_used,
            total_duration_ms=result.total_duration_ms,
            started_at=result.started_at.isoformat() if result.started_at else None,
            completed_at=result.completed_at.isoformat() if result.completed_at else None,
        )
        
        # Store individual reviews using the storage backend
        from context_graph.storage.config import get_review_storage
        storage = get_review_storage()
        
        for idx, prd_result in enumerate(result.prd_results, 1):
            if prd_result.success and prd_result.review_result:
                await storage.save_review(prd_result.review_id, prd_result.review_result)
                await storage.update_review_status(
                    review_id=prd_result.review_id,
                    status="completed",
                    progress=1.0,
                    message=f"Review completed",
                )
                tc.emit("info", "bulk",
                          f"PRD {idx}/{result.total_prds} '{prd_result.prd_file_name}' complete — "
                          f"{prd_result.total_findings} findings",
                          prd=prd_result.prd_file_name, findings=prd_result.total_findings)
            elif not prd_result.success:
                tc.emit("error", "bulk",
                          f"PRD '{prd_result.prd_file_name}' failed: {prd_result.error_message}",
                          prd=prd_result.prd_file_name)
        
        tc.emit("info", "bulk",
                  f"Bulk scan complete: {result.successful_prds}/{result.total_prds} successful, "
                  f"{result.total_findings} total findings",
                  successful=result.successful_prds, failed=result.failed_prds,
                  total_findings=result.total_findings,
                  duration_ms=result.total_duration_ms)
        
        bulk_status_store[bulk_id] = {
            "status": "completed",
            "progress": 1.0,
            "message": f"Completed: {result.successful_prds}/{result.total_prds} successful",
            "total_prds": result.total_prds,
            "successful_prds": result.successful_prds,
            "failed_prds": result.failed_prds,
        }
        
    except Exception as e:
        logging.error(f"Bulk analysis failed: {e}")
        tc.emit("error", "bulk", f"Bulk analysis failed: {str(e)}")
        bulk_status_store[bulk_id] = {
            "status": "failed",
            "progress": 0.0,
            "message": f"Analysis failed: {str(e)}",
            "total_prds": len(request.prds),
            "successful_prds": 0,
            "failed_prds": len(request.prds),
        }
    finally:
        tc.close()
