"""
Unified Code Graph - Language-agnostic code understanding.

This module provides a unified abstraction over:
- LSP servers (TypeScript, Kotlin, etc.) - OPTIONAL enhancement
- Python AST (always available, fast)
- Regex fallbacks (when LSP unavailable)

The Code Graph enables cross-functional analysis:
- Architecture: Dependency graphs, module boundaries, coupling
- Engineering: Dead code, complexity, type coverage
- Security: Data flow, input validation, authentication paths
- Impact Analysis: What changes affect what

LSP is an OPTIONAL feature that enhances analysis when installed.
The system works well without it.
"""

from context_graph.code_graph.graph import (
    CodeGraph,
    CodeNode,
    CodeEdge,
    EdgeType,
)
from context_graph.code_graph.builder import (
    CodeGraphBuilder,
    BuilderConfig,
    BuildTrace,
    AnalysisTrace,
)
from context_graph.code_graph.hybrid_analyzer import (
    HybridAnalyzer,
    HybridResult,
    ASTResult,
    analyze_fast,
)
from context_graph.code_graph.config import (
    GraphAnalysisConfig,
    LSPConfig,
    load_graph_config,
    check_lsp_availability,
    get_analysis_capabilities,
    print_capabilities_summary,
)

__all__ = [
    # Core graph classes
    "CodeGraph",
    "CodeNode",
    "CodeEdge",
    "EdgeType",
    "CodeGraphBuilder",
    "BuilderConfig",
    # Hybrid analyzer (AST-first, LSP on-demand)
    "HybridAnalyzer",
    "HybridResult",
    "ASTResult",
    "analyze_fast",
    # Tracing
    "BuildTrace",
    "AnalysisTrace",
    # Configuration
    "GraphAnalysisConfig",
    "LSPConfig",
    "load_graph_config",
    "check_lsp_availability",
    "get_analysis_capabilities",
    "print_capabilities_summary",
]
