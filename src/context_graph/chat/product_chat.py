"""
Product-Aware Chat — conversational AI grounded in product context.

Answers PM questions using the context graph, review history,
collaboration data, learned patterns, and (optionally) the actual
codebase files.  When codebase-aware chat is enabled and a review
is scoped, the chat can read relevant source files to ground its
answers in real code.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from context_graph.storage.base import ReviewStorage, CollaborationStorage

logger = logging.getLogger(__name__)

_vector_index_cache: dict[str, Any] = {}


def _get_cached_vector_index(codebase_path: str) -> Any | None:
    return _vector_index_cache.get(codebase_path)


def set_cached_vector_index(codebase_path: str, index: Any) -> None:
    _vector_index_cache[codebase_path] = index


@dataclass
class Citation:
    """A reference to an existing piece of data used to answer the question."""

    type: str  # "review", "finding", "entity", "pattern", "feedback", "code"
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
        finding_id: str | None = None,
        codebase_path: str | None = None,
        vector_index: Any | None = None,
    ) -> ChatResponse:
        """Answer a product question using existing data + LLM.

        Args:
            question: The user's question.
            review_id: Scope to a specific review for grounded answers.
            conversation_id: Continue an existing conversation.
            finding_id: Focus on a specific finding (drill-down chat).
            codebase_path: Explicit codebase path for standalone chat
                (when no review_id is provided). Ignored if review_id
                is set — the review's codebase_path is used instead.
        """

        conv_id = conversation_id or str(uuid4())

        # 1. Gather grounded context from storage + codebase
        context, citations = await self._gather_context(
            question, review_id, finding_id=finding_id, codebase_path=codebase_path,
        )

        # 1b. Inject codebase context via indexed _codebase_states (if available)
        self._inject_codebase_context(question, context, citations, vector_index)

        # 2. Generate follow-up suggestions before _build_system_prompt
        #    (which pops code_snippets/codebase_structure from context)
        followups = self._suggest_followups(question, context)

        # 3. Build conversation messages
        history = self._conversations.get(conv_id, [])
        history.append(ChatMessage(role="user", content=question))

        # 4. Build the LLM prompt (mutates context via pop — must be after followups)
        system_prompt = self._build_system_prompt(context)
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history[-10:]:  # Keep last 10 turns
            messages.append({"role": msg.role, "content": msg.content})

        # 5. Call LLM
        answer_text = await self._call_llm(messages)

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

    async def answer_stream(
        self,
        question: str,
        review_id: str | None = None,
        conversation_id: str | None = None,
        finding_id: str | None = None,
        codebase_path: str | None = None,
        vector_index: Any | None = None,
    ) -> AsyncIterator[str]:
        """Stream an answer as SSE events."""

        conv_id = conversation_id or str(uuid4())

        context, citations = await self._gather_context(
            question, review_id, finding_id=finding_id, codebase_path=codebase_path,
        )
        self._inject_codebase_context(question, context, citations, vector_index)

        history = self._conversations.get(conv_id, [])
        history.append(ChatMessage(role="user", content=question))

        system_prompt = self._build_system_prompt(context)
        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        for msg in history[-10:]:
            messages.append({"role": msg.role, "content": msg.content})

        followups = self._suggest_followups(question, context)

        full_answer = ""
        try:
            async for token in self._stream_llm(messages):
                full_answer += token
                yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception as exc:
            logger.error("Streaming LLM failed: %s", exc)
            error_msg = f"I encountered an error: {exc}"
            yield f"data: {json.dumps({'token': error_msg})}\n\n"
            full_answer = error_msg

        citation_dicts = [
            {"type": c.type, "id": c.id, "text": c.text, "url": c.url}
            for c in citations
        ]
        yield f"data: {json.dumps({'done': True, 'citations': citation_dicts, 'suggested_followups': followups, 'conversation_id': conv_id})}\n\n"

        history.append(ChatMessage(role="assistant", content=full_answer, citations=citations))
        self._conversations[conv_id] = history

    # ------------------------------------------------------------------
    # Context gathering — queries existing storage
    # ------------------------------------------------------------------

    async def _gather_context(
        self,
        question: str,
        review_id: str | None,
        *,
        finding_id: str | None = None,
        codebase_path: str | None = None,
    ) -> tuple[dict[str, Any], list[Citation]]:
        """Query existing storage for context relevant to the question."""

        context: dict[str, Any] = {}
        citations: list[Citation] = []
        q_lower = question.lower()
        review = None

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

        # ---- Finding drill-down ----
        if finding_id and review:
            self._inject_finding_context(context, citations, review, finding_id, review_id or "")

        # ---- Codebase-aware context (Layer 1 + Layer 2) ----
        resolved_codebase = None
        if review and getattr(review, "state", None) and review.state.codebase_path:
            resolved_codebase = review.state.codebase_path
        elif codebase_path:
            resolved_codebase = codebase_path

        # Legacy direct-path codebase injection (when codebase not yet indexed via /chat/index-codebase)
        if resolved_codebase and not getattr(self, "_codebase_states", {}):
            from context_graph.chat.codebase_reader import CodebaseIndex, CodebaseReader
            from context_graph.code_graph.hybrid_analyzer import HybridAnalyzer

            cb_path = Path(resolved_codebase)
            if cb_path.is_dir():
                try:
                    analyzer = HybridAnalyzer(cb_path)
                    hybrid_result = analyzer.analyze_fast()
                    index = CodebaseIndex.from_ast_results(hybrid_result.ast_results)
                    if not hasattr(self, "_codebase_states"):
                        self._codebase_states = {}
                    self._codebase_states[resolved_codebase] = index
                except Exception as exc:
                    logger.warning("Auto-index of codebase failed: %s", exc)

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
    # Codebase context injection
    # ------------------------------------------------------------------

    def _inject_codebase_context(
        self,
        question: str,
        context: dict[str, Any],
        citations: list[Citation],
        vector_index: Any | None = None,
    ) -> None:
        """Search the codebase index and inject matching snippets into context."""
        from context_graph.config.features import get_features

        codebase_states = getattr(self, "_codebase_states", {})
        if not codebase_states:
            return

        for cb_path, state in codebase_states.items():
            from context_graph.chat.codebase_reader import CodebaseReader

            vi = vector_index
            if vi is None and get_features().enable_semantic_search:
                vi = _get_cached_vector_index(str(cb_path))

            reader = CodebaseReader(cb_path, state, vector_index=vi)

            if hasattr(reader, "vector_index") and reader.vector_index is not None and get_features().enable_semantic_search:
                snippets = reader.hybrid_search(question, max_results=10)
            else:
                snippets = reader.search(question, max_results=5)

            if snippets:
                code_blocks = []
                for s in snippets:
                    code_blocks.append(
                        f"### {s.file_path} (lines {s.start_line}-{s.end_line})"
                        + (f" — {s.symbol_name}" if s.symbol_name else "")
                        + f"\n```\n{s.text}\n```"
                    )
                    citations.append(Citation(
                        type="code",
                        id=f"{s.file_path}:{s.start_line}",
                        text=f"{s.file_path}:{s.start_line}-{s.end_line}"
                        + (f" ({s.symbol_name})" if s.symbol_name else ""),
                    ))
                context["codebase_snippets"] = "\n\n".join(code_blocks)
                context["codebase_summary"] = reader.get_structure_summary()

    def _inject_finding_context(
        self,
        context: dict[str, Any],
        citations: list[Citation],
        review: Any,
        finding_id: str,
        review_id: str,
    ) -> None:
        """Inject a specific finding's full details into context."""
        for f in review.all_findings:
            if str(f.id) == finding_id:
                context["focused_finding"] = {
                    "title": f.title,
                    "severity": f.severity.value,
                    "dimension": f.dimension.value,
                    "category": f.category.value if hasattr(f.category, "value") else str(f.category),
                    "description": getattr(f, "description", "") or "",
                    "technical_details": getattr(f, "technical_details", "") or "",
                    "attack_scenario": getattr(f, "attack_scenario", "") or "",
                    "business_impact": getattr(f, "business_impact", "") or "",
                    "affected_components": getattr(f, "affected_components", []) or [],
                    "recommendation": getattr(f, "recommendation", "") or "",
                    "implementation_guidance": getattr(f, "implementation_guidance", "") or "",
                    "references": getattr(f, "references", []) or [],
                }
                citations.append(Citation(
                    type="finding",
                    id=str(f.id),
                    text=f"FOCUSED: {f.severity.value.upper()}: {f.title}",
                    url=f"/reviews/{review_id}#finding-{f.id}",
                ))
                break

    @staticmethod
    def _get_finding_components(review: Any | None, finding_id: str | None) -> list[str]:
        """Extract affected_components from a specific finding."""
        if not review or not finding_id:
            return []
        for f in review.all_findings:
            if str(f.id) == finding_id:
                return getattr(f, "affected_components", []) or []
        return []

    # ------------------------------------------------------------------
    # LLM interaction
    # ------------------------------------------------------------------

    def _build_system_prompt(self, context: dict[str, Any]) -> str:
        """Build a grounded system prompt from gathered context."""

        has_code = any(k in context for k in (
            "code_snippets", "codebase_structure", "codebase_snippets", "codebase_summary",
        ))
        has_finding_focus = "focused_finding" in context

        # Build context in sections to stay within token limits
        # Keep code snippets separate so they render cleanly
        code_snippets = context.pop("code_snippets", None)
        codebase_structure = context.pop("codebase_structure", None)
        codebase_snippets = context.pop("codebase_snippets", None)
        codebase_summary = context.pop("codebase_summary", None)

        context_block = json.dumps(context, indent=2, default=str)

        code_section = ""
        if codebase_structure:
            code_section += "\n\nCODEBASE STRUCTURE:\n```json\n"
            code_section += json.dumps(codebase_structure, indent=2, default=str)
            code_section += "\n```"

        if codebase_summary:
            code_section += f"\n\nCODEBASE SUMMARY: {codebase_summary}"

        if code_snippets:
            code_section += "\n\nRELEVANT CODE SNIPPETS:"
            for snippet in code_snippets:
                code_section += f"\n\n--- {snippet['file']}:{snippet['lines']}"
                if snippet.get("symbol"):
                    code_section += f" ({snippet['type']}: {snippet['symbol']})"
                code_section += f" ---\n```\n{snippet['code']}\n```"

        if codebase_snippets:
            code_section += f"\n\nRELEVANT CODE SNIPPETS:\n{codebase_snippets}"

        finding_instruction = ""
        if has_finding_focus:
            finding_instruction = """
- A specific finding is FOCUSED. Give priority to answering about this finding.
- Explain the finding in practical terms the PM can act on.
- If code snippets are available, reference the actual code when explaining the issue."""

        code_instruction = ""
        if has_code:
            code_instruction = """
- You have access to the codebase structure and relevant code snippets.
- When answering questions about the code, reference specific files and line numbers.
- Explain code in PM-friendly language — avoid jargon, focus on what it does and why it matters.
- If the code snippets don't contain what's needed, say so and suggest what to look for."""

        return f"""You are an AI assistant for Intently, a product analysis platform that helps PMs bridge PRDs to code. You answer questions about the product, codebase, reviews, and organizational patterns.

GROUNDING RULES:
- Base your answers ONLY on the context data provided below.
- When you reference a review, finding, or entity, mention it by name/ID so the frontend can link to it.
- If you don't have enough context to answer confidently, say so and suggest what the user could do (e.g., "Run a review on this PRD" or "Check the security findings for review X").
- Be concise but thorough. Use bullet points for lists.
- Do NOT hallucinate data. If the context doesn't contain information about something, say so.{finding_instruction}{code_instruction}

PRODUCT CONTEXT:
```json
{context_block}
```{code_section}

Answer the user's question using the above context. Cite specific files, reviews, findings, and entities when relevant."""

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
    # Streaming LLM
    # ------------------------------------------------------------------

    async def _stream_llm(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        if self._openai_key:
            async for token in self._stream_openai(messages):
                yield token
        elif self._anthropic_key:
            async for token in self._stream_anthropic(messages):
                yield token
        else:
            yield self._fallback_response(messages)

    async def _stream_openai(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self._openai_key)
        response = await client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            temperature=0.3,
            max_tokens=2048,
            stream=True,
        )
        async for chunk in response:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content

    async def _stream_anthropic(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=self._anthropic_key)
        system = ""
        chat_messages = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                chat_messages.append(m)

        async with client.messages.stream(
            model="claude-haiku-4-5-20251001",
            system=system,
            messages=chat_messages,
            max_tokens=2048,
            temperature=0.3,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    # ------------------------------------------------------------------
    # Follow-up suggestions
    # ------------------------------------------------------------------

    def _suggest_followups(
        self, question: str, context: dict[str, Any]
    ) -> list[str]:
        """Generate contextual follow-up question suggestions."""

        suggestions: list[str] = []
        q_lower = question.lower()

        if context.get("focused_finding"):
            suggestions.append("Explain this in simpler business terms")
            suggestions.append("What's the minimum fix to unblock shipping?")
            suggestions.append("Write me a ticket description for this issue")
        elif context.get("current_review"):
            review = context["current_review"]
            if review.get("security_findings", 0) > 0:
                suggestions.append("What are the most critical security findings?")
            if review.get("privacy_findings", 0) > 0:
                suggestions.append("Are there any privacy concerns with PII handling?")
            if review.get("quality_score"):
                suggestions.append("How can I improve the PRD quality score?")
            suggestions.append("What entities are affected by this change?")

        if context.get("codebase_structure") or context.get("code_snippets"):
            if "auth" not in q_lower:
                suggestions.append("How does authentication work in this codebase?")
            if "endpoint" not in q_lower:
                suggestions.append("What are the main API endpoints?")
            if "pii" not in q_lower and "sensitive" not in q_lower:
                suggestions.append("Which data models handle sensitive/PII data?")
        elif not context.get("current_review"):
            suggestions.append("Show me a summary of the latest review.")
            suggestions.append("What are the most common finding categories?")

        if "security" not in q_lower and not context.get("focused_finding"):
            suggestions.append("What security patterns should I be aware of?")

        return suggestions[:4]
