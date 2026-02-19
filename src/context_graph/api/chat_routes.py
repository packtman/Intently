"""
Chat API Routes — Product-Aware Chat for PMs.

Provides a conversational interface grounded in review data,
context graph entities, and collaboration history. Includes
codebase file reading, optional embedding-based semantic search,
and SSE streaming responses.

Feature flags:
  FEATURE_PRODUCT_CHAT=true       — base chat functionality
  FEATURE_CODEBASE_CHAT=true      — codebase file reading in chat
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from context_graph.config.features import requires_feature, get_features
from context_graph.storage.config import get_review_storage, get_collaboration_storage
from context_graph.chat.product_chat import ProductChat, set_cached_vector_index

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

# Singleton chat engine (lazy init)
_chat_engine: ProductChat | None = None

# Cached vector indexes by codebase path
_vector_indexes: dict[str, Any] = {}


def _get_chat_engine() -> ProductChat:
    global _chat_engine
    if _chat_engine is None:
        _chat_engine = ProductChat(
            review_storage=get_review_storage(),
            collaboration_storage=get_collaboration_storage(),
        )
    return _chat_engine


def _get_vector_index(codebase_path: str) -> Any | None:
    return _vector_indexes.get(codebase_path)


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


class IndexCodebaseRequest(BaseModel):
    """Request to index a codebase for chat."""

    codebase_path: str = Field(..., min_length=1, description="Absolute path to codebase root")


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


class CodebaseIndexResponse(BaseModel):
    """Response from codebase indexing."""

    files_analyzed: int = 0
    classes: int = 0
    functions: int = 0
    embedding_status: str = "unavailable"
    embedding_chunks: int = 0


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

    vi = None
    for path, index in _vector_indexes.items():
        if index is not None and getattr(index, "is_ready", False):
            vi = index
            break

    result = await engine.answer(
        question=request.question,
        review_id=request.review_id,
        conversation_id=request.conversation_id,
        finding_id=request.finding_id,
        codebase_path=request.codebase_path,
        vector_index=vi,
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


@router.post("/chat/stream")
@requires_feature("product_chat")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """Stream an answer as Server-Sent Events."""
    engine = _get_chat_engine()

    vi = None
    for path, index in _vector_indexes.items():
        if index is not None and getattr(index, "is_ready", False):
            vi = index
            break

    async def _event_stream():
        async for event in engine.answer_stream(
            question=request.question,
            review_id=request.review_id,
            conversation_id=request.conversation_id,
            finding_id=request.finding_id,
            codebase_path=request.codebase_path,
            vector_index=vi,
        ):
            yield event

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat/index-codebase", response_model=CodebaseIndexResponse)
@requires_feature("codebase_chat")
async def index_codebase(request: IndexCodebaseRequest) -> CodebaseIndexResponse:
    """Index a codebase for chat context.

    Runs AST analysis for keyword search and optionally builds
    embedding-based vector index for semantic search.
    """
    cb_path = Path(request.codebase_path).resolve()
    if not cb_path.is_dir():
        raise HTTPException(status_code=400, detail=f"Not a valid directory: {cb_path}")

    from context_graph.code_graph.hybrid_analyzer import HybridAnalyzer
    from context_graph.chat.codebase_reader import CodebaseIndex

    analyzer = HybridAnalyzer(cb_path)
    hybrid_result = analyzer.analyze_fast()

    index = CodebaseIndex.from_ast_results(hybrid_result.ast_results)

    engine = _get_chat_engine()
    if not hasattr(engine, "_codebase_states"):
        engine._codebase_states = {}
    engine._codebase_states[str(cb_path)] = index

    embedding_status = "unavailable"
    embedding_chunks = 0

    if get_features().enable_semantic_search:
        try:
            from context_graph.chat.vector_index import VectorIndex

            vector_index = VectorIndex(cb_path)
            stats = await vector_index.build_or_update()
            _vector_indexes[str(cb_path)] = vector_index
            set_cached_vector_index(str(cb_path), vector_index)
            embedding_status = "ready"
            embedding_chunks = stats.get("new_chunks", 0)
        except Exception as exc:
            logger.error("Failed to build vector index: %s", exc)
            embedding_status = "error"

    return CodebaseIndexResponse(
        files_analyzed=index.file_count,
        classes=index.class_count,
        functions=index.function_count,
        embedding_status=embedding_status,
        embedding_chunks=embedding_chunks,
    )
