"""
FastAPI Application - Web API for Context Graph Security Reviews.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
# Look for .env in the project root (4 levels up from this file)
_project_root = Path(__file__).parent.parent.parent.parent
_env_file = _project_root / ".env"
if _env_file.exists():
    load_dotenv(_env_file)
else:
    # Fallback: try current working directory
    load_dotenv()
from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from context_graph.api.routes import router as api_router
from context_graph.api.collaboration_routes import router as collaboration_router
from context_graph.api.pm_routes import router as pm_router
from context_graph.api.bulk_prd_routes import router as bulk_prd_router
from context_graph.api.prd_generator_routes import router as prd_generator_router
from context_graph.api.chat_routes import router as chat_router
from context_graph.api.review_request_routes import router as review_request_router
from context_graph.api.live_analysis_routes import router as live_analysis_router
from context_graph.api.analytics_routes import router as analytics_router
from context_graph.api.version_history_routes import router as version_history_router
from context_graph.config.features import get_features


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    print("Context Graph Security Review API starting...")
    features = get_features()
    enabled = features.get_enabled_features()
    if enabled:
        print(f"Enabled features: {', '.join(enabled)}")
    else:
        print("All optional features: disabled (set FEATURE_* env vars to enable)")
    
    # Print PM features status
    pm_features = []
    if features.enable_prd_changes:
        pm_features.append("PRD changes")
    if features.enable_prd_quality_scoring:
        pm_features.append("PRD quality scoring")
    if features.enable_effort_estimation:
        pm_features.append("Effort estimation")
    if features.enable_expert_assist:
        pm_features.append("Expert assist")
    if pm_features:
        print(f"Enabled PM features: {', '.join(pm_features)}")
    yield
    # Shutdown
    print("Context Graph API shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Context Graph",
        description="Security Review Platform - PRD to Code Impact Analysis",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes
    app.include_router(api_router, prefix="/api")
    
    # Include collaboration routes (feature-flag protected)
    app.include_router(collaboration_router, prefix="/api")
    
    # Include PM-focused routes (feature-flag protected)
    app.include_router(pm_router, prefix="/api")
    
    # Include bulk PRD analysis routes
    app.include_router(bulk_prd_router, prefix="/api")
    
    # Include PRD generator routes
    app.include_router(prd_generator_router, prefix="/api")
    
    # Include P0 feature routes (feature-flag protected)
    app.include_router(chat_router, prefix="/api")
    app.include_router(review_request_router, prefix="/api")
    
    # Include P1 feature routes (feature-flag protected)
    app.include_router(live_analysis_router, prefix="/api")
    app.include_router(analytics_router, prefix="/api")
    app.include_router(version_history_router, prefix="/api")
    
    # Health check
    @app.get("/health")
    @app.get("/api/health")
    async def health_check() -> dict[str, str]:
        return {"status": "healthy", "service": "context-graph"}
    
    # Feature flags endpoint
    @app.get("/api/features")
    async def get_feature_flags() -> dict[str, Any]:
        """Get current feature flags configuration."""
        features = get_features()
        return features.to_dict()
    
    # Serve static frontend (if built)
    static_dir = Path(__file__).parent.parent.parent.parent / "frontend" / "dist"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
    else:
        @app.get("/")
        async def root() -> dict[str, Any]:
            return {
                "message": "Context Graph API",
                "docs": "/api/docs",
                "frontend": "Run 'npm run dev' in frontend/ directory",
            }
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "context_graph.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )

