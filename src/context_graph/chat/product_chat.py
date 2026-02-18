"""
Product-Aware Chat — conversational AI grounded in product context.

Answers PM questions using the context graph, review history,
collaboration data, and learned patterns. Provides citations
back to specific reviews, findings, and entities.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from context_graph.storage.base import ReviewStorage, CollaborationStorage

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    """A reference to an existing piece of data used to answer the question."""

    type: str  # "review", "finding", "entity", "pattern", "feedback"
    id: str
    text: str  # Human-readable snippet
    url: str = ""  # Deep-link in the frontend (e.g. /reviews/{id})


@dataclass
class ChatMessage:
    """A single message in a conversation."""

    role: str  # "user" or "assistant"
    content: str
    citations: list[Citation] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ChatResponse:
    """Response from the product chat engine."""

    answer: str
    citations: list[Citation] = field(default_factory=list)
    suggested_followups: list[str] = field(default_factory=list)
    conversation_id: str = ""


class ProductChat:
    """Conversational AI grounded in Intently product context.

    Queries existing storage backends (reviews, collaboration, patterns)
    to build a context-rich prompt, then uses an LLM provider to
    generate a grounded answer with citations.
    """

    def __init__(
        self,
        review_storage: ReviewStorage,
        collaboration_storage: CollaborationStorage,
        openai_api_key: str | None = None,
        anthropic_api_key: str | None = None,
    ) -> None:
        self.review_storage = review_storage
        self.collab_storage = collaboration_storage
        self._openai_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self._anthropic_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")

        # Conversation memory keyed by conversation_id
        self._conversations: dict[str, list[ChatMessage]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def answer(
        self,
        question: str,
        review_id: str | None = None,
        conversation_id: str | None = None,
    ) -> ChatResponse:
        """Answer a product question using existing data + LLM."""

        conv_id = conversation_id or str(uuid4())

        # 1. Gather grounded context from storage
        context, citations = await self._gather_context(question, review_id)

        # 2. Build conversation messages
        history = self._conversations.get(conv_id, [])
        history.append(ChatMessage(role="user", content=question))

        # 3. Build the LLM prompt
        system_prompt = self._build_system_prompt(context)
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history[-10:]:  # Keep last 10 turns
            messages.append({"role": msg.role, "content": msg.content})

        # 4. Call LLM
        answer_text = await self._call_llm(messages)

        # 5. Generate follow-up suggestions
        followups = self._suggest_followups(question, context)

        # 6. Record assistant message
        assistant_msg = ChatMessage(
            role="assistant",
            content=answer_text,
            citations=citations,
        )
        history.append(assistant_msg)
        self._conversations[conv_id] = history

        return ChatResponse(
            answer=answer_text,
            citations=citations,
            suggested_followups=followups,
            conversation_id=conv_id,
        )

    # ------------------------------------------------------------------
    # Context gathering — queries existing storage
    # ------------------------------------------------------------------

    async def _gather_context(
        self,
        question: str,
        review_id: str | None,
    ) -> tuple[dict[str, Any], list[Citation]]:
        """Query existing storage for context relevant to the question."""

        context: dict[str, Any] = {}
        citations: list[Citation] = []
        q_lower = question.lower()

        # Always include recent reviews summary
        try:
            reviews = await self.review_storage.list_reviews()
            context["total_reviews"] = len(reviews)
            context["recent_reviews"] = reviews[:5]
            for r in reviews[:5]:
                citations.append(Citation(
                    type="review",
                    id=r.get("review_id", ""),
                    text=r.get("title", r.get("review_id", "")),
                    url=f"/reviews/{r.get('review_id', '')}",
                ))
        except Exception as exc:
            logger.warning("Failed to load reviews: %s", exc)

        # If scoped to a specific review, load its full data
        if review_id:
            try:
                review = await self.review_storage.get_review(review_id)
                if review:
                    context["current_review"] = {
                        "id": review_id,
                        "title": review.intent.title,
                        "summary": review.executive_summary,
                        "risk_rating": review.risk_rating,
                        "dimensions": [d.value for d in review.dimensions_analyzed],
                        "total_findings": len(review.all_findings),
                        "security_findings": len(review.security_findings),
                        "privacy_findings": len(review.privacy_findings),
                        "compliance_findings": len(review.compliance_findings),
                        "engineering_findings": len(review.engineering_findings),
                        "architecture_findings": len(review.architecture_findings),
                    }
                    if review.prd_quality_score:
                        context["current_review"]["quality_score"] = review.prd_quality_score.score
                        context["current_review"]["quality_grade"] = review.prd_quality_score.grade

                    # Include top findings for context
                    top_findings = []
                    for f in review.all_findings[:10]:
                        top_findings.append({
                            "title": f.title,
                            "severity": f.severity.value,
                            "dimension": f.dimension.value,
                            "recommendation": f.recommendation[:200] if f.recommendation else "",
                        })
                        citations.append(Citation(
                            type="finding",
                            id=str(f.id),
                            text=f"{f.severity.value.upper()}: {f.title}",
                            url=f"/reviews/{review_id}#finding-{f.id}",
                        ))
                    context["top_findings"] = top_findings

                    # Include entities from state
                    entities = []
                    for e in review.state.entities[:20]:
                        entities.append({
                            "name": e.name,
                            "type": e.entity_type.value,
                            "sensitive": e.is_sensitive,
                            "source": e.source,
                        })
                    context["entities"] = entities

            except Exception as exc:
                logger.warning("Failed to load review %s: %s", review_id, exc)

        # Load collaboration stats if question is about feedback/patterns
        if any(kw in q_lower for kw in [
            "feedback", "pattern", "learned", "expert", "false positive",
            "rejected", "validated", "team",
        ]):
            try:
                stats = await self.collab_storage.get_feedback_stats()
                context["feedback_stats"] = stats
            except Exception as exc:
                logger.debug("Failed to load feedback stats: %s", exc)

        return context, citations

    # ------------------------------------------------------------------
    # LLM interaction
    # ------------------------------------------------------------------

    def _build_system_prompt(self, context: dict[str, Any]) -> str:
        """Build a grounded system prompt from gathered context."""

        context_block = json.dumps(context, indent=2, default=str)

        return f"""You are an AI assistant for Intently, a product analysis platform that helps PMs bridge PRDs to code. You answer questions about the product, codebase, reviews, and organizational patterns.

GROUNDING RULES:
- Base your answers ONLY on the context data provided below.
- When you reference a review, finding, or entity, mention it by name/ID so the frontend can link to it.
- If you don't have enough context to answer confidently, say so and suggest what the user could do (e.g., "Run a review on this PRD" or "Check the security findings for review X").
- Be concise but thorough. Use bullet points for lists.
- Do NOT hallucinate data. If the context doesn't contain information about something, say so.

PRODUCT CONTEXT:
```json
{context_block}
```

Answer the user's question using the above context. Cite specific reviews, findings, and entities when relevant."""

    async def _call_llm(self, messages: list[dict[str, str]]) -> str:
        """Call the LLM provider. Prefers OpenAI, falls back to Anthropic."""

        if self._openai_key:
            return await self._call_openai(messages)
        elif self._anthropic_key:
            return await self._call_anthropic(messages)
        else:
            return self._fallback_response(messages)

    async def _call_openai(self, messages: list[dict[str, str]]) -> str:
        """Call OpenAI chat completion."""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self._openai_key)
            response = await client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=messages,
                temperature=0.3,
                max_tokens=2048,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.error("OpenAI chat failed: %s", exc)
            return f"I encountered an error calling the LLM: {exc}"

    async def _call_anthropic(self, messages: list[dict[str, str]]) -> str:
        """Call Anthropic chat completion."""
        try:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=self._anthropic_key)

            # Anthropic uses system param separately
            system = ""
            chat_messages = []
            for m in messages:
                if m["role"] == "system":
                    system = m["content"]
                else:
                    chat_messages.append(m)

            response = await client.messages.create(
                model="claude-haiku-4-5-20251001",
                system=system,
                messages=chat_messages,
                max_tokens=2048,
                temperature=0.3,
            )
            return response.content[0].text if response.content else ""
        except Exception as exc:
            logger.error("Anthropic chat failed: %s", exc)
            return f"I encountered an error calling the LLM: {exc}"

    def _fallback_response(self, messages: list[dict[str, str]]) -> str:
        """Provide a basic response when no LLM keys are configured."""
        return (
            "I can't provide an AI-generated answer because no LLM API keys are configured. "
            "Set OPENAI_API_KEY or ANTHROPIC_API_KEY to enable the chat feature.\n\n"
            "In the meantime, you can explore your review data through the dashboard."
        )

    # ------------------------------------------------------------------
    # Follow-up suggestions
    # ------------------------------------------------------------------

    def _suggest_followups(
        self, question: str, context: dict[str, Any]
    ) -> list[str]:
        """Generate contextual follow-up question suggestions."""

        suggestions: list[str] = []
        q_lower = question.lower()

        if context.get("current_review"):
            review = context["current_review"]
            if review.get("security_findings", 0) > 0:
                suggestions.append("What are the most critical security findings?")
            if review.get("privacy_findings", 0) > 0:
                suggestions.append("Are there any privacy concerns with PII handling?")
            if review.get("quality_score"):
                suggestions.append("How can I improve the PRD quality score?")
            suggestions.append("What entities are affected by this change?")
        else:
            suggestions.append("Show me a summary of the latest review.")
            suggestions.append("What are the most common finding categories?")

        if "security" not in q_lower:
            suggestions.append("What security patterns should I be aware of?")

        return suggestions[:4]
