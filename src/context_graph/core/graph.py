"""
Context Graph - The central knowledge graph for security analysis.

Uses NetworkX for graph operations with security-focused traversal methods.
"""

from __future__ import annotations

from typing import Any, Iterator
from uuid import UUID

import networkx as nx

from context_graph.core.models import (
    Entity,
    EntityType,
    Relationship,
    RelationshipType,
)


class ContextGraph:
    """
    A directed graph representing security-relevant entities and relationships.
    
    Provides methods for:
    - Building the graph from Intent and State
    - Querying security patterns
    - Finding attack paths
    - Identifying trust boundary crossings
    """
    
    def __init__(self) -> None:
        self._graph: nx.DiGraph = nx.DiGraph()
        self._entities: dict[UUID, Entity] = {}
        self._relationships: dict[UUID, Relationship] = {}
    
    def add_entity(self, entity: Entity) -> None:
        """Add an entity node to the graph."""
        self._entities[entity.id] = entity
        self._graph.add_node(
            entity.id,
            entity=entity,
            name=entity.name,
            type=entity.entity_type.value,
            sensitive=entity.is_sensitive,
            requires_auth=entity.requires_auth,
            trust_level=entity.trust_level,
        )
    
    def add_relationship(self, relationship: Relationship) -> None:
        """Add a relationship edge to the graph."""
        self._relationships[relationship.id] = relationship
        self._graph.add_edge(
            relationship.source_id,
            relationship.target_id,
            relationship=relationship,
            type=relationship.relationship_type.value,
            crosses_boundary=relationship.crosses_trust_boundary,
            requires_encryption=relationship.requires_encryption,
        )
    
    def get_entity(self, entity_id: UUID) -> Entity | None:
        """Get an entity by ID."""
        return self._entities.get(entity_id)
    
    def get_entities_by_type(self, entity_type: EntityType) -> list[Entity]:
        """Get all entities of a specific type."""
        return [e for e in self._entities.values() if e.entity_type == entity_type]
    
    def get_sensitive_entities(self) -> list[Entity]:
        """Get all entities marked as sensitive."""
        return [e for e in self._entities.values() if e.is_sensitive]
    
    def get_relationships_from(self, entity_id: UUID) -> list[Relationship]:
        """Get all relationships originating from an entity."""
        relationships = []
        for _, target, data in self._graph.out_edges(entity_id, data=True):
            if "relationship" in data:
                relationships.append(data["relationship"])
        return relationships
    
    def get_relationships_to(self, entity_id: UUID) -> list[Relationship]:
        """Get all relationships targeting an entity."""
        relationships = []
        for source, _, data in self._graph.in_edges(entity_id, data=True):
            if "relationship" in data:
                relationships.append(data["relationship"])
        return relationships
    
    def find_data_flows(
        self, 
        source_id: UUID, 
        target_id: UUID
    ) -> list[list[UUID]]:
        """
        Find all data flow paths between two entities.
        
        Returns a list of paths, where each path is a list of entity IDs.
        """
        try:
            paths = list(nx.all_simple_paths(self._graph, source_id, target_id))
            return paths
        except nx.NetworkXError:
            return []
    
    def find_trust_boundary_crossings(self) -> list[Relationship]:
        """Find all relationships that cross trust boundaries."""
        crossings = []
        for rel in self._relationships.values():
            if rel.crosses_trust_boundary:
                crossings.append(rel)
                continue
            
            # Check if source and target have different trust levels
            source = self._entities.get(rel.source_id)
            target = self._entities.get(rel.target_id)
            if source and target and source.trust_level != target.trust_level:
                crossings.append(rel)
        
        return crossings
    
    def find_paths_to_sensitive_data(self, start_id: UUID) -> list[list[UUID]]:
        """
        Find all paths from a starting entity to sensitive data.
        
        Useful for identifying potential data exposure risks.
        """
        sensitive_ids = [e.id for e in self.get_sensitive_entities()]
        all_paths: list[list[UUID]] = []
        
        for sensitive_id in sensitive_ids:
            paths = self.find_data_flows(start_id, sensitive_id)
            all_paths.extend(paths)
        
        return all_paths
    
    def find_unauthenticated_paths(self) -> list[tuple[Entity, list[UUID], Entity]]:
        """
        Find paths from unauthenticated entities to sensitive data.
        
        Returns tuples of (start_entity, path, end_entity).
        """
        results = []
        
        # Find entities that don't require auth (potential entry points)
        entry_points = [
            e for e in self._entities.values() 
            if not e.requires_auth and e.entity_type in [
                EntityType.API, EntityType.ENDPOINT
            ]
        ]
        
        sensitive = self.get_sensitive_entities()
        
        for entry in entry_points:
            for sens in sensitive:
                paths = self.find_data_flows(entry.id, sens.id)
                for path in paths:
                    # Check if any entity in path requires auth
                    requires_auth = any(
                        self._entities.get(eid, Entity()).requires_auth 
                        for eid in path[1:-1]  # Exclude start and end
                    )
                    if not requires_auth:
                        results.append((entry, path, sens))
        
        return results
    
    def get_attack_surface(self) -> list[Entity]:
        """
        Get entities that form the attack surface.
        
        These are typically external-facing APIs and endpoints
        with low trust levels.
        """
        return [
            e for e in self._entities.values()
            if e.entity_type in [EntityType.API, EntityType.ENDPOINT]
            and e.trust_level < 5
        ]
    
    def compute_risk_score(self, entity_id: UUID) -> float:
        """
        Compute a risk score for an entity based on:
        - Its sensitivity
        - Number of paths to/from it
        - Trust boundary crossings
        - Auth requirements
        """
        entity = self._entities.get(entity_id)
        if not entity:
            return 0.0
        
        score = 0.0
        
        # Base score from sensitivity
        if entity.is_sensitive:
            score += 30.0
        
        # Score from trust level (lower = riskier)
        score += (10 - entity.trust_level) * 3
        
        # Score from connectivity
        in_degree = self._graph.in_degree(entity_id)
        out_degree = self._graph.out_degree(entity_id)
        score += min(in_degree + out_degree, 20)  # Cap connectivity score
        
        # Score from auth requirements
        if not entity.requires_auth:
            score += 15.0
        
        # Score from boundary crossings
        crossings = sum(
            1 for r in self.get_relationships_to(entity_id)
            if r.crosses_trust_boundary
        )
        score += crossings * 10
        
        return min(score, 100.0)  # Cap at 100
    
    def iter_entities(self) -> Iterator[Entity]:
        """Iterate over all entities."""
        yield from self._entities.values()
    
    def iter_relationships(self) -> Iterator[Relationship]:
        """Iterate over all relationships."""
        yield from self._relationships.values()
    
    def to_dict(self) -> dict[str, Any]:
        """Export graph to dictionary format."""
        return {
            "entities": [
                {
                    "id": str(e.id),
                    "name": e.name,
                    "type": e.entity_type.value,
                    "description": e.description,
                    "sensitive": e.is_sensitive,
                    "requires_auth": e.requires_auth,
                    "trust_level": e.trust_level,
                }
                for e in self._entities.values()
            ],
            "relationships": [
                {
                    "id": str(r.id),
                    "source_id": str(r.source_id),
                    "target_id": str(r.target_id),
                    "type": r.relationship_type.value,
                    "crosses_boundary": r.crosses_trust_boundary,
                }
                for r in self._relationships.values()
            ],
        }
    
    def __len__(self) -> int:
        """Return number of entities in the graph."""
        return len(self._entities)
    
    def __repr__(self) -> str:
        return (
            f"ContextGraph(entities={len(self._entities)}, "
            f"relationships={len(self._relationships)})"
        )

