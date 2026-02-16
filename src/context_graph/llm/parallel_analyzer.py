"""
Parallel LLM Analyzer - Run analysis on multiple providers concurrently.

Combines insights from OpenAI and Anthropic for more comprehensive analysis.
Supports iterative multi-round analysis for comprehensive coverage.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from context_graph.llm.provider import LLMProvider, LLMResponse, AnalysisType
from context_graph.llm.openai_provider import OpenAIProvider
from context_graph.llm.anthropic_provider import AnthropicProvider
from context_graph.llm.iterative_analyzer import (
    IterativeAnalyzer,
    IterativeAnalysisResult,
    LLMCallResult,
)
from context_graph.llm.analysis_categories import (
    AnalysisTypeCategories,
    get_analysis_config,
)
from context_graph.config.features import get_features


logger = logging.getLogger(__name__)


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
        openai_model: str = "gpt-5.2",
        anthropic_model: str = "claude-opus-4-5-20251101",
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
        
        if not valid_responses:
            raise RuntimeError("LLM extract_intent failed: no providers returned a valid response")
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
            raise RuntimeError("LLM security_review failed: no providers returned a valid response")
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
        
        if not valid_responses:
            raise RuntimeError("LLM threat_model failed: no providers returned a valid response")
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
            raise RuntimeError("LLM privacy_review failed: no providers returned a valid response")
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
            raise RuntimeError("LLM compliance_review failed: no providers returned a valid response")
        return self._merge_compliance_results(valid_responses)
    
    async def engineering_review(
        self,
        intent: dict[str, Any],
        state: dict[str, Any],
        delta: dict[str, Any],
        engineering_metrics: dict[str, Any] | None = None,
    ) -> ParallelAnalysisResult:
        """Perform engineering feasibility and effort review using all providers in parallel.
        
        This review focuses on:
        1. Understanding the current codebase context (metrics, complexity, patterns)
        2. Assessing PRD feature feasibility based on existing code
        3. Providing detailed time estimates based on actual codebase metrics
        
        Args:
            intent: PRD intent data
            state: Current codebase state
            delta: Changes between intent and state
            engineering_metrics: Detailed metrics from EngineeringAnalyzer
        """
        import logging
        
        logging.info(f"Starting engineering review with metrics: {bool(engineering_metrics)}")
        if engineering_metrics:
            logging.info(f"Metrics summary: {engineering_metrics.get('source_files', 0)} files, "
                        f"{engineering_metrics.get('total_lines', 0)} lines, "
                        f"test ratio: {engineering_metrics.get('test_to_code_ratio', 0):.2f}")
        
        tasks = [
            provider.engineering_review(intent, state, delta, engineering_metrics)
            for provider in self.providers
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_responses = []
        for i, r in enumerate(responses):
            if isinstance(r, LLMResponse):
                valid_responses.append(r)
                # Log more details about the response
                findings_count = len(r.structured_data.get('findings', []))
                feasibility = r.structured_data.get('feasibility_assessment', {}).get('overall_feasibility', 'N/A')
                logging.info(f"LLM provider {self.providers[i].provider_name} returned "
                            f"{findings_count} findings, feasibility: {feasibility}")
            elif isinstance(r, Exception):
                logging.error(f"LLM provider {self.providers[i].provider_name} engineering review failed: {r}")
        
        if not valid_responses:
            raise RuntimeError("LLM engineering_review failed: no providers returned a valid response")
        return self._merge_engineering_results(valid_responses)
    
    async def architecture_review(
        self,
        intent: dict[str, Any],
        state: dict[str, Any],
        delta: dict[str, Any],
    ) -> ParallelAnalysisResult:
        """Perform architecture review using all providers in parallel."""
        import logging
        
        tasks = [
            provider.architecture_review(intent, state, delta)
            for provider in self.providers
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_responses = []
        for i, r in enumerate(responses):
            if isinstance(r, LLMResponse):
                valid_responses.append(r)
                logging.info(f"LLM provider {self.providers[i].provider_name} returned {len(r.structured_data.get('findings', []))} architecture findings")
            elif isinstance(r, Exception):
                logging.error(f"LLM provider {self.providers[i].provider_name} architecture review failed: {r}")
        
        if not valid_responses:
            raise RuntimeError("LLM architecture_review failed: no providers returned a valid response")
        return self._merge_architecture_results(valid_responses)
    
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
    
    def _merge_engineering_results(
        self,
        responses: list[LLMResponse]
    ) -> ParallelAnalysisResult:
        """Merge engineering review results from multiple providers."""
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
                    # Merge affected files
                    existing["affected_files"] = list(set(
                        existing.get("affected_files", []) + 
                        finding.get("affected_files", [])
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
    
    def _merge_architecture_results(
        self,
        responses: list[LLMResponse]
    ) -> ParallelAnalysisResult:
        """Merge architecture review results from multiple providers."""
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
                # Create signature for dedup - include breaking_change for architecture
                title = finding.get("title", "").lower()[:30]
                category = finding.get("category", "").lower()
                severity = finding.get("severity", "").lower()
                breaking = "breaking" if finding.get("breaking_change") else "non-breaking"
                sig = f"{severity}:{category}:{breaking}:{title}"
                
                if sig in finding_signatures:
                    # Found by multiple providers - increase confidence
                    existing = finding_signatures[sig]
                    existing["providers"].append(response.provider)
                    existing["confidence"] = min(
                        existing.get("confidence", 0.5) + 0.2,
                        1.0
                    )
                    # Merge affected services
                    existing["affected_services"] = list(set(
                        existing.get("affected_services", []) + 
                        finding.get("affected_services", [])
                    ))
                    existing["affected_apis"] = list(set(
                        existing.get("affected_apis", []) + 
                        finding.get("affected_apis", [])
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
        
        # Sort by severity and breaking changes first
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        result.merged_findings.sort(
            key=lambda f: (
                0 if f.get("breaking_change") else 1,
                severity_order.get(f.get("severity", "info"), 5)
            )
        )
        
        return result
    
    def _finding_signature(self, finding: dict[str, Any]) -> str:
        """Create a signature for finding deduplication.
        
        Uses category + severity + normalised title keywords so that
        semantically identical findings from different providers merge
        even when phrased differently (e.g. "SQL Injection in Login" vs
        "Login Endpoint SQL Injection Attack").
        """
        import re

        category = finding.get("category", "").lower().strip()
        severity = finding.get("severity", "").lower().strip()

        # Normalise the title: lowercase, strip punctuation, sort keywords
        raw_title = finding.get("title", "").lower()
        words = sorted(set(re.sub(r"[^a-z0-9 ]", "", raw_title).split()))
        # Also pull top keywords from affected_components for extra signal
        components = finding.get("affected_components", [])
        if isinstance(components, list):
            comp_words = sorted(
                set(
                    w
                    for c in components
                    for w in re.sub(r"[^a-z0-9 ]", "", str(c).lower()).split()
                )
            )
        else:
            comp_words = []

        return f"{severity}:{category}:{' '.join(words)}:{' '.join(comp_words)}"
    
    # ==================== Iterative Analysis Methods ====================
    
    async def security_review_iterative(
        self,
        intent: dict[str, Any],
        state: dict[str, Any],
        delta: dict[str, Any],
    ) -> ParallelAnalysisResult:
        """
        Perform iterative security review using multiple rounds for comprehensive coverage.
        
        Uses the iterative analysis framework to ensure all security categories
        (STRIDE, OWASP Top 10) are covered across multiple rounds.
        """
        features = get_features()
        
        if not features.enable_iterative_security_analysis:
            # Fall back to single-pass analysis
            return await self.security_review(intent, state, delta)
        
        return await self._run_iterative_review(
            analysis_type=AnalysisTypeCategories.SECURITY,
            intent=intent,
            state=state,
            delta=delta,
            review_method=self._single_security_review,
        )
    
    async def privacy_review_iterative(
        self,
        intent: dict[str, Any],
        state: dict[str, Any],
        delta: dict[str, Any],
    ) -> ParallelAnalysisResult:
        """
        Perform iterative privacy review using multiple rounds for comprehensive LINDDUN coverage.
        """
        features = get_features()
        
        if not features.enable_iterative_privacy_analysis:
            return await self.privacy_review(intent, state, delta)
        
        return await self._run_iterative_review(
            analysis_type=AnalysisTypeCategories.PRIVACY,
            intent=intent,
            state=state,
            delta=delta,
            review_method=self._single_privacy_review,
        )
    
    async def compliance_review_iterative(
        self,
        intent: dict[str, Any],
        state: dict[str, Any],
        delta: dict[str, Any],
        frameworks: list[str] | None = None,
    ) -> ParallelAnalysisResult:
        """
        Perform iterative compliance review using multiple rounds for comprehensive framework coverage.
        """
        features = get_features()
        
        if not features.enable_iterative_compliance_analysis:
            return await self.compliance_review(intent, state, delta, frameworks)
        
        async def review_method(context: str, metadata: dict[str, Any]) -> LLMCallResult:
            return await self._single_compliance_review(context, metadata, frameworks)
        
        return await self._run_iterative_review(
            analysis_type=AnalysisTypeCategories.COMPLIANCE,
            intent=intent,
            state=state,
            delta=delta,
            review_method=review_method,
        )
    
    async def engineering_review_iterative(
        self,
        intent: dict[str, Any],
        state: dict[str, Any],
        delta: dict[str, Any],
        engineering_metrics: dict[str, Any] | None = None,
    ) -> ParallelAnalysisResult:
        """
        Perform iterative engineering review using multiple rounds.
        """
        features = get_features()
        
        if not features.enable_iterative_engineering_analysis:
            return await self.engineering_review(intent, state, delta, engineering_metrics)
        
        async def review_method(context: str, metadata: dict[str, Any]) -> LLMCallResult:
            return await self._single_engineering_review(context, metadata, engineering_metrics)
        
        return await self._run_iterative_review(
            analysis_type=AnalysisTypeCategories.ENGINEERING,
            intent=intent,
            state=state,
            delta=delta,
            review_method=review_method,
        )
    
    async def architecture_review_iterative(
        self,
        intent: dict[str, Any],
        state: dict[str, Any],
        delta: dict[str, Any],
    ) -> ParallelAnalysisResult:
        """
        Perform iterative architecture review using multiple rounds.
        """
        features = get_features()
        
        if not features.enable_iterative_architecture_analysis:
            return await self.architecture_review(intent, state, delta)
        
        return await self._run_iterative_review(
            analysis_type=AnalysisTypeCategories.ARCHITECTURE,
            intent=intent,
            state=state,
            delta=delta,
            review_method=self._single_architecture_review,
        )
    
    async def _run_iterative_review(
        self,
        analysis_type: AnalysisTypeCategories,
        intent: dict[str, Any],
        state: dict[str, Any],
        delta: dict[str, Any],
        review_method,
    ) -> ParallelAnalysisResult:
        """
        Run iterative analysis across all providers and merge results.
        """
        features = get_features()
        
        # Build initial context
        initial_context = self._build_review_context(intent, state, delta)
        
        # Get config with max rounds override
        config = get_analysis_config(analysis_type)
        if features.iterative_analysis_max_rounds != config.max_rounds:
            # Create a modified config
            from dataclasses import replace
            config = replace(config, max_rounds=features.iterative_analysis_max_rounds)
        
        # Run iterative analysis for each provider
        async def run_for_provider(provider: LLMProvider):
            async def llm_call_fn(context: str, metadata: dict[str, Any]) -> LLMCallResult:
                # Call the review method for this provider
                response = await review_method(context, metadata)
                return response
            
            analyzer = IterativeAnalyzer(
                analysis_type=analysis_type,
                llm_call_fn=lambda ctx, meta: self._provider_call_wrapper(
                    provider, ctx, meta, analysis_type
                ),
                config_override=config,
                verbose=True,
            )
            return await analyzer.analyze(initial_context)
        
        # Run for all providers in parallel
        tasks = [run_for_provider(provider) for provider in self.providers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Merge iterative results
        return self._merge_iterative_results(results, analysis_type)
    
    async def _provider_call_wrapper(
        self,
        provider: LLMProvider,
        context: str,
        metadata: dict[str, Any],
        analysis_type: AnalysisTypeCategories,
    ) -> LLMCallResult:
        """Wrapper to call a provider and convert response to LLMCallResult."""
        from context_graph.llm.provider import AnalysisRequest, AnalysisType
        
        # Map analysis type categories to provider analysis types
        type_mapping = {
            AnalysisTypeCategories.SECURITY: AnalysisType.SECURITY_REVIEW,
            AnalysisTypeCategories.PRIVACY: AnalysisType.PRIVACY_REVIEW,
            AnalysisTypeCategories.COMPLIANCE: AnalysisType.COMPLIANCE_REVIEW,
            AnalysisTypeCategories.ENGINEERING: AnalysisType.ENGINEERING_REVIEW,
            AnalysisTypeCategories.ARCHITECTURE: AnalysisType.ARCHITECTURE_REVIEW,
            AnalysisTypeCategories.THREAT_MODEL: AnalysisType.THREAT_MODELING,
        }
        
        request = AnalysisRequest(
            analysis_type=type_mapping.get(analysis_type, AnalysisType.SECURITY_REVIEW),
            content=context,
            context=metadata,
        )
        
        try:
            response = await provider.analyze(request)
            return LLMCallResult(
                structured_data=response.structured_data,
                was_truncated=response.was_truncated,
                stop_reason=response.stop_reason,
                latency_ms=response.latency_ms,
                tokens_used=response.tokens_used,
            )
        except Exception as e:
            logger.error(f"Provider {provider.provider_name} failed: {e}")
            return LLMCallResult(
                structured_data={},
                was_truncated=False,
                stop_reason=f"error: {str(e)}",
            )
    
    def _build_review_context(
        self,
        intent: dict[str, Any],
        state: dict[str, Any],
        delta: dict[str, Any],
    ) -> str:
        """Build context string for review."""
        import json
        return f"""## PRD Intent
{json.dumps(intent, indent=2)}

