"""
Graph-Enhanced Analyzer - Uses the Unified Code Graph for cross-functional analysis.

This analyzer leverages LSP-powered code understanding to provide:
- Richer dependency analysis
- Cross-file impact assessment
- Data flow tracing
- Better endpoint detection
- Type-aware security analysis
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from context_graph.analyzers.codebase_analyzer import FileAnalysis
from context_graph.code_graph import CodeGraph, CodeGraphBuilder, CodeNode, EdgeType
from context_graph.code_graph.builder import BuilderConfig
from context_graph.core.models import (
    State,
    Entity,
    EntityType,
    Relationship,
    RelationshipType,
)

logger = logging.getLogger(__name__)


@dataclass
class GraphAnalysisResult:
    """Result of graph-based code analysis."""
    
    # The unified code graph
    graph: CodeGraph | None = None
    
    # Traditional state (for backward compatibility)
    state: State | None = None
    
    # Enhanced metrics from graph analysis
    metrics: dict[str, Any] = field(default_factory=dict)
    
    # Cross-functional findings
    findings: list[dict[str, Any]] = field(default_factory=list)
    
    # Analysis metadata
    lsp_used: bool = False
    files_analyzed: int = 0
    analysis_time_ms: float = 0.0


class GraphEnhancedAnalyzer:
    """
    Analyzer that uses the Unified Code Graph for deep code understanding.
    
    Provides enhanced analysis capabilities:
    - Cross-file dependency tracking
    - Call hierarchy analysis
    - Data flow tracing
    - Impact assessment
    - Unused code detection
    
    Usage:
        analyzer = GraphEnhancedAnalyzer()
        result = await analyzer.analyze(codebase_path)
        
        # Access the graph
        graph = result.graph
        
        # Or get traditional state for backward compatibility
        state = result.state
    """
    
    def __init__(
        self,
        use_lsp: bool = True,
        include_call_hierarchy: bool = True,
        include_references: bool = True,
    ) -> None:
        self.use_lsp = use_lsp
        self.include_call_hierarchy = include_call_hierarchy
        self.include_references = include_references
    
    async def analyze(
        self,
        codebase_path: Path,
        languages: list[str] | None = None,
    ) -> GraphAnalysisResult:
        """
        Analyze a codebase and build a unified code graph.
        
        Args:
            codebase_path: Path to the codebase root
            languages: Languages to analyze (default: python, typescript, kotlin)
            
        Returns:
            GraphAnalysisResult with graph, state, and findings
        """
        import time
        start_time = time.time()
        
        result = GraphAnalysisResult()
        
        # Configure builder
        config = BuilderConfig(
            languages=languages or ["python", "typescript", "kotlin"],
            use_lsp=self.use_lsp,
            include_call_hierarchy=self.include_call_hierarchy,
            include_references=self.include_references,
        )
        
        # Build the code graph
        builder = CodeGraphBuilder(codebase_path)
        try:
            result.graph = await builder.build(config)
            result.lsp_used = builder._lsp_available
        except Exception as e:
            logger.error(f"Failed to build code graph: {e}")
            result.graph = CodeGraph()
        
        # Convert to traditional State for backward compatibility
        result.state = self._graph_to_state(result.graph, codebase_path)
        
        # Calculate enhanced metrics
        result.metrics = self._calculate_metrics(result.graph)
        
        # Generate cross-functional findings
        result.findings = self._generate_findings(result.graph)
        
        result.files_analyzed = len([n for n in result.graph.nodes if n.kind == "file"])
        result.analysis_time_ms = (time.time() - start_time) * 1000
        
        logger.info(
            f"Graph analysis complete: {result.graph.node_count} nodes, "
            f"{result.graph.edge_count} edges, LSP={result.lsp_used}"
        )
        
        return result
    
    def _graph_to_state(self, graph: CodeGraph, codebase_path: Path) -> State:
        """Convert CodeGraph to traditional State object."""
        state = State(codebase_path=str(codebase_path))
        
        for node in graph.nodes:
            # Convert to entities
            entity_type_map = {
                "endpoint": EntityType.ENDPOINT,
                "class": EntityType.DATA if "model" in node.name.lower() else EntityType.CLASS,
                "function": EntityType.FUNCTION,
                "method": EntityType.FUNCTION,
                "interface": EntityType.DATA,
                "file": EntityType.MODULE,
            }
            
            entity_type = entity_type_map.get(node.kind, EntityType.FUNCTION)
            
            entity = Entity(
                name=node.name,
                entity_type=entity_type,
                description=node.documentation or f"{node.kind} from {node.file_path}",
                source=str(node.file_path) if node.file_path else "",
                is_sensitive=node.handles_sensitive_data,
                requires_auth=node.requires_auth,
            )
            state.entities.append(entity)
            
            # Extract API endpoints
            if node.kind == "endpoint":
                endpoint_info = {
                    "path": node.attributes.get("route_path", node.name),
                    "method": node.attributes.get("http_method", "GET"),
                    "file": str(node.file_path) if node.file_path else "",
                    "line": node.start_line,
                    "requires_auth": node.requires_auth,
                    "function": node.name,
                }
                state.api_endpoints.append(endpoint_info)
            
            # Extract data models
            if node.kind in ["class", "interface"] and node.layer == "model":
                model_info = {
                    "name": node.name,
                    "file": str(node.file_path) if node.file_path else "",
                    "language": node.language,
                    "is_sensitive": node.handles_sensitive_data,
                }
                state.data_models.append(model_info)
            
            # Track auth patterns
            if node.requires_auth:
                state.auth_patterns.append({
                    "type": "decorated",
                    "name": node.name,
                    "file": str(node.file_path) if node.file_path else "",
                    "line": node.start_line,
                })
        
        # Convert edges to relationships
        # Note: We store edge info in a simpler format since Relationship uses UUIDs
        for edge in graph.edges:
            rel_type_map = {
                EdgeType.CALLS: RelationshipType.CALLS,
                EdgeType.IMPORTS: RelationshipType.DEPENDS_ON,
                EdgeType.DEPENDS_ON: RelationshipType.DEPENDS_ON,
                EdgeType.EXTENDS: RelationshipType.DEPENDS_ON,  # Inheritance is a form of dependency
                EdgeType.IMPLEMENTS: RelationshipType.IMPLEMENTS,
                EdgeType.REFERENCES: RelationshipType.ACCESSES,  # References = accesses
                EdgeType.CONTAINS: RelationshipType.CONTAINS,
            }
            
            if edge.edge_type in rel_type_map:
                # Create relationship with properties containing edge info
                relationship = Relationship(
                    relationship_type=rel_type_map[edge.edge_type],
                    properties={
                        "source_name": edge.source_id,
                        "target_name": edge.target_id,
                        "context": edge.context,
                    },
                )
                state.relationships.append(relationship)
        
        # Count lines of code
        for node in graph.nodes:
            if node.kind == "file" and node.end_line > 0:
                state.lines_of_code += node.end_line
                state.files_analyzed += 1
        
        return state
    
    def _calculate_metrics(self, graph: CodeGraph) -> dict[str, Any]:
        """Calculate enhanced metrics from the code graph."""
        metrics = {
            "total_nodes": graph.node_count,
            "total_edges": graph.edge_count,
            "nodes_by_kind": {},
            "nodes_by_language": {},
            "coupling_metrics": {},
            "architecture_metrics": {},
        }
        
        # Count by kind
        kind_counts: dict[str, int] = {}
        lang_counts: dict[str, int] = {}
        layer_counts: dict[str, int] = {}
        
        for node in graph.nodes:
            kind_counts[node.kind] = kind_counts.get(node.kind, 0) + 1
            if node.language:
                lang_counts[node.language] = lang_counts.get(node.language, 0) + 1
            if node.layer:
                layer_counts[node.layer] = layer_counts.get(node.layer, 0) + 1
        
        metrics["nodes_by_kind"] = kind_counts
        metrics["nodes_by_language"] = lang_counts
        metrics["architecture_metrics"]["nodes_by_layer"] = layer_counts
        
        # Coupling metrics
        metrics["coupling_metrics"] = graph.get_coupling_metrics()
        
        # Unused exports
        unused = graph.get_unused_exports()
        metrics["unused_exports_count"] = len(unused)
        metrics["unused_exports"] = [
            {"name": n.name, "file": str(n.file_path), "kind": n.kind}
            for n in unused[:10]  # Limit to 10
        ]
        
        return metrics
    
    def _generate_findings(self, graph: CodeGraph) -> list[dict[str, Any]]:
        """Generate cross-functional findings from the graph."""
        findings = []
        
        # Find highly coupled components
        coupling = graph.get_coupling_metrics()
        for node_info in coupling.get("highly_coupled_nodes", []):
            node = graph.get_node(node_info["id"])
            if node:
                findings.append({
                    "type": "architecture",
                    "category": "high_coupling",
                    "severity": "medium",
                    "title": f"High Coupling: {node.name}",
                    "description": f"{node.name} has {node_info['dependencies']} dependencies, "
                                   f"which is significantly above average.",
                    "file": str(node.file_path) if node.file_path else "",
                    "line": node.start_line,
                    "node_id": node.id,
                })
        
        # Find unused exports (potential dead code)
        unused_exports = graph.get_unused_exports()
        for node in unused_exports[:5]:  # Limit findings
            findings.append({
                "type": "engineering",
                "category": "dead_code",
                "severity": "low",
                "title": f"Unused Export: {node.name}",
                "description": f"Exported symbol '{node.name}' is never referenced in the codebase.",
                "file": str(node.file_path) if node.file_path else "",
                "line": node.start_line,
                "node_id": node.id,
            })
        
        # Find endpoints without auth
        for node in graph.nodes:
            if node.kind == "endpoint" and not node.requires_auth:
                # Check if there's sensitive data flow to this endpoint
                findings.append({
                    "type": "security",
                    "category": "missing_auth",
                    "severity": "high",
                    "title": f"Unauthenticated Endpoint: {node.name}",
                    "description": f"API endpoint '{node.name}' does not require authentication.",
                    "file": str(node.file_path) if node.file_path else "",
                    "line": node.start_line,
                    "node_id": node.id,
                    "http_method": node.attributes.get("http_method"),
                    "route_path": node.attributes.get("route_path"),
                })
        
        # Find functions that handle user input but don't validate
        for node in graph.nodes:
            if node.handles_user_input and node.kind in ["function", "method"]:
                # Check if there are calls to validation functions
                callees = graph.get_callees(node.id)
                has_validation = any(
                    "valid" in c.name.lower() or "sanitiz" in c.name.lower()
                    for c in callees
                )
                
                if not has_validation:
                    findings.append({
                        "type": "security",
                        "category": "missing_validation",
                        "severity": "medium",
                        "title": f"No Input Validation: {node.name}",
                        "description": f"Function '{node.name}' handles user input but has no "
                                       f"apparent validation calls.",
                        "file": str(node.file_path) if node.file_path else "",
                        "line": node.start_line,
                        "node_id": node.id,
                    })
        
        return findings


def analyze_codebase_sync(
    codebase_path: Path,
    use_lsp: bool = True,
) -> GraphAnalysisResult:
    """
    Synchronous wrapper for codebase analysis.
    
    Convenience function for non-async contexts.
    """
    analyzer = GraphEnhancedAnalyzer(use_lsp=use_lsp)
    return asyncio.run(analyzer.analyze(codebase_path))
