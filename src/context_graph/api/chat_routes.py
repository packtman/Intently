"""
Chat API Routes — Product-Aware Chat for PMs.

Provides a conversational interface grounded in review data,
context graph entities, collaboration history, and (optionally)
the actual codebase files.

Feature flags:
  FEATURE_PRODUCT_CHAT=true       — base chat functionality
  FEATURE_CODEBASE_CHAT=true      — codebase file reading in chat
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from context_graph.config.features import requires_feature
from context_graph.storage.config import get_review_storage, get_collaboration_storage
from context_graph.chat.product_chat import ProductChat


router = APIRouter(tags=["chat"])

# Singleton chat engine (lazy init)
_chat_engine: ProductChat | None = None


def _get_chat_engine() -> ProductChat:
    global _chat_engine
    if _chat_engine is None:
        _chat_engine = ProductChat(
            review_storage=get_review_storage(),
            collaboration_storage=get_collaboration_storage(),
        )
    return _chat_engine


# ==================== Request / Response Models ====================


class ChatRequest(BaseModel):
    """Chat request from the frontend."""

    question: str = Field(..., min_length=1, description="The question to ask")
    review_id: str | None = Field(
        None, description="Optional: scope to a specific review for grounded answers"
    )
    conversation_id: str | None = Field(
        None, description="Optional: continue an existing conversation"
    )
    finding_id: str | None = Field(
        None, description="Optional: focus on a specific finding (drill-down chat)"
    )
    codebase_path: str | None = Field(
        None,
        description="Optional: codebase path for standalone chat (ignored when review_id is set)",
    )


class CitationResponse(BaseModel):
    """A citation linking the answer to existing data."""

    type: str
    id: str
    text: str
    url: str = ""


class ChatResponseModel(BaseModel):
    """Chat response with answer, citations, and follow-ups."""

    answer: str
    citations: list[CitationResponse] = []
    suggested_followups: list[str] = []
    conversation_id: str = ""


class CodebaseIndexRequest(BaseModel):
    """Request to index a codebase for standalone chat."""

    codebase_path: str = Field(..., description="Path to the codebase directory")


class CodebaseIndexResponse(BaseModel):
    """Summary of the indexed codebase."""

    codebase_path: str
    total_indexed_symbols: int = 0
    endpoints: list[dict[str, Any]] = []
    data_models: list[dict[str, Any]] = []
    key_classes: list[dict[str, Any]] = []
    key_functions: list[dict[str, Any]] = []


# ==================== Routes ====================


@router.post("/chat", response_model=ChatResponseModel)
@requires_feature("product_chat")
async def chat(request: ChatRequest) -> ChatResponseModel:
    """Answer a product question using review data + context graph + LLM.

    Questions can be scoped to a specific review (provide review_id) or
    asked globally across all reviews. Supports multi-turn conversations
    via conversation_id.

    When codebase_chat is enabled and a review is scoped, the chat reads
    relevant source files from the codebase to ground its answers in
    actual code.

    Examples:
      - "What are the top security findings?"
      - "How does authentication work in this codebase?"
      - "Explain this finding in simpler terms" (with finding_id)
      - "What endpoints handle payment data?"
    """
    engine = _get_chat_engine()

    result = await engine.answer(
        question=request.question,
        review_id=request.review_id,
        conversation_id=request.conversation_id,
        finding_id=request.finding_id,
        codebase_path=request.codebase_path,
    )

    return ChatResponseModel(
        answer=result.answer,
        citations=[
            CitationResponse(type=c.type, id=c.id, text=c.text, url=c.url)
            for c in result.citations
        ],
        suggested_followups=result.suggested_followups,
        conversation_id=result.conversation_id,
    )


@router.post("/chat/index-codebase", response_model=CodebaseIndexResponse)
@requires_feature("codebase_chat")
async def index_codebase(request: CodebaseIndexRequest) -> CodebaseIndexResponse:
    """Index a codebase for standalone chat (no review required).

    Runs a fast AST analysis on the codebase and returns the structural
    summary. The returned structure is also cached for subsequent chat
    questions that reference this codebase_path.
    """
    from pathlib import Path

    cb_path = Path(request.codebase_path)
    if not cb_path.exists() or not cb_path.is_dir():
        raise HTTPException(status_code=400, detail=f"Codebase path not found: {request.codebase_path}")

    from context_graph.code_graph.hybrid_analyzer import HybridAnalyzer
    from context_graph.chat.codebase_reader import CodebaseReader

    analyzer = HybridAnalyzer(cb_path)
    result = analyzer.analyze_fast()

    # Build a lightweight State-like object from AST results for the reader
    from context_graph.core.models import State, Entity, EntityType

    state = State(codebase_path=str(cb_path))
    for rel_path, ast_result in result.ast_results.items():
        file_path = cb_path / rel_path
        for cls in ast_result.classes:
            state.entities.append(Entity(
                name=cls["name"],
                entity_type=EntityType.DATA if "model" in cls["name"].lower() else EntityType.CLASS,
                source=str(file_path),
            ))
            if any(base in ["BaseModel", "Model", "Entity"] for base in cls.get("bases", [])):
                state.data_models.append({"name": cls["name"], "file": str(file_path), "line": cls.get("line", 0)})
        for func in ast_result.functions:
            state.entities.append(Entity(
                name=func["name"],
                entity_type=EntityType.FUNCTION,
                source=str(file_path),
            ))
            decorators = func.get("decorators", [])
            if any(d in ["get", "post", "put", "delete", "patch", "route", "Get", "Post", "Put", "Delete"] for d in decorators):
                state.api_endpoints.append({
                    "path": func["name"],
                    "method": next((d.upper() for d in decorators if d.lower() in ["get", "post", "put", "delete", "patch"]), "GET"),
                    "file": str(file_path),
                    "line": func.get("line", 0),
                })

    reader = CodebaseReader(cb_path, state)
    summary = reader.get_structure_summary()

    return CodebaseIndexResponse(**summary)
