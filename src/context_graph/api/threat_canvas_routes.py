"""
Interactive Threat Model Canvas API Routes.

Provides CRUD operations for visual threat model canvases,
AI-powered threat suggestions based on canvas topology,
auto-population from existing reviews, and Markdown/JSON export.

Feature flag: FEATURE_THREAT_CANVAS
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from context_graph.config.features import requires_feature
from context_graph.storage.config import get_collaboration_storage, get_review_storage
from context_graph.security.canvas_threat_analyzer import (
    CanvasThreatAnalyzer,
    generate_export_markdown,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["threat-canvas"])


# ==================== Request / Response Models ====================


class CanvasNodeModel(BaseModel):
    id: str
    type: str  # actor, process, data_store, external
    label: str
    x: float = 0
    y: float = 0
    width: float = 120
    height: float = 80
    properties: Dict[str, Any] = Field(default_factory=dict)


class CanvasEdgeModel(BaseModel):
    id: str
    source_id: str
    target_id: str
    label: str = ""
    data_classification: str = "unclassified"
    protocol: str = ""
    bidirectional: bool = False


class TrustBoundaryModel(BaseModel):
    id: str
    label: str
    x: float = 0
    y: float = 0
    width: float = 300
    height: float = 300
    trust_level: int = 0
    color: str = "#ef4444"


class ThreatOverlayModel(BaseModel):
    id: str
    threat_id: str
    category: str
    title: str
    description: str
    severity: str
    affected_node_ids: List[str] = Field(default_factory=list)
    affected_edge_ids: List[str] = Field(default_factory=list)
    mitigation: str = ""
    confidence: float = 0.75
    source: str = "ai"


class CreateCanvasRequest(BaseModel):
    title: str = "Untitled Threat Model"
    review_id: Optional[str] = None
    nodes: List[CanvasNodeModel] = Field(default_factory=list)
    edges: List[CanvasEdgeModel] = Field(default_factory=list)
    boundaries: List[TrustBoundaryModel] = Field(default_factory=list)
    threats: List[ThreatOverlayModel] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UpdateCanvasRequest(BaseModel):
    title: Optional[str] = None
    nodes: Optional[List[CanvasNodeModel]] = None
    edges: Optional[List[CanvasEdgeModel]] = None
    boundaries: Optional[List[TrustBoundaryModel]] = None
    threats: Optional[List[ThreatOverlayModel]] = None
    metadata: Optional[Dict[str, Any]] = None


class PopulateRequest(BaseModel):
    review_id: str


# ==================== Endpoints ====================


@router.post("/threat-canvas")
@requires_feature("threat_canvas")
async def create_canvas(request: CreateCanvasRequest) -> Dict[str, Any]:
    """Create a new threat model canvas."""
    storage = get_collaboration_storage()
    canvas_id = str(uuid4())[:12]

    canvas_state = {
        "nodes": [n.model_dump() for n in request.nodes],
        "edges": [e.model_dump() for e in request.edges],
        "boundaries": [b.model_dump() for b in request.boundaries],
        "threats": [t.model_dump() for t in request.threats],
        "metadata": request.metadata,
    }

    result = await storage.save_threat_canvas(
        canvas_id=canvas_id,
        title=request.title,
        canvas_state=canvas_state,
        review_id=request.review_id,
    )
    return result


@router.get("/threat-canvas")
@requires_feature("threat_canvas")
async def list_canvases() -> List[Dict[str, Any]]:
    """List all threat model canvases."""
    storage = get_collaboration_storage()
    return await storage.list_threat_canvases()


@router.get("/threat-canvas/{canvas_id}")
@requires_feature("threat_canvas")
async def get_canvas(canvas_id: str) -> Dict[str, Any]:
    """Get a specific threat model canvas."""
    storage = get_collaboration_storage()
    canvas = await storage.get_threat_canvas(canvas_id)
    if not canvas:
        raise HTTPException(status_code=404, detail="Canvas not found")
    return canvas


@router.put("/threat-canvas/{canvas_id}")
@requires_feature("threat_canvas")
async def update_canvas(canvas_id: str, request: UpdateCanvasRequest) -> Dict[str, Any]:
    """Update an existing threat model canvas (auto-save)."""
    storage = get_collaboration_storage()
    existing = await storage.get_threat_canvas(canvas_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Canvas not found")

    canvas_state = {
        "nodes": [n.model_dump() for n in request.nodes] if request.nodes is not None else existing.get("nodes", []),
        "edges": [e.model_dump() for e in request.edges] if request.edges is not None else existing.get("edges", []),
        "boundaries": [b.model_dump() for b in request.boundaries] if request.boundaries is not None else existing.get("boundaries", []),
        "threats": [t.model_dump() for t in request.threats] if request.threats is not None else existing.get("threats", []),
        "metadata": request.metadata if request.metadata is not None else existing.get("metadata", {}),
    }

    result = await storage.save_threat_canvas(
        canvas_id=canvas_id,
        title=request.title or existing.get("title", "Untitled Threat Model"),
        canvas_state=canvas_state,
        review_id=existing.get("review_id"),
    )
    return result


@router.delete("/threat-canvas/{canvas_id}")
@requires_feature("threat_canvas")
async def delete_canvas(canvas_id: str) -> Dict[str, str]:
    """Delete a threat model canvas."""
    storage = get_collaboration_storage()
    deleted = await storage.delete_threat_canvas(canvas_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Canvas not found")
    return {"status": "deleted", "canvas_id": canvas_id}


@router.post("/threat-canvas/{canvas_id}/suggest")
@requires_feature("threat_canvas")
async def suggest_threats(canvas_id: str) -> Dict[str, Any]:
    """Run AI threat analysis on the canvas topology and return suggestions."""
    storage = get_collaboration_storage()
    canvas = await storage.get_threat_canvas(canvas_id)
    if not canvas:
        raise HTTPException(status_code=404, detail="Canvas not found")

    nodes = canvas.get("nodes", [])
    edges = canvas.get("edges", [])
    boundaries = canvas.get("boundaries", [])

    if not nodes:
        return {"threats": [], "message": "Canvas is empty — add elements before requesting analysis."}

    analyzer = CanvasThreatAnalyzer()
    threats = analyzer.analyze_sync(nodes, edges, boundaries)

    # Persist the threats back to the canvas
    canvas_state = {
        "nodes": nodes,
        "edges": edges,
        "boundaries": boundaries,
        "threats": threats,
        "metadata": canvas.get("metadata", {}),
    }
    await storage.save_threat_canvas(
        canvas_id=canvas_id,
        title=canvas.get("title", "Untitled"),
        canvas_state=canvas_state,
        review_id=canvas.get("review_id"),
    )

    return {
        "threats": threats,
        "count": len(threats),
        "by_category": _count_by(threats, "category"),
        "by_severity": _count_by(threats, "severity"),
    }


@router.post("/threat-canvas/{canvas_id}/populate")
@requires_feature("threat_canvas")
async def populate_from_review(canvas_id: str, request: PopulateRequest) -> Dict[str, Any]:
    """Auto-populate canvas elements from an existing review's analysis."""
    storage = get_collaboration_storage()
    canvas = await storage.get_threat_canvas(canvas_id)
    if not canvas:
        raise HTTPException(status_code=404, detail="Canvas not found")

    review_storage = get_review_storage()
    review = await review_storage.get_review(request.review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    nodes: List[Dict[str, Any]] = list(canvas.get("nodes", []))
    edges: List[Dict[str, Any]] = list(canvas.get("edges", []))
    boundaries: List[Dict[str, Any]] = list(canvas.get("boundaries", []))

    x_offset = 100
    y_offset = 100
    spacing = 160
    col = 0

    # Add endpoints as process nodes
    for ep in review.state.api_endpoints[:20]:
        node_id = f"proc-{str(uuid4())[:8]}"
        path = ep.get("path", ep.get("name", "endpoint"))
        nodes.append({
            "id": node_id,
            "type": "process",
            "label": path[:30],
            "x": x_offset + (col % 4) * spacing,
            "y": y_offset + (col // 4) * spacing,
            "width": 120,
            "height": 80,
            "properties": {
                "requires_auth": bool(ep.get("auth") or ep.get("requires_auth")),
                "handles_pii": bool(ep.get("pii") or ep.get("handles_pii")),
            },
        })
        col += 1

    # Add entities as data store nodes
    sensitive_entities = [e for e in review.state.entities if e.is_sensitive][:10]
    for entity in sensitive_entities:
        node_id = f"ds-{str(uuid4())[:8]}"
        nodes.append({
            "id": node_id,
            "type": "data_store",
            "label": entity.name[:30],
            "x": x_offset + (col % 4) * spacing,
            "y": y_offset + (col // 4) * spacing,
            "width": 120,
            "height": 80,
            "properties": {
                "handles_pii": entity.is_sensitive,
            },
        })
        col += 1

    # Add a default actor
    actor_id = f"actor-{str(uuid4())[:8]}"
    nodes.append({
        "id": actor_id,
        "type": "actor",
        "label": "End User",
        "x": 50,
        "y": 50,
        "width": 120,
        "height": 80,
        "properties": {},
    })

    # Save updated canvas
    canvas_state = {
        "nodes": nodes,
        "edges": edges,
        "boundaries": boundaries,
        "threats": canvas.get("threats", []),
        "metadata": {**canvas.get("metadata", {}), "populated_from": request.review_id},
    }
    result = await storage.save_threat_canvas(
        canvas_id=canvas_id,
        title=canvas.get("title", "Untitled"),
        canvas_state=canvas_state,
        review_id=request.review_id,
    )

    return {
        **result,
        "populated": True,
        "nodes_added": col + 1,
    }


@router.get("/threat-canvas/{canvas_id}/export")
@requires_feature("threat_canvas")
async def export_canvas(
    canvas_id: str,
    format: str = Query("markdown", description="Export format: markdown or json"),
) -> Any:
    """Export the threat model canvas as a document."""
    storage = get_collaboration_storage()
    canvas = await storage.get_threat_canvas(canvas_id)
    if not canvas:
        raise HTTPException(status_code=404, detail="Canvas not found")

    if format == "json":
        return canvas

    markdown = generate_export_markdown(canvas)
    return PlainTextResponse(content=markdown, media_type="text/markdown")


# ==================== Helpers ====================


def _count_by(items: List[Dict[str, Any]], key: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for item in items:
        val = item.get(key, "unknown")
        counts[val] = counts.get(val, 0) + 1
    return counts
