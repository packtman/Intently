"""
LSP Data Models - Normalized representations of LSP protocol types.

These models provide a language-agnostic interface for code intelligence
that can be used by all analyzers regardless of which LSP server provides the data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class SymbolKind(Enum):
    """Symbol kinds from LSP specification."""
    FILE = 1
    MODULE = 2
    NAMESPACE = 3
    PACKAGE = 4
    CLASS = 5
    METHOD = 6
    PROPERTY = 7
    FIELD = 8
    CONSTRUCTOR = 9
    ENUM = 10
    INTERFACE = 11
    FUNCTION = 12
    VARIABLE = 13
    CONSTANT = 14
    STRING = 15
    NUMBER = 16
    BOOLEAN = 17
    ARRAY = 18
    OBJECT = 19
    KEY = 20
    NULL = 21
    ENUM_MEMBER = 22
    STRUCT = 23
    EVENT = 24
    OPERATOR = 25
    TYPE_PARAMETER = 26


class DiagnosticSeverity(Enum):
    """Diagnostic severities from LSP specification."""
    ERROR = 1
    WARNING = 2
    INFORMATION = 3
    HINT = 4


@dataclass
class Location:
    """A location in a source file."""
    
    uri: str  # File URI or path
    start_line: int
    start_character: int
    end_line: int
    end_character: int
    
    @property
    def file_path(self) -> Path:
        """Get the file path from URI."""
        uri = self.uri
        if uri.startswith("file://"):
            uri = uri[7:]
        return Path(uri)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "uri": self.uri,
            "start_line": self.start_line,
            "start_character": self.start_character,
            "end_line": self.end_line,
            "end_character": self.end_character,
        }


@dataclass
class Symbol:
    """
    A symbol in the codebase (class, function, variable, etc.).
    
    This is the normalized representation used across all language analyzers.
    """
    
    name: str
    kind: SymbolKind
    location: Location
    
    # Optional details
    detail: str = ""  # e.g., type signature
    container_name: str = ""  # Parent symbol name (e.g., class for a method)
    
    # Children (for hierarchical symbols like classes with methods)
    children: list[Symbol] = field(default_factory=list)
    
    # Cross-functional metadata
    is_exported: bool = False  # Public API surface
    is_deprecated: bool = False
    documentation: str = ""
    type_annotation: str = ""  # Type if known
    
    # Analysis metadata
    reference_count: int = 0  # How many places use this?
    complexity_score: float = 0.0  # Cyclomatic complexity if calculable
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind.name,
            "location": self.location.to_dict(),
            "detail": self.detail,
            "container_name": self.container_name,
            "is_exported": self.is_exported,
            "is_deprecated": self.is_deprecated,
            "documentation": self.documentation,
            "type_annotation": self.type_annotation,
            "reference_count": self.reference_count,
            "children": [c.to_dict() for c in self.children],
        }


@dataclass
class Reference:
    """A reference to a symbol (where it's used)."""
    
    location: Location
    symbol_name: str
    
    # Context about the reference
    is_definition: bool = False
    is_declaration: bool = False
    is_write: bool = False  # Assignment vs read
    is_read: bool = True
    
    # The line of code containing the reference
    context_line: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "location": self.location.to_dict(),
            "symbol_name": self.symbol_name,
            "is_definition": self.is_definition,
            "is_declaration": self.is_declaration,
            "is_write": self.is_write,
            "is_read": self.is_read,
            "context_line": self.context_line,
        }


@dataclass
class CallHierarchyItem:
    """
    An item in the call hierarchy (who calls whom).
    
    Critical for data flow analysis and impact assessment.
    """
    
    name: str
    kind: SymbolKind
    location: Location
    
    # The actual call site (where the call happens)
    call_location: Location | None = None
    
    # Direction
    is_incoming: bool = False  # Caller (someone calling this)
    is_outgoing: bool = False  # Callee (this calls something)
    
    # Context
    detail: str = ""  # Function signature
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind.name,
            "location": self.location.to_dict(),
            "call_location": self.call_location.to_dict() if self.call_location else None,
            "is_incoming": self.is_incoming,
            "is_outgoing": self.is_outgoing,
            "detail": self.detail,
        }


@dataclass
class Diagnostic:
    """
    A diagnostic (error, warning, hint) from the language server.
    
    Useful for:
    - Engineering: Type errors, unused code, complexity warnings
    - Security: Potential vulnerabilities detected by linters
    - Architecture: Circular dependencies, import issues
    """
    
    location: Location
    message: str
    severity: DiagnosticSeverity
    
    # Source of the diagnostic
    source: str = ""  # e.g., "typescript", "eslint", "pyright"
    code: str | int = ""  # Error code
    
    # Related information
    related_information: list[dict[str, Any]] = field(default_factory=list)
    
    # Tags
    is_deprecated: bool = False
    is_unnecessary: bool = False  # Dead code
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "location": self.location.to_dict(),
            "message": self.message,
            "severity": self.severity.name,
            "source": self.source,
            "code": self.code,
            "is_deprecated": self.is_deprecated,
            "is_unnecessary": self.is_unnecessary,
        }


@dataclass
class TypeInfo:
    """Type information for a symbol or expression."""
    
    type_string: str  # Human-readable type
    is_nullable: bool = False
    is_any: bool = False  # TypeScript 'any' or equivalent
    is_generic: bool = False
    generic_arguments: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "type_string": self.type_string,
            "is_nullable": self.is_nullable,
            "is_any": self.is_any,
            "is_generic": self.is_generic,
            "generic_arguments": self.generic_arguments,
        }


@dataclass
class ImportInfo:
    """Information about an import statement."""
    
    module_path: str  # What's being imported
    imported_names: list[str]  # Specific names imported
    location: Location
    
    is_default_import: bool = False
    is_namespace_import: bool = False  # import * as X
    is_type_only: bool = False  # TypeScript: import type { X }
    
    # Resolved path (if LSP can resolve it)
    resolved_path: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "module_path": self.module_path,
            "imported_names": self.imported_names,
            "location": self.location.to_dict(),
            "is_default_import": self.is_default_import,
            "is_namespace_import": self.is_namespace_import,
            "is_type_only": self.is_type_only,
            "resolved_path": self.resolved_path,
        }
