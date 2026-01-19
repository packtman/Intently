"""
LSP (Language Server Protocol) Integration Module.

Provides LSP client infrastructure for rich code intelligence:
- Document symbols (classes, functions, interfaces)
- References (who uses this symbol?)
- Call hierarchy (data flow analysis)
- Diagnostics (errors, warnings, type issues)
- Go-to-definition (resolve imports)
"""

from context_graph.lsp.client import LSPClient, LSPClientManager
from context_graph.lsp.models import (
    Symbol,
    SymbolKind,
    Reference,
    CallHierarchyItem,
    Diagnostic,
    DiagnosticSeverity,
    Location,
)

__all__ = [
    "LSPClient",
    "LSPClientManager",
    "Symbol",
    "SymbolKind",
    "Reference",
    "CallHierarchyItem",
    "Diagnostic",
    "DiagnosticSeverity",
    "Location",
]
