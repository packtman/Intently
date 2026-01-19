"""
Code Graph - A unified graph representation of codebase structure.

The Code Graph represents:
- Nodes: Code entities (files, classes, functions, variables, endpoints, models)
- Edges: Relationships (imports, calls, references, inheritance, data flow)

This enables powerful queries like:
- "What functions call this endpoint?"
- "What data flows from user input to database?"
- "What would be affected if I change this class?"
- "Show me all unused exports"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterator


class EdgeType(Enum):
    """Types of relationships between code entities."""
    
    # Structural relationships
    IMPORTS = "imports"          # A imports B
    CONTAINS = "contains"        # A contains B (class contains method)
    EXTENDS = "extends"          # A extends B (inheritance)
    IMPLEMENTS = "implements"    # A implements B (interface)
    
    # Call relationships
    CALLS = "calls"              # A calls B
    CALLED_BY = "called_by"      # A is called by B
    
    # Reference relationships
    REFERENCES = "references"    # A references B
    REFERENCED_BY = "referenced_by"
    
    # Data flow relationships
    DATA_FLOWS_TO = "data_flows_to"
    DATA_FLOWS_FROM = "data_flows_from"
    READS = "reads"              # A reads B (variable/field)
    WRITES = "writes"            # A writes B (variable/field)
    
    # Dependency relationships
    DEPENDS_ON = "depends_on"
    DEPENDENCY_OF = "dependency_of"


@dataclass
class CodeNode:
    """
    A node in the code graph representing a code entity.
    
    Can represent:
    - Files/Modules
    - Classes/Interfaces/Types
    - Functions/Methods
    - Variables/Constants
    - API Endpoints
    - Data Models
    """
    
    id: str  # Unique identifier (e.g., "file.ts:ClassName.methodName")
    name: str
    kind: str  # "file", "class", "function", "method", "variable", "endpoint", "model"
    
    # Location
    file_path: Path | None = None
    start_line: int = 0
    end_line: int = 0
    
    # Metadata
    language: str = ""
    is_exported: bool = False
    is_public: bool = True
    is_deprecated: bool = False
    is_test: bool = False
    
    # Type information (from LSP)
    type_annotation: str = ""
    signature: str = ""  # Function signature
    documentation: str = ""
    
    # Cross-functional attributes
    complexity: float = 0.0  # Cyclomatic complexity
    test_coverage: float = 0.0  # 0-1
    reference_count: int = 0  # How many places use this?
    
    # Security attributes
    handles_user_input: bool = False
    handles_sensitive_data: bool = False
    requires_auth: bool = False
    
    # Architecture attributes  
    layer: str = ""  # "controller", "service", "repository", "utility"
    domain: str = ""  # Business domain
    
    # Raw attributes for extensibility
    attributes: dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self) -> int:
        return hash(self.id)
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CodeNode):
            return False
        return self.id == other.id
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "file_path": str(self.file_path) if self.file_path else None,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "language": self.language,
            "is_exported": self.is_exported,
            "is_deprecated": self.is_deprecated,
            "type_annotation": self.type_annotation,
            "signature": self.signature,
            "complexity": self.complexity,
            "reference_count": self.reference_count,
            "handles_user_input": self.handles_user_input,
            "handles_sensitive_data": self.handles_sensitive_data,
            "requires_auth": self.requires_auth,
            "layer": self.layer,
        }


@dataclass
class CodeEdge:
    """
    An edge in the code graph representing a relationship.
    """
    
    source_id: str  # Source node ID
    target_id: str  # Target node ID
    edge_type: EdgeType
    
    # Location of the relationship (e.g., where the import/call happens)
    file_path: Path | None = None
    line: int = 0
    
    # Metadata
    weight: float = 1.0  # For weighted analysis (e.g., call frequency)
    is_direct: bool = True  # Direct vs transitive relationship
    
    # Additional context
    context: str = ""  # e.g., the actual import statement or call expression
    
    def __hash__(self) -> int:
        return hash((self.source_id, self.target_id, self.edge_type))
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "edge_type": self.edge_type.value,
            "file_path": str(self.file_path) if self.file_path else None,
            "line": self.line,
            "weight": self.weight,
            "context": self.context,
        }


class CodeGraph:
    """
    A graph representation of codebase structure.
    
    Enables powerful queries for cross-functional analysis.
    """
    
    def __init__(self) -> None:
        self._nodes: dict[str, CodeNode] = {}
        self._edges: list[CodeEdge] = []
        
        # Indexes for fast lookups
        self._edges_by_source: dict[str, list[CodeEdge]] = {}
        self._edges_by_target: dict[str, list[CodeEdge]] = {}
        self._nodes_by_kind: dict[str, list[CodeNode]] = {}
        self._nodes_by_file: dict[Path, list[CodeNode]] = {}
    
    # ========== Node Operations ==========
    
    def add_node(self, node: CodeNode) -> None:
        """Add a node to the graph."""
        self._nodes[node.id] = node
        
        # Update indexes
        if node.kind not in self._nodes_by_kind:
            self._nodes_by_kind[node.kind] = []
        self._nodes_by_kind[node.kind].append(node)
        
        if node.file_path:
            if node.file_path not in self._nodes_by_file:
                self._nodes_by_file[node.file_path] = []
            self._nodes_by_file[node.file_path].append(node)
    
    def get_node(self, node_id: str) -> CodeNode | None:
        """Get a node by ID."""
        return self._nodes.get(node_id)
    
    def get_nodes(
        self,
        kind: str | None = None,
        file_path: Path | None = None,
        is_exported: bool | None = None,
        layer: str | None = None,
    ) -> list[CodeNode]:
        """Get nodes matching the given criteria."""
        if kind is not None:
            candidates = self._nodes_by_kind.get(kind, [])
        elif file_path is not None:
            candidates = self._nodes_by_file.get(file_path, [])
        else:
            candidates = list(self._nodes.values())
        
        result = []
        for node in candidates:
            if is_exported is not None and node.is_exported != is_exported:
                continue
            if layer is not None and node.layer != layer:
                continue
            if file_path is not None and node.file_path != file_path:
                continue
            result.append(node)
        
        return result
    
    @property
    def nodes(self) -> Iterator[CodeNode]:
        """Iterate over all nodes."""
        return iter(self._nodes.values())
    
    @property
    def node_count(self) -> int:
        return len(self._nodes)
    
    # ========== Edge Operations ==========
    
    def add_edge(self, edge: CodeEdge) -> None:
        """Add an edge to the graph."""
        self._edges.append(edge)
        
        # Update indexes
        if edge.source_id not in self._edges_by_source:
            self._edges_by_source[edge.source_id] = []
        self._edges_by_source[edge.source_id].append(edge)
        
        if edge.target_id not in self._edges_by_target:
            self._edges_by_target[edge.target_id] = []
        self._edges_by_target[edge.target_id].append(edge)
    
    def get_outgoing_edges(
        self,
        node_id: str,
        edge_type: EdgeType | None = None,
    ) -> list[CodeEdge]:
        """Get edges going out from a node."""
        edges = self._edges_by_source.get(node_id, [])
        if edge_type is not None:
            edges = [e for e in edges if e.edge_type == edge_type]
        return edges
    
    def get_incoming_edges(
        self,
        node_id: str,
        edge_type: EdgeType | None = None,
    ) -> list[CodeEdge]:
        """Get edges coming into a node."""
        edges = self._edges_by_target.get(node_id, [])
        if edge_type is not None:
            edges = [e for e in edges if e.edge_type == edge_type]
        return edges
    
    @property
    def edges(self) -> Iterator[CodeEdge]:
        """Iterate over all edges."""
        return iter(self._edges)
    
    @property
    def edge_count(self) -> int:
        return len(self._edges)
    
    # ========== Graph Queries ==========
    
    def get_callers(self, node_id: str) -> list[CodeNode]:
        """Get all nodes that call this node."""
        edges = self.get_incoming_edges(node_id, EdgeType.CALLS)
        return [self._nodes[e.source_id] for e in edges if e.source_id in self._nodes]
    
    def get_callees(self, node_id: str) -> list[CodeNode]:
        """Get all nodes that this node calls."""
        edges = self.get_outgoing_edges(node_id, EdgeType.CALLS)
        return [self._nodes[e.target_id] for e in edges if e.target_id in self._nodes]
    
    def get_references(self, node_id: str) -> list[CodeNode]:
        """Get all nodes that reference this node."""
        edges = self.get_incoming_edges(node_id, EdgeType.REFERENCES)
        return [self._nodes[e.source_id] for e in edges if e.source_id in self._nodes]
    
    def get_dependencies(self, node_id: str) -> list[CodeNode]:
        """Get all nodes that this node depends on."""
        edges = self.get_outgoing_edges(node_id, EdgeType.DEPENDS_ON)
        return [self._nodes[e.target_id] for e in edges if e.target_id in self._nodes]
    
    def get_dependents(self, node_id: str) -> list[CodeNode]:
        """Get all nodes that depend on this node."""
        edges = self.get_incoming_edges(node_id, EdgeType.DEPENDS_ON)
        return [self._nodes[e.source_id] for e in edges if e.source_id in self._nodes]
    
    def get_ancestors(
        self,
        node_id: str,
        edge_types: list[EdgeType] | None = None,
        max_depth: int = 10,
    ) -> list[CodeNode]:
        """Get all ancestor nodes (transitive incoming relationships)."""
        if edge_types is None:
            edge_types = [EdgeType.DEPENDS_ON, EdgeType.IMPORTS, EdgeType.CALLS]
        
        visited = set()
        result = []
        queue = [(node_id, 0)]
        
        while queue:
            current_id, depth = queue.pop(0)
            if current_id in visited or depth > max_depth:
                continue
            visited.add(current_id)
            
            for edge_type in edge_types:
                for edge in self.get_incoming_edges(current_id, edge_type):
                    source_node = self._nodes.get(edge.source_id)
                    if source_node and source_node.id not in visited:
                        result.append(source_node)
                        queue.append((source_node.id, depth + 1))
        
        return result
    
    def get_descendants(
        self,
        node_id: str,
        edge_types: list[EdgeType] | None = None,
        max_depth: int = 10,
    ) -> list[CodeNode]:
        """Get all descendant nodes (transitive outgoing relationships)."""
        if edge_types is None:
            edge_types = [EdgeType.DEPENDS_ON, EdgeType.IMPORTS, EdgeType.CALLS]
        
        visited = set()
        result = []
        queue = [(node_id, 0)]
        
        while queue:
            current_id, depth = queue.pop(0)
            if current_id in visited or depth > max_depth:
                continue
            visited.add(current_id)
            
            for edge_type in edge_types:
                for edge in self.get_outgoing_edges(current_id, edge_type):
                    target_node = self._nodes.get(edge.target_id)
                    if target_node and target_node.id not in visited:
                        result.append(target_node)
                        queue.append((target_node.id, depth + 1))
        
        return result
    
    # ========== Cross-Functional Analysis ==========
    
    def get_impact_analysis(self, node_id: str) -> dict[str, Any]:
        """
        Analyze the impact of changing a node.
        
        Returns information about what would be affected.
        """
        node = self._nodes.get(node_id)
        if not node:
            return {"error": "Node not found"}
        
        # Get all affected nodes
        affected_by_change = self.get_ancestors(node_id, max_depth=5)
        
        # Categorize by type
        affected_tests = [n for n in affected_by_change if n.is_test]
        affected_endpoints = [n for n in affected_by_change if n.kind == "endpoint"]
        affected_files = {n.file_path for n in affected_by_change if n.file_path}
        
        return {
            "node": node.to_dict(),
            "total_affected": len(affected_by_change),
            "affected_files": len(affected_files),
            "affected_tests": len(affected_tests),
            "affected_endpoints": len(affected_endpoints),
            "affected_nodes": [n.to_dict() for n in affected_by_change[:20]],
        }
    
    def get_unused_exports(self) -> list[CodeNode]:
        """Find exported symbols that are never referenced."""
        unused = []
        for node in self._nodes.values():
            if node.is_exported:
                references = self.get_incoming_edges(node.id, EdgeType.REFERENCES)
                if len(references) == 0:
                    unused.append(node)
        return unused
    
    def get_coupling_metrics(self) -> dict[str, Any]:
        """Calculate coupling metrics for the codebase."""
        metrics = {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "avg_dependencies_per_node": 0.0,
            "highly_coupled_nodes": [],
        }
        
        if not self._nodes:
            return metrics
        
        # Calculate dependencies per node
        dep_counts = []
        for node_id in self._nodes:
            deps = len(self.get_outgoing_edges(node_id, EdgeType.DEPENDS_ON))
            deps += len(self.get_outgoing_edges(node_id, EdgeType.IMPORTS))
            dep_counts.append((node_id, deps))
        
        metrics["avg_dependencies_per_node"] = sum(d for _, d in dep_counts) / len(dep_counts)
        
        # Find highly coupled nodes (>2x average)
        threshold = metrics["avg_dependencies_per_node"] * 2
        metrics["highly_coupled_nodes"] = [
            {"id": node_id, "dependencies": deps}
            for node_id, deps in dep_counts
            if deps > threshold
        ][:10]
        
        return metrics
    
    def get_data_flow_paths(
        self,
        from_node_id: str,
        to_node_id: str,
        max_depth: int = 10,
    ) -> list[list[str]]:
        """
        Find all data flow paths between two nodes.
        
        Critical for security analysis (e.g., user input to database).
        """
        paths: list[list[str]] = []
        
        def dfs(current: str, target: str, path: list[str], depth: int) -> None:
            if depth > max_depth:
                return
            if current == target:
                paths.append(path.copy())
                return
            
            # Follow data flow edges
            for edge_type in [EdgeType.CALLS, EdgeType.DATA_FLOWS_TO, EdgeType.WRITES]:
                for edge in self.get_outgoing_edges(current, edge_type):
                    if edge.target_id not in path:
                        path.append(edge.target_id)
                        dfs(edge.target_id, target, path, depth + 1)
                        path.pop()
        
        dfs(from_node_id, to_node_id, [from_node_id], 0)
        return paths
    
    # ========== Serialization ==========
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize the graph to a dictionary."""
        return {
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "edges": [e.to_dict() for e in self._edges],
            "stats": {
                "node_count": len(self._nodes),
                "edge_count": len(self._edges),
                "nodes_by_kind": {k: len(v) for k, v in self._nodes_by_kind.items()},
            },
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CodeGraph:
        """Deserialize a graph from a dictionary."""
        graph = cls()
        
        for node_data in data.get("nodes", []):
            node = CodeNode(
                id=node_data["id"],
                name=node_data["name"],
                kind=node_data["kind"],
                file_path=Path(node_data["file_path"]) if node_data.get("file_path") else None,
                start_line=node_data.get("start_line", 0),
                end_line=node_data.get("end_line", 0),
                language=node_data.get("language", ""),
                is_exported=node_data.get("is_exported", False),
                type_annotation=node_data.get("type_annotation", ""),
                signature=node_data.get("signature", ""),
                complexity=node_data.get("complexity", 0.0),
                reference_count=node_data.get("reference_count", 0),
            )
            graph.add_node(node)
        
        for edge_data in data.get("edges", []):
            edge = CodeEdge(
                source_id=edge_data["source_id"],
                target_id=edge_data["target_id"],
                edge_type=EdgeType(edge_data["edge_type"]),
                file_path=Path(edge_data["file_path"]) if edge_data.get("file_path") else None,
                line=edge_data.get("line", 0),
                weight=edge_data.get("weight", 1.0),
                context=edge_data.get("context", ""),
            )
            graph.add_edge(edge)
        
        return graph
