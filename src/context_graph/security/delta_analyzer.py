"""
Delta Analyzer - Compute the security-relevant difference between Intent and State.

Identifies:
- New attack surface
- Modified security controls
- New data flows
- Trust boundary changes
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from context_graph.core.models import (
    Intent,
    State,
    Delta,
    Entity,
    EntityType,
    Relationship,
    RelationshipType,
)
from context_graph.core.graph import ContextGraph


@dataclass
class DeltaAnalysisResult:
    """Detailed delta analysis result."""
    
    delta: Delta
    
    # Categorized changes
    new_endpoints: list[dict[str, Any]] = field(default_factory=list)
    modified_endpoints: list[dict[str, Any]] = field(default_factory=list)
    new_data_models: list[dict[str, Any]] = field(default_factory=list)
    new_data_flows: list[dict[str, Any]] = field(default_factory=list)
    
    # Security impact
    attack_surface_changes: list[str] = field(default_factory=list)
    trust_boundary_impacts: list[str] = field(default_factory=list)
    auth_requirement_changes: list[str] = field(default_factory=list)
    
    # Risk indicators
    introduces_pii: bool = False
    introduces_external_integration: bool = False
    modifies_auth_flow: bool = False
    expands_attack_surface: bool = False


class DeltaAnalyzer:
    """
    Analyzes the delta between PRD intent and codebase state.
    
    Produces a security-focused diff that highlights:
    - What's new and needs security review
    - What existing controls might be affected
    - Where new risks might be introduced
    """
    
    def __init__(self) -> None:
        self._graph = ContextGraph()
    
    def analyze(self, intent: Intent, state: State) -> DeltaAnalysisResult:
        """
        Compute the delta between intent and state.
        
        Args:
            intent: Extracted intent from PRD
            state: Current codebase state
            
        Returns:
            DeltaAnalysisResult with detailed analysis
        """
        delta = Delta(
            intent_id=intent.id,
            state_id=state.id,
        )
        
        result = DeltaAnalysisResult(delta=delta)
        
        # Analyze API changes
        self._analyze_api_delta(intent, state, result)
        
        # Analyze data model changes
        self._analyze_data_delta(intent, state, result)
        
        # Analyze auth changes
        self._analyze_auth_delta(intent, state, result)
        
        # Analyze external integrations
        self._analyze_integration_delta(intent, state, result)
        
        # Compute overall risk indicators
        self._compute_risk_indicators(result)
        
        # Build delta summary
        delta.summary = self._build_summary(result)
        delta.risk_score = self._compute_risk_score(result)
        
        return result
    
    def _analyze_api_delta(
        self, 
        intent: Intent, 
        state: State, 
        result: DeltaAnalysisResult
    ) -> None:
        """Analyze differences in API endpoints."""
        # Get existing endpoints
        existing_paths = {
            ep.get("path", ""): ep 
            for ep in state.api_endpoints
        }
        
        # Check PRD API changes against existing
        for api_change in intent.api_changes:
            path = api_change.get("path", "")
            
            if path in existing_paths:
                # Modification to existing endpoint
                existing = existing_paths[path]
                changes = self._compute_endpoint_changes(existing, api_change)
                if changes:
                    result.modified_endpoints.append({
                        "path": path,
                        "changes": changes,
                        "existing": existing,
                        "proposed": api_change,
                    })
                    result.attack_surface_changes.append(
                        f"Modified endpoint: {path}"
                    )
            else:
                # New endpoint
                result.new_endpoints.append(api_change)
                result.delta.new_entities.append(Entity(
                    name=path,
                    entity_type=EntityType.ENDPOINT,
                    description=api_change.get("description", "New endpoint from PRD"),
                    source="prd",
                    requires_auth=api_change.get("auth_required", False),
                ))
                result.attack_surface_changes.append(
                    f"New endpoint: {api_change.get('method', 'ANY')} {path}"
                )
        
        # Check for endpoints mentioned in features but not explicitly defined
        for feature in intent.features:
            feature_lower = feature.lower()
            if "api" in feature_lower or "endpoint" in feature_lower:
                # Extract potential path patterns
                path_match = self._extract_path_from_text(feature)
                if path_match and path_match not in existing_paths:
                    result.new_endpoints.append({
                        "path": path_match,
                        "source": "feature_mention",
                        "description": feature,
                    })
    
    def _analyze_data_delta(
        self, 
        intent: Intent, 
        state: State, 
        result: DeltaAnalysisResult
    ) -> None:
        """Analyze differences in data models."""
        # Get existing data models
        existing_models = {
            dm.get("name", "").lower(): dm 
            for dm in state.data_models
        }
        
        # Check PRD entities against existing
        for entity in intent.data_entities:
            name_lower = entity.name.lower()
            
            if name_lower not in existing_models:
                result.new_data_models.append({
                    "name": entity.name,
                    "type": entity.entity_type.value,
                    "is_sensitive": entity.is_sensitive,
                    "description": entity.description,
                })
                result.delta.new_entities.append(entity)
                
                if entity.is_sensitive:
                    result.introduces_pii = True
                    result.attack_surface_changes.append(
                        f"New sensitive data: {entity.name}"
                    )
        
        # Infer data flows from features and user stories
        for feature in intent.features + intent.user_stories:
            flows = self._infer_data_flows(feature, intent.data_entities)
            result.new_data_flows.extend(flows)
    
    def _analyze_auth_delta(
        self, 
        intent: Intent, 
        state: State, 
        result: DeltaAnalysisResult
    ) -> None:
        """Analyze authentication/authorization changes."""
        existing_auth_types = set(
            ap.get("type", "") for ap in state.auth_patterns
        )
        
        # Check PRD auth requirements
        for req in intent.auth_requirements:
            req_lower = req.lower()
            
            # Check for new auth mechanisms
            if "oauth" in req_lower and "oauth" not in str(existing_auth_types).lower():
                result.auth_requirement_changes.append("New: OAuth integration required")
                result.modifies_auth_flow = True
            
            if "mfa" in req_lower or "2fa" in req_lower:
                if "mfa" not in str(state.existing_controls).lower():
                    result.auth_requirement_changes.append("New: MFA requirement")
                    result.modifies_auth_flow = True
            
            if "sso" in req_lower:
                if "sso" not in str(state.existing_controls).lower():
                    result.auth_requirement_changes.append("New: SSO integration")
                    result.modifies_auth_flow = True
            
            # Check for role/permission changes
            if "role" in req_lower or "permission" in req_lower:
                result.auth_requirement_changes.append(f"Auth change: {req[:100]}")
    
    def _analyze_integration_delta(
        self, 
        intent: Intent, 
        state: State, 
        result: DeltaAnalysisResult
    ) -> None:
        """Analyze external integration changes."""
        for integration in intent.external_integrations:
            integration_lower = integration.lower()
            
            # Check for new third-party services
            known_services = [
                "stripe", "paypal", "twilio", "sendgrid", "aws", 
                "gcp", "azure", "firebase", "auth0", "okta"
            ]
            
            for service in known_services:
                if service in integration_lower:
                    result.introduces_external_integration = True
                    result.trust_boundary_impacts.append(
                        f"New external integration: {service}"
                    )
                    result.delta.new_trust_boundaries.append(
                        f"trust_boundary:{service}"
                    )
    
    def _compute_endpoint_changes(
        self, 
        existing: dict[str, Any], 
        proposed: dict[str, Any]
    ) -> list[str]:
        """Compute changes between existing and proposed endpoint."""
        changes = []
        
        # Check method changes
        existing_methods = existing.get("methods", [existing.get("method")])
        proposed_methods = proposed.get("methods", [proposed.get("method")])
        
        if set(existing_methods) != set(proposed_methods):
            changes.append(f"Methods: {existing_methods} -> {proposed_methods}")
        
        # Check auth changes
        existing_auth = existing.get("requires_auth", False)
        proposed_auth = proposed.get("auth_required", False)
        
        if existing_auth != proposed_auth:
            changes.append(f"Auth required: {existing_auth} -> {proposed_auth}")
        
        return changes
    
    def _extract_path_from_text(self, text: str) -> str | None:
        """Extract API path pattern from text."""
        import re
        
        # Look for path-like patterns
        path_pattern = r'/[a-z][a-z0-9/_-]*(?:\{[^}]+\})?(?:/[a-z0-9/_-]*)*'
        match = re.search(path_pattern, text.lower())
        
        return match.group(0) if match else None
    
    def _infer_data_flows(
        self, 
        text: str, 
        entities: list[Entity]
    ) -> list[dict[str, Any]]:
        """Infer data flows from text descriptions."""
        flows = []
        text_lower = text.lower()
        
        # Look for flow indicators
        flow_patterns = [
            (r'(\w+)\s+(?:sends?|writes?|stores?)\s+(?:to\s+)?(\w+)', 'write'),
            (r'(\w+)\s+(?:reads?|gets?|retrieves?)\s+(?:from\s+)?(\w+)', 'read'),
            (r'(\w+)\s+(?:access|view)s?\s+(\w+)', 'access'),
        ]
        
        import re
        for pattern, flow_type in flow_patterns:
            for match in re.finditer(pattern, text_lower):
                source, target = match.groups()
                
                # Check if entities are mentioned
                source_entity = next(
                    (e for e in entities if source in e.name.lower()), 
                    None
                )
                target_entity = next(
                    (e for e in entities if target in e.name.lower()), 
                    None
                )
                
                if source_entity or target_entity:
                    flows.append({
                        "source": source,
                        "target": target,
                        "type": flow_type,
                        "context": text[:100],
                    })
        
        return flows
    
    def _compute_risk_indicators(self, result: DeltaAnalysisResult) -> None:
        """Compute overall risk indicators."""
        # Check if attack surface is expanding
        result.expands_attack_surface = bool(
            result.new_endpoints or 
            result.new_data_models or
            result.introduces_external_integration
        )
    
    def _build_summary(self, result: DeltaAnalysisResult) -> str:
        """Build human-readable delta summary."""
        parts = []
        
        if result.new_endpoints:
            parts.append(f"{len(result.new_endpoints)} new endpoint(s)")
        
        if result.modified_endpoints:
            parts.append(f"{len(result.modified_endpoints)} modified endpoint(s)")
        
        if result.new_data_models:
            parts.append(f"{len(result.new_data_models)} new data model(s)")
        
        if result.introduces_pii:
            parts.append("introduces PII handling")
        
        if result.introduces_external_integration:
            parts.append("adds external integrations")
        
        if result.modifies_auth_flow:
            parts.append("modifies authentication flow")
        
        return "; ".join(parts) if parts else "No significant security-relevant changes detected"
    
    def _compute_risk_score(self, result: DeltaAnalysisResult) -> float:
        """Compute overall risk score (0-100)."""
        score = 0.0
        
        # New endpoints add risk
        score += len(result.new_endpoints) * 10
        
        # Modified endpoints add less risk
        score += len(result.modified_endpoints) * 5
        
        # New data models add risk
        score += len(result.new_data_models) * 8
        
        # PII handling adds significant risk
        if result.introduces_pii:
            score += 20
        
        # External integrations add risk
        if result.introduces_external_integration:
            score += 15
        
        # Auth changes are high risk
        if result.modifies_auth_flow:
            score += 25
        
        return min(score, 100.0)