## Current Codebase State
{json.dumps(state, indent=2)}

## Delta (Changes)
{json.dumps(delta, indent=2)}"""
    
    def _merge_iterative_results(
        self,
        results: list[IterativeAnalysisResult | Exception],
        analysis_type: AnalysisTypeCategories,
    ) -> ParallelAnalysisResult:
        """Merge iterative results from multiple providers."""
        parallel_result = ParallelAnalysisResult()
        
        # Collect all findings
        finding_signatures: dict[str, dict[str, Any]] = {}
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Provider {i} failed: {result}")
                continue
            
            if not isinstance(result, IterativeAnalysisResult):
                continue
            
            parallel_result.total_tokens += result.total_tokens
            parallel_result.total_latency_ms = max(
                parallel_result.total_latency_ms, result.total_latency_ms
            )
            
            # Merge findings
            for finding in result.findings:
                sig = self._finding_signature(finding)
                
                if sig in finding_signatures:
                    existing = finding_signatures[sig]
                    existing["providers"] = existing.get("providers", []) + [f"provider_{i}"]
                    existing["confidence"] = min(
                        existing.get("confidence", 0.5) + 0.2,
                        1.0
                    )
                else:
                    finding_signatures[sig] = {
                        **finding,
                        "providers": [f"provider_{i}"],
                    }
            
            # Merge summary from first successful result
            if not parallel_result.merged_findings and result.summary:
                # Store summary in merged_findings temporarily
                pass
        
        # Categorize findings
        for sig, finding in finding_signatures.items():
            if len(finding.get("providers", [])) > 1:
                parallel_result.consensus_items.append(finding)
            else:
                parallel_result.divergent_items.append(finding)
            parallel_result.merged_findings.append(finding)
        
        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        parallel_result.merged_findings.sort(
            key=lambda f: severity_order.get(f.get("severity", "info"), 5)
        )
        
        return parallel_result
    
    # ==================== Single-call review methods for iteration ====================
    
    async def _single_security_review(
        self,
        context: str,
        metadata: dict[str, Any],
    ) -> LLMCallResult:
        """Single security review call for one provider."""
        # This will be called by the iterative analyzer
        # The actual implementation depends on which provider is being used
        pass
    
    async def _single_privacy_review(
        self,
        context: str,
        metadata: dict[str, Any],
    ) -> LLMCallResult:
        """Single privacy review call for one provider."""
        pass
    
    async def _single_compliance_review(
        self,
        context: str,
        metadata: dict[str, Any],
        frameworks: list[str] | None = None,
    ) -> LLMCallResult:
        """Single compliance review call for one provider."""
        pass
    
    async def _single_engineering_review(
        self,
        context: str,
        metadata: dict[str, Any],
        engineering_metrics: dict[str, Any] | None = None,
    ) -> LLMCallResult:
        """Single engineering review call for one provider."""
        pass
    
    async def _single_architecture_review(
        self,
        context: str,
        metadata: dict[str, Any],
    ) -> LLMCallResult:
        """Single architecture review call for one provider."""
        pass

