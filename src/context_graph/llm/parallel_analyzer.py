"""
Parallel LLM Analyzer - Run analysis on multiple providers concurrently.

Combines insights from OpenAI and Anthropic for more comprehensive analysis.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from context_graph.llm.provider import LLMProvider, LLMResponse, AnalysisType
from context_graph.llm.openai_provider import OpenAIProvider
from context_graph.llm.anthropic_provider import AnthropicProvider


@dataclass
class ParallelAnalysisResult:
    """Combined result from parallel LLM analysis."""
    
    responses: list[LLMResponse] = field(default_factory=list)
    merged_findings: list[dict[str, Any]] = field(default_factory=list)
    consensus_items: list[dict[str, Any]] = field(default_factory=list)
    divergent_items: list[dict[str, Any]] = field(default_factory=list)
    
    # Metadata
    providers_used: list[str] = field(default_factory=list)
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    
    @property
    def average_confidence(self) -> float:
        if not self.responses:
            return 0.0
        return sum(r.confidence for r in self.responses) / len(self.responses)


class ParallelLLMAnalyzer:
    """
    Orchestrates parallel analysis across multiple LLM providers.
    
    Benefits:
    - Reduces single-provider bias
    - Identifies consensus findings (higher confidence)
    - Catches findings one provider might miss
    - Provides diverse perspectives on security concerns
    """
    
    def __init__(
        self,
        openai_api_key: str | None = None,
        anthropic_api_key: str | None = None,
        openai_model: str = "gpt-4o",
        anthropic_model: str = "claude-sonnet-4-20250514",
    ) -> None:
        self.providers: list[LLMProvider] = []
        
        if openai_api_key:
            self.providers.append(OpenAIProvider(
                api_key=openai_api_key,
                model=openai_model,
            ))
        
        if anthropic_api_key:
            self.providers.append(AnthropicProvider(
                api_key=anthropic_api_key,
                model=anthropic_model,
            ))
        
        if not self.providers:
            raise ValueError("At least one API key must be provided")
    
    async def extract_intent(self, prd_content: str) -> ParallelAnalysisResult:
        """Extract intent using all providers in parallel."""
        tasks = [
            provider.extract_intent(prd_content)
            for provider in self.providers
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful responses
        valid_responses = [
            r for r in responses
            if isinstance(r, LLMResponse)
        ]
        
        return self._merge_intent_results(valid_responses)
    
    async def security_review(
        self,
        intent: dict[str, Any],
        state: dict[str, Any],
        delta: dict[str, Any],
    ) -> ParallelAnalysisResult:
        """Perform security review using all providers in parallel."""
        import logging
        
        tasks = [
            provider.security_review(intent, state, delta)
            for provider in self.providers
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_responses = []
        for i, r in enumerate(responses):
            if isinstance(r, LLMResponse):
                valid_responses.append(r)
                logging.info(f"LLM provider {self.providers[i].provider_name} returned {len(r.structured_data.get('findings', []))} findings")
            elif isinstance(r, Exception):
                logging.error(f"LLM provider {self.providers[i].provider_name} failed: {r}")
        
        if not valid_responses:
            logging.warning("All LLM providers failed or returned no valid responses")
        
        return self._merge_security_results(valid_responses)
    
    async def threat_model(
        self,
        entities: list[dict[str, Any]],
        relationships: list[dict[str, Any]],
    ) -> ParallelAnalysisResult:
        """Generate threat model using all providers in parallel."""
        tasks = [
            provider.threat_model(entities, relationships)
            for provider in self.providers
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_responses = [
            r for r in responses
            if isinstance(r, LLMResponse)
        ]
        
        return self._merge_threat_results(valid_responses)
    
    async def privacy_review(
        self,
        intent: dict[str, Any],
        state: dict[str, Any],
        delta: dict[str, Any],
    ) -> ParallelAnalysisResult:
        """Perform privacy review using LINDDUN framework with all providers in parallel."""
        import logging
        
        tasks = [
            provider.privacy_review(intent, state, delta)
            for provider in self.providers
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_responses = []
        for i, r in enumerate(responses):
            if isinstance(r, LLMResponse):
                valid_responses.append(r)
                logging.info(f"LLM provider {self.providers[i].provider_name} returned {len(r.structured_data.get('findings', []))} privacy findings")
            elif isinstance(r, Exception):
                logging.error(f"LLM provider {self.providers[i].provider_name} privacy review failed: {r}")
        
        if not valid_responses:
            logging.warning("All LLM providers failed or returned no valid privacy responses")
        
        return self._merge_privacy_results(valid_responses)
    
    async def compliance_review(
        self,
        intent: dict[str, Any],
        state: dict[str, Any],
        delta: dict[str, Any],
        frameworks: list[str] | None = None,
    ) -> ParallelAnalysisResult:
        """Perform compliance review using all providers in parallel."""
        import logging
        
        tasks = [
            provider.compliance_review(intent, state, delta, frameworks)
            for provider in self.providers
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_responses = []
        for i, r in enumerate(responses):
            if isinstance(r, LLMResponse):
                valid_responses.append(r)
                logging.info(f"LLM provider {self.providers[i].provider_name} returned {len(r.structured_data.get('findings', []))} compliance findings")
            elif isinstance(r, Exception):
                logging.error(f"LLM provider {self.providers[i].provider_name} compliance review failed: {r}")
        
        if not valid_responses:
            logging.warning("All LLM providers failed or returned no valid compliance responses")
        
        return self._merge_compliance_results(valid_responses)
    
    def _merge_intent_results(
        self, 
        responses: list[LLMResponse]
    ) -> ParallelAnalysisResult:
        """Merge intent extraction results from multiple providers."""
        result = ParallelAnalysisResult(
            responses=responses,
            providers_used=[r.provider for r in responses],
            total_tokens=sum(r.tokens_used for r in responses),
            total_latency_ms=max(r.latency_ms for r in responses) if responses else 0,
        )
        
        if not responses:
            return result
        
        # Merge data entities
        all_entities: dict[str, dict[str, Any]] = {}
        for response in responses:
            entities = response.structured_data.get("data_entities", [])
            for entity in entities:
                name = entity.get("name", "").lower()
                if name:
                    if name in all_entities:
                        # Merge, keep higher sensitivity
                        existing = all_entities[name]
                        if entity.get("is_sensitive"):
                            existing["is_sensitive"] = True
                        existing["sources"] = existing.get("sources", []) + [response.provider]
                    else:
                        all_entities[name] = {**entity, "sources": [response.provider]}
        
        # Find consensus (entities identified by multiple providers)
        for name, entity in all_entities.items():
            if len(entity.get("sources", [])) > 1:
                result.consensus_items.append(entity)
            else:
                result.divergent_items.append(entity)
        
        # Merge features
        all_features: set[str] = set()
        for response in responses:
            features = response.structured_data.get("features", [])
            all_features.update(features)
        
        # Merge potential risks
        all_risks: list[dict[str, Any]] = []
        seen_risks: set[str] = set()
        for response in responses:
            risks = response.structured_data.get("potential_risks", [])
            for risk in risks:
                risk_key = str(risk).lower()[:50]  # Approximate dedup
                if risk_key not in seen_risks:
                    seen_risks.add(risk_key)
                    all_risks.append({"risk": risk, "source": response.provider})
        
        result.merged_findings = list(all_entities.values())
        
        return result
    
    def _merge_security_results(
        self, 
        responses: list[LLMResponse]
    ) -> ParallelAnalysisResult:
        """Merge security review results from multiple providers."""
        result = ParallelAnalysisResult(
            responses=responses,
            providers_used=[r.provider for r in responses],
            total_tokens=sum(r.tokens_used for r in responses),
            total_latency_ms=max(r.latency_ms for r in responses) if responses else 0,
        )
        
        if not responses:
            return result
        
        # Collect all findings
        all_findings: list[dict[str, Any]] = []
        finding_signatures: dict[str, dict[str, Any]] = {}
        
        for response in responses:
            findings = response.structured_data.get("findings", [])
            for finding in findings:
                # Create signature for dedup
                sig = self._finding_signature(finding)
                
                if sig in finding_signatures:
                    # Found by multiple providers - increase confidence
                    existing = finding_signatures[sig]
                    existing["providers"].append(response.provider)
                    existing["confidence"] = min(
                        existing.get("confidence", 0.5) + 0.2, 
                        1.0
                    )
                else:
                    finding_signatures[sig] = {
                        **finding,
                        "providers": [response.provider],
                    }
        
        # Categorize findings
        for sig, finding in finding_signatures.items():
            if len(finding.get("providers", [])) > 1:
                result.consensus_items.append(finding)
            else:
                result.divergent_items.append(finding)
            result.merged_findings.append(finding)
        
        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        result.merged_findings.sort(
            key=lambda f: severity_order.get(f.get("severity", "info"), 5)
        )
        
        return result
    
    def _merge_threat_results(
        self, 
        responses: list[LLMResponse]
    ) -> ParallelAnalysisResult:
        """Merge threat modeling results from multiple providers."""
        result = ParallelAnalysisResult(
            responses=responses,
            providers_used=[r.provider for r in responses],
            total_tokens=sum(r.tokens_used for r in responses),
            total_latency_ms=max(r.latency_ms for r in responses) if responses else 0,
        )
        
        if not responses:
            return result
        
        # Merge attack paths
        all_paths: list[dict[str, Any]] = []
        path_signatures: set[str] = set()
        
        for response in responses:
            paths = response.structured_data.get("attack_paths", [])
            for path in paths:
                sig = f"{path.get('name', '')}:{path.get('target', '')}"
                if sig not in path_signatures:
                    path_signatures.add(sig)
                    all_paths.append({**path, "source": response.provider})
        
        result.merged_findings = all_paths
        
        # Merge trust boundaries
        boundaries: dict[str, dict[str, Any]] = {}
        for response in responses:
            bs = response.structured_data.get("trust_boundaries", [])
            for b in bs:
                name = b.get("name", "")
                if name and name not in boundaries:
                    boundaries[name] = b
        
        return result
    
    def _merge_privacy_results(
        self,
        responses: list[LLMResponse]
    ) -> ParallelAnalysisResult:
        """Merge privacy review results from multiple providers."""
        result = ParallelAnalysisResult(
            responses=responses,
            providers_used=[r.provider for r in responses],
            total_tokens=sum(r.tokens_used for r in responses),
            total_latency_ms=max(r.latency_ms for r in responses) if responses else 0,
        )
        
        if not responses:
            return result
        
        # Collect all findings
        finding_signatures: dict[str, dict[str, Any]] = {}
        
        for response in responses:
            findings = response.structured_data.get("findings", [])
            for finding in findings:
                # Create signature for dedup
                sig = self._finding_signature(finding)
                
                if sig in finding_signatures:
                    # Found by multiple providers - increase confidence
                    existing = finding_signatures[sig]
                    existing["providers"].append(response.provider)
                    existing["confidence"] = min(
                        existing.get("confidence", 0.5) + 0.2,
                        1.0
                    )
                    # Merge data subjects and personal data types
                    existing["data_subjects"] = list(set(
                        existing.get("data_subjects", []) + 
                        finding.get("data_subjects", [])
                    ))
                    existing["personal_data_types"] = list(set(
                        existing.get("personal_data_types", []) + 
                        finding.get("personal_data_types", [])
                    ))
                else:
                    finding_signatures[sig] = {
                        **finding,
                        "providers": [response.provider],
                    }
        
        # Categorize findings
        for sig, finding in finding_signatures.items():
            if len(finding.get("providers", [])) > 1:
                result.consensus_items.append(finding)
            else:
                result.divergent_items.append(finding)
            result.merged_findings.append(finding)
        
        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        result.merged_findings.sort(
            key=lambda f: severity_order.get(f.get("severity", "info"), 5)
        )
        
        return result
    
    def _merge_compliance_results(
        self,
        responses: list[LLMResponse]
    ) -> ParallelAnalysisResult:
        """Merge compliance review results from multiple providers."""
        result = ParallelAnalysisResult(
            responses=responses,
            providers_used=[r.provider for r in responses],
            total_tokens=sum(r.tokens_used for r in responses),
            total_latency_ms=max(r.latency_ms for r in responses) if responses else 0,
        )
        
        if not responses:
            return result
        
        # Collect all findings, grouped by framework and control
        finding_signatures: dict[str, dict[str, Any]] = {}
        
        for response in responses:
            findings = response.structured_data.get("findings", [])
            for finding in findings:
                # Create signature including framework and control_id for compliance
                framework = finding.get("framework", "")
                control_id = finding.get("control_id", "")
                title = finding.get("title", "").lower()[:30]
                severity = finding.get("severity", "").lower()
                
                sig = f"{framework}:{control_id}:{severity}:{title}"
                
                if sig in finding_signatures:
                    # Found by multiple providers - increase confidence
                    existing = finding_signatures[sig]
                    existing["providers"].append(response.provider)
                    existing["confidence"] = min(
                        existing.get("confidence", 0.5) + 0.2,
                        1.0
                    )
                else:
                    finding_signatures[sig] = {
                        **finding,
                        "providers": [response.provider],
                    }
        
        # Categorize findings
        for sig, finding in finding_signatures.items():
            if len(finding.get("providers", [])) > 1:
                result.consensus_items.append(finding)
            else:
                result.divergent_items.append(finding)
            result.merged_findings.append(finding)
        
        # Sort by severity and framework
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        result.merged_findings.sort(
            key=lambda f: (
                severity_order.get(f.get("severity", "info"), 5),
                f.get("framework", "zzz")
            )
        )
        
        return result
    
    def _finding_signature(self, finding: dict[str, Any]) -> str:
        """Create a signature for finding deduplication."""
        title = finding.get("title", "").lower()[:30]
        category = finding.get("category", "").lower()
        severity = finding.get("severity", "").lower()
        return f"{severity}:{category}:{title}"

