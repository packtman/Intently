"""
FastAPI Application - Web API for Context Graph Security Reviews.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from context_graph.api.routes import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    print("🚀 Context Graph Security Review API starting...")
    yield
    # Shutdown
    print("👋 Context Graph API shutting down...")


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
    
    # Health check
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "healthy", "service": "context-graph"}
    
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

