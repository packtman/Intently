"""
OpenAI LLM Provider implementation.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from openai import AsyncOpenAI

from context_graph.llm.provider import (
    LLMProvider,
    LLMResponse,
    AnalysisRequest,
    AnalysisType,
    REFINEMENT_PROMPT,
)


class OpenAIProvider(LLMProvider):
    """OpenAI API provider for LLM analysis."""

    def _uses_max_completion_tokens(self, model: str) -> bool:
        """
        Some newer OpenAI models (e.g., GPT-5 family) require `max_completion_tokens`
        instead of `max_tokens` on the Chat Completions API.
        """
        m = (model or "").lower()
        return m.startswith("gpt-5") or m.startswith("o")
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-5.2",
        temperature: float = 0.0,
        max_tokens: int = 16384,
    ) -> None:
        super().__init__(api_key, model, temperature, max_tokens)
        self.client = AsyncOpenAI(api_key=api_key)
    
    @property
    def provider_name(self) -> str:
        return "openai"
    
    async def analyze(self, request: AnalysisRequest) -> LLMResponse:
        """Perform analysis using OpenAI."""
        system_prompt = (
            request.context.get("custom_prompt")
            if request.context and isinstance(request.context.get("custom_prompt"), str)
            else self._get_system_prompt(request.analysis_type)
        )
        
        user_content = self._build_user_prompt(request)

        # Prompt repetition: duplicate the user content for a second attention pass
        user_content = self._apply_prompt_repetition(
            user_content,
            enabled=self._resolve_prompt_repetition(request.context),
        )
        
        # Allow per-request model override (e.g. faster model for FP filtering)
        effective_model = (
            request.context.get("model_override")
            if request.context and request.context.get("model_override")
            else self.model
        )

        start_time = time.time()

        create_kwargs: dict[str, Any] = {
            "model": effective_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": self.temperature,
            "response_format": {"type": "json_object"},
            "seed": 42,
        }
        if self._uses_max_completion_tokens(effective_model):
            create_kwargs["max_completion_tokens"] = self.max_tokens
        else:
            create_kwargs["max_tokens"] = self.max_tokens

        # Retry with `max_completion_tokens` if the model rejects `max_tokens`
        try:
            response = await self.client.chat.completions.create(**create_kwargs)
        except Exception as e:
            msg = str(e)
            if "Unsupported parameter: 'max_tokens'" in msg:
                create_kwargs.pop("max_tokens", None)
                create_kwargs["max_completion_tokens"] = self.max_tokens
                response = await self.client.chat.completions.create(**create_kwargs)
            elif (
                "Unsupported parameter: 'response_format'" in msg
                or ("response_format" in msg and "unsupported" in msg.lower())
            ):
                # Some models/endpoints may not support structured response formatting.
                # Fall back to prompt-only JSON instruction.
                create_kwargs.pop("response_format", None)
                response = await self.client.chat.completions.create(**create_kwargs)
            else:
                raise
        
        latency_ms = (time.time() - start_time) * 1000
        
        content = response.choices[0].message.content or "{}"
        tokens_used = response.usage.total_tokens if response.usage else 0
        
        # Parse JSON response
        try:
            structured_data = json.loads(content)
        except json.JSONDecodeError:
            logging.warning(
                "OpenAI response for %s was not valid JSON (%d chars). "
                "First 200 chars: %s",
                request.analysis_type.value,
                len(content),
                content[:200],
            )
            structured_data = {"raw": content, "parse_error": True}

        # Validate that the response contains the expected top-level keys
        structured_data = self._validate_response(
            structured_data, request.analysis_type
        )
        
        return LLMResponse(
            provider=self.provider_name,
            model=effective_model,
            content=content,
            analysis_type=request.analysis_type,
            structured_data=structured_data,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            confidence=self._calculate_confidence(structured_data),
        )
    
    async def extract_intent(self, prd_content: str) -> LLMResponse:
        """Extract structured intent from PRD."""
        request = AnalysisRequest(
            analysis_type=AnalysisType.INTENT_EXTRACTION,
            content=prd_content,
            prd_content=prd_content,
        )
        return await self.analyze(request)
    
    async def security_review(
        self,
        intent: dict[str, Any],
        state: dict[str, Any],
        delta: dict[str, Any],
    ) -> LLMResponse:
        """Perform security review on the delta."""
        request = AnalysisRequest(
            analysis_type=AnalysisType.SECURITY_REVIEW,
            content=json.dumps({
                "intent": intent,
                "current_state": state,
                "delta": delta,
            }, indent=2),
            context={
                "intent": intent,
                "state": state,
                "delta": delta,
            },
        )
        return await self.analyze(request)
    
    async def threat_model(
        self,
        entities: list[dict[str, Any]],
        relationships: list[dict[str, Any]],
    ) -> LLMResponse:
        """Generate threat model from context graph."""
        request = AnalysisRequest(
            analysis_type=AnalysisType.THREAT_MODELING,
            content=json.dumps({
                "entities": entities,
                "relationships": relationships,
            }, indent=2),
            context={
                "entities": entities,
                "relationships": relationships,
            },
        )
        return await self.analyze(request)
    
    async def privacy_review(
        self,
        intent: dict[str, Any],
        state: dict[str, Any],
        delta: dict[str, Any],
    ) -> LLMResponse:
        """Perform privacy review using LINDDUN framework."""
        request = AnalysisRequest(
            analysis_type=AnalysisType.PRIVACY_REVIEW,
            content=json.dumps({
                "intent": intent,
                "current_state": state,
                "delta": delta,
            }, indent=2),
            context={
                "intent": intent,
                "state": state,
                "delta": delta,
            },
        )
        return await self.analyze(request)
    
    async def compliance_review(
        self,
        intent: dict[str, Any],
        state: dict[str, Any],
        delta: dict[str, Any],
        frameworks: list[str] | None = None,
    ) -> LLMResponse:
        """Perform compliance review against selected frameworks."""
        from context_graph.llm.provider import COMPLIANCE_REVIEW_PROMPT
        
        # Default to common frameworks if none specified
        if not frameworks:
            frameworks = ["soc2", "hipaa", "pci_dss"]
        
        # Build framework description for prompt
        framework_descriptions = {
            "soc2": "SOC 2 Trust Service Criteria (Security, Availability, Processing Integrity, Confidentiality, Privacy)",
            "hipaa": "HIPAA (Health Insurance Portability and Accountability Act) - PHI handling, safeguards",
            "pci_dss": "PCI-DSS (Payment Card Industry Data Security Standard) - Cardholder data protection",
            "iso_27001": "ISO 27001 - Information Security Management System controls",
            "gdpr": "GDPR (General Data Protection Regulation) - EU data protection",
            "ccpa": "CCPA (California Consumer Privacy Act) - California privacy requirements",
        }
        
        selected_frameworks = "\n".join([
            f"- {framework_descriptions.get(f, f)}" 
            for f in frameworks
        ])
        
        # Create custom prompt with selected frameworks
        # IMPORTANT: don't use `.format(...)` because the prompt contains many `{}` JSON braces.
        custom_prompt = COMPLIANCE_REVIEW_PROMPT.replace("{frameworks}", selected_frameworks)
        
        request = AnalysisRequest(
            analysis_type=AnalysisType.COMPLIANCE_REVIEW,
            content=json.dumps({
                "intent": intent,
                "current_state": state,
                "delta": delta,
                "frameworks_to_evaluate": frameworks,
            }, indent=2),
            context={
                "intent": intent,
                "state": state,
                "delta": delta,
                "frameworks": frameworks,
                "custom_prompt": custom_prompt,
            },
        )
        return await self.analyze(request)
    
    async def engineering_review(
        self,
        intent: dict[str, Any],
        state: dict[str, Any],
        delta: dict[str, Any],
        engineering_metrics: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Perform engineering feasibility and effort review.
        
        This review focuses on:
        1. Understanding the current codebase context
        2. Assessing PRD feature feasibility based on existing code
        3. Providing detailed time estimates based on actual codebase metrics
        """
        # Build enhanced state with engineering metrics for context-aware analysis
        enhanced_state = {
            **state,
            "codebase_metrics": engineering_metrics or {},
        }
        
        request = AnalysisRequest(
            analysis_type=AnalysisType.ENGINEERING_REVIEW,
            content=json.dumps({
                "intent": intent,
                "current_state": enhanced_state,
                "codebase_metrics": engineering_metrics or {},
                "delta": delta,
            }, indent=2),
            context={
                "intent": intent,
                "state": enhanced_state,
                "engineering_metrics": engineering_metrics,
                "delta": delta,
            },
        )
        return await self.analyze(request)
    
    async def architecture_review(
        self,
        intent: dict[str, Any],
        state: dict[str, Any],
        delta: dict[str, Any],
    ) -> LLMResponse:
        """Perform architecture review (API design, dependencies, patterns)."""
        request = AnalysisRequest(
            analysis_type=AnalysisType.ARCHITECTURE_REVIEW,
            content=json.dumps({
                "intent": intent,
                "current_state": state,
                "delta": delta,
            }, indent=2),
            context={
                "intent": intent,
                "state": state,
                "delta": delta,
            },
        )
        return await self.analyze(request)

    async def refine_findings(
        self,
        findings: list[dict[str, Any]],
        dimension: str,
    ) -> list[dict[str, Any]]:
        """Run a refinement/consolidation pass over raw findings.

        Sends the full list of findings to the LLM with a refinement prompt
        that asks it to deduplicate, merge, validate severities, remove noise
        and return a prioritised, consolidated list.
        """
        request = AnalysisRequest(
            analysis_type=AnalysisType.SECURITY_REVIEW,  # reuse type; prompt overrides
            content=json.dumps({"findings": findings}, indent=2),
            context={
                "custom_prompt": REFINEMENT_PROMPT,
                "dimension": dimension,
            },
        )
        response = await self.analyze(request)
        refined = response.structured_data.get("findings", [])
        if not refined:
            logging.warning(
                "OpenAI refinement for %s returned no findings — keeping originals",
                dimension,
            )
            return findings
        return refined

    # Expected top-level keys per analysis type.
    # If the response is missing *all* of them, the JSON is likely malformed.
    _EXPECTED_KEYS: dict[AnalysisType, list[str]] = {
        AnalysisType.SECURITY_REVIEW: ["findings"],
        AnalysisType.PRIVACY_REVIEW: ["findings"],
        AnalysisType.COMPLIANCE_REVIEW: ["findings"],
        AnalysisType.ENGINEERING_REVIEW: ["findings"],
        AnalysisType.ARCHITECTURE_REVIEW: ["findings"],
        AnalysisType.INTENT_EXTRACTION: ["title", "features", "data_entities"],
        AnalysisType.THREAT_MODELING: ["attack_paths", "trust_boundaries"],
    }

    def _validate_response(
        self,
        data: dict[str, Any],
        analysis_type: AnalysisType,
    ) -> dict[str, Any]:
        """Validate that the LLM response contains expected keys.

        If the response has a parse error or is completely missing the
        expected structure, log a warning and inject empty defaults so
        downstream merge logic doesn't break.
        """
        if data.get("parse_error"):
            return data

        expected = self._EXPECTED_KEYS.get(analysis_type, [])
        if expected and not any(k in data for k in expected):
            logging.warning(
                "OpenAI %s response missing expected keys %s. "
                "Got keys: %s — injecting empty defaults.",
                analysis_type.value,
                expected,
                list(data.keys())[:10],
            )
            for key in expected:
                data.setdefault(key, [])
        return data

    def _build_user_prompt(self, request: AnalysisRequest) -> str:
        """Build the user prompt from request."""
        parts = []
        
        if request.prd_content:
            parts.append(f"## PRD Content\n\n{request.prd_content}")
        
        if request.code_snippets:
            parts.append("## Code Snippets\n")
            for i, snippet in enumerate(request.code_snippets, 1):
                parts.append(f"### Snippet {i}\n```\n{snippet}\n```")
        
        if request.existing_findings:
            parts.append(f"## Existing Findings\n\n{json.dumps(request.existing_findings, indent=2)}")
        
        if request.content and not parts:
            parts.append(request.content)
        elif request.content:
            parts.append(f"## Analysis Input\n\n{request.content}")
        
        return "\n\n".join(parts)
    
    def _calculate_confidence(self, data: dict[str, Any]) -> float:
        """Calculate confidence score based on response completeness."""
        if not data:
            return 0.0
        
        # Check for expected fields based on analysis type
        expected_fields = {
            "findings": 0.3,
            "summary": 0.2,
            "title": 0.1,
            "data_entities": 0.2,
            "potential_risks": 0.2,
        }
        
        confidence = 0.0
        for field, weight in expected_fields.items():
            if field in data and data[field]:
                confidence += weight
        
        return min(confidence, 1.0)

