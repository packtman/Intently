"""
Anthropic Claude LLM Provider implementation.
"""

from __future__ import annotations

import json
import time
from typing import Any

from anthropic import AsyncAnthropic

from context_graph.llm.provider import (
    LLMProvider,
    LLMResponse,
    AnalysisRequest,
    AnalysisType,
)


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API provider for LLM analysis."""
    
    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> None:
        super().__init__(api_key, model, temperature, max_tokens)
        self.client = AsyncAnthropic(api_key=api_key)
    
    @property
    def provider_name(self) -> str:
        return "anthropic"
    
    async def analyze(self, request: AnalysisRequest) -> LLMResponse:
        """Perform analysis using Anthropic Claude."""
        system_prompt = self._get_system_prompt(request.analysis_type)
        
        # Add JSON instruction to system prompt for Claude
        system_prompt += "\n\nIMPORTANT: Respond with valid JSON only. No markdown formatting, no code blocks, just raw JSON."
        
        user_content = self._build_user_prompt(request)
        
        start_time = time.time()
        
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_content},
            ],
            temperature=self.temperature,
        )
        
        latency_ms = (time.time() - start_time) * 1000
        
        # Extract content from response
        content = ""
        for block in response.content:
            if hasattr(block, "text"):
                content += block.text
        
        tokens_used = response.usage.input_tokens + response.usage.output_tokens
        
        # Parse JSON response
        structured_data = self._parse_json_response(content)
        
        return LLMResponse(
            provider=self.provider_name,
            model=self.model,
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
        custom_prompt = COMPLIANCE_REVIEW_PROMPT.format(frameworks=selected_frameworks)
        
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
        
        parts.append("\nProvide your analysis as valid JSON.")
        
        return "\n\n".join(parts)
    
    def _parse_json_response(self, content: str) -> dict[str, Any]:
        """Parse JSON from Claude's response, handling various formats."""
        # Try direct parse
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from markdown code blocks
        import re
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON object in content
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        return {"raw": content, "parse_error": True}
    
    def _calculate_confidence(self, data: dict[str, Any]) -> float:
        """Calculate confidence score based on response completeness."""
        if not data or data.get("parse_error"):
            return 0.0
        
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

