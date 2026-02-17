"""
Chat API Routes — Product-Aware Chat for PMs.

Provides a conversational interface grounded in review data,
context graph entities, and collaboration history.

Feature flag: FEATURE_PRODUCT_CHAT=true
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


# ==================== Routes ====================


@router.post("/chat", response_model=ChatResponseModel)
@requires_feature("product_chat")
async def chat(request: ChatRequest) -> ChatResponseModel:
    """Answer a product question using review data + context graph + LLM.

    Questions can be scoped to a specific review (provide review_id) or
    asked globally across all reviews. Supports multi-turn conversations
    via conversation_id.

    Examples:
      - "What are the top security findings?"
      - "What services access PII in our system?"
      - "How can I improve the PRD quality score?"
      - "What did the security team flag in the last review?"
    """
    engine = _get_chat_engine()

    result = await engine.answer(
        question=request.question,
        review_id=request.review_id,
        conversation_id=request.conversation_id,
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
