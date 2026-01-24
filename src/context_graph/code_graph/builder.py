"""
Code Graph Builder - Constructs a unified code graph from multiple sources.

Analysis Methods (in order of preference):
1. Python AST - Always used for Python (fast, no dependencies)
2. LSP - OPTIONAL enhancement for TypeScript/Kotlin (when servers installed)
3. Regex fallback - Used when LSP not available

LSP is an OPTIONAL FEATURE that provides richer analysis:
- Cross-file references
- Call hierarchy
- Type information

The system works perfectly well without LSP installed.
"""

from __future__ import annotations

import ast
import asyncio
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from context_graph.code_graph.graph import CodeGraph, CodeNode, CodeEdge, EdgeType

logger = logging.getLogger(__name__)


@dataclass
class BuilderConfig:
    """Configuration for the code graph builder."""
    
    # Which languages to analyze
    languages: list[str] = field(default_factory=lambda: ["python", "typescript", "kotlin"])
    
    # LSP settings
    use_lsp: bool = True
    lsp_timeout_seconds: float = 30.0
    
    # Fallback settings
    use_regex_fallback: bool = True
    
    # Analysis depth
    include_call_hierarchy: bool = True
    include_references: bool = True
    max_reference_depth: int = 3
    
    # Filters
    exclude_patterns: list[str] = field(default_factory=lambda: [
        "node_modules", "__pycache__", ".git", ".venv", "venv",
        "dist", "build", "*.test.*", "*.spec.*",
    ])
    
    # Performance
    max_files: int = 1000
    parallel_files: int = 10
    
    # Tracing/debugging
    trace_enabled: bool = False  # Enable detailed tracing


@dataclass
class AnalysisTrace:
    """Trace information for a single file analysis."""
    file_path: str
    language: str
    method_used: str  # "lsp", "ast", "regex"
    symbols_found: int
    edges_found: int
    duration_ms: float
    error: str = ""


@dataclass
class BuildTrace:
    """Complete trace of a code graph build."""
    started_at: str = ""
    completed_at: str = ""
    total_duration_ms: float = 0.0
    
    # LSP status
    lsp_requested: bool = False
    lsp_initialized: bool = False
    lsp_clients: list[str] = field(default_factory=list)
    
    # File analysis traces
    file_traces: list[AnalysisTrace] = field(default_factory=list)
    
    # Summary by method
    files_by_method: dict[str, int] = field(default_factory=dict)
    symbols_by_method: dict[str, int] = field(default_factory=dict)
    
    # Errors
    errors: list[str] = field(default_factory=list)
    
    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            "=" * 60,
            "BUILD TRACE SUMMARY",
            "=" * 60,
            f"Duration: {self.total_duration_ms:.0f}ms",
            f"LSP requested: {self.lsp_requested}",
            f"LSP initialized: {self.lsp_initialized}",
            f"LSP clients: {', '.join(self.lsp_clients) or 'none'}",
            "",
            "Files analyzed by method:",
        ]
        for method, count in self.files_by_method.items():
            symbols = self.symbols_by_method.get(method, 0)
            lines.append(f"  - {method}: {count} files, {symbols} symbols")
        
        if self.errors:
            lines.append(f"\nErrors ({len(self.errors)}):")
            for err in self.errors[:5]:
                lines.append(f"  - {err}")
        
        lines.append("=" * 60)
        return "\n".join(lines)


class CodeGraphBuilder:
    """
    Builds a unified Code Graph from a codebase.
    
    Usage:
        builder = CodeGraphBuilder(workspace_path)
        graph = await builder.build()
        
        # Or with custom config
        config = BuilderConfig(use_lsp=True, include_call_hierarchy=True)
        graph = await builder.build(config)
        
        # Enable tracing to see what happened
        config = BuilderConfig(trace_enabled=True)
        graph = await builder.build(config)
        print(builder.trace.summary())
    """
    
    def __init__(self, workspace_path: Path) -> None:
        self.workspace_path = workspace_path
        self._graph = CodeGraph()
        self._lsp_manager = None
        self._lsp_available = False
        self.trace = BuildTrace()  # Trace information
    
    async def build(self, config: BuilderConfig | None = None) -> CodeGraph:
        """
        Build the code graph for the workspace.
        
        Returns a fully populated CodeGraph with nodes and edges.
        """
        import time
        from datetime import datetime
        
        config = config or BuilderConfig()
        self._graph = CodeGraph()
        self._config = config  # Store for use in analysis methods
        
        # Initialize trace
        self.trace = BuildTrace()
        self.trace.started_at = datetime.now().isoformat()
        self.trace.lsp_requested = config.use_lsp
        start_time = time.time()
        
        # Try to initialize LSP if enabled
        if config.use_lsp:
            self._lsp_available = await self._init_lsp()
            self.trace.lsp_initialized = self._lsp_available
            if self._lsp_manager and self._lsp_manager._clients:
                self.trace.lsp_clients = list(self._lsp_manager._clients.keys())
        
        try:
            # Discover files
            files = self._discover_files(config)
            logger.info(f"Discovered {len(files)} files to analyze")
            
            # Analyze files - process sequentially when using LSP for stability
            if self._lsp_available:
                # LSP servers can be unstable with parallel requests
                for file_path in files:
                    try:
                        await self._analyze_file(file_path, config)
                    except Exception as e:
                        logger.debug(f"Error analyzing {file_path}: {e}")
                        self.trace.errors.append(f"{file_path}: {e}")
            else:
                # Batch processing for regex-only analysis
                for i in range(0, len(files), config.parallel_files):
                    batch = files[i:i + config.parallel_files]
                    await asyncio.gather(*[
                        self._analyze_file(file_path, config)
                        for file_path in batch
                    ], return_exceptions=True)
            
            # Build cross-file relationships if LSP available
            if self._lsp_available and config.include_references:
                try:
                    await self._build_references(config)
                except Exception as e:
                    logger.warning(f"Failed to build references: {e}")
                    self.trace.errors.append(f"References: {e}")
            
            if self._lsp_available and config.include_call_hierarchy:
                try:
                    await self._build_call_hierarchy(config)
                except Exception as e:
                    logger.warning(f"Failed to build call hierarchy: {e}")
                    self.trace.errors.append(f"Call hierarchy: {e}")
            
            # Calculate derived metrics
            self._calculate_metrics()
            
            # Finalize trace
            self.trace.completed_at = datetime.now().isoformat()
            self.trace.total_duration_ms = (time.time() - start_time) * 1000
            
            # Compute summary stats
            for ft in self.trace.file_traces:
                method = ft.method_used
                self.trace.files_by_method[method] = self.trace.files_by_method.get(method, 0) + 1
                self.trace.symbols_by_method[method] = self.trace.symbols_by_method.get(method, 0) + ft.symbols_found
            
            logger.info(
                f"Code graph built: {self._graph.node_count} nodes, "
                f"{self._graph.edge_count} edges"
            )
            
            # Print trace if enabled
            if config.trace_enabled:
                print(self.trace.summary())
            
            return self._graph
            
        finally:
            # Clean up LSP
            if self._lsp_manager:
                try:
                    await self._lsp_manager.stop()
                except Exception:
                    pass  # Ignore cleanup errors
    
    async def _init_lsp(self) -> bool:
        """Initialize LSP client manager."""
        try:
            from context_graph.lsp import LSPClientManager
            self._lsp_manager = LSPClientManager(self.workspace_path)
            await self._lsp_manager.start()
            # Check if we actually got any clients
            if not self._lsp_manager._clients:
                logger.warning("No LSP clients were started")
                return False
            logger.info(f"LSP initialized with clients: {list(self._lsp_manager._clients.keys())}")
            return True
        except ImportError:
            logger.warning("LSP module not available")
            return False
        except Exception as e:
            logger.warning(f"Failed to initialize LSP: {e}")
            return False
    
    def _discover_files(self, config: BuilderConfig) -> list[Path]:
        """Discover all analyzable files."""
        files = []
        
        extension_map = {
            "python": [".py"],
            "typescript": [".ts", ".tsx", ".js", ".jsx"],
            "kotlin": [".kt", ".kts"],
        }
        
        extensions = []
        for lang in config.languages:
            extensions.extend(extension_map.get(lang, []))
        
        for ext in extensions:
            for file_path in self.workspace_path.rglob(f"*{ext}"):
                if self._should_exclude(file_path, config.exclude_patterns):
                    continue
                files.append(file_path)
                if len(files) >= config.max_files:
                    break
        
        return files[:config.max_files]
    
    def _should_exclude(self, path: Path, patterns: list[str]) -> bool:
        """Check if path should be excluded."""
        path_str = str(path)
        for pattern in patterns:
            if pattern.startswith("*"):
                if path_str.endswith(pattern[1:]):
                    return True
            elif pattern in path_str:
                return True
        return False
    
    def _record_trace(
        self,
        file_path: Path,
        language: str,
        method: str,
        symbols_found: int,
        edges_found: int,
        start_time: float,
        error: str = "",
    ) -> None:
        """Record a trace entry for file analysis."""
        import time
        duration_ms = (time.time() - start_time) * 1000
        
        try:
            rel_path = str(file_path.relative_to(self.workspace_path))
        except ValueError:
            rel_path = str(file_path)
        
        trace = AnalysisTrace(
            file_path=rel_path,
            language=language,
            method_used=method,
            symbols_found=symbols_found,
            edges_found=edges_found,
            duration_ms=duration_ms,
            error=error,
        )
        self.trace.file_traces.append(trace)
    
    async def _analyze_file(self, file_path: Path, config: BuilderConfig) -> None:
        """Analyze a single file and add to graph."""
        suffix = file_path.suffix.lower()
        
        try:
            if suffix == ".py":
                await self._analyze_python_file(file_path, config)
            elif suffix in [".ts", ".tsx", ".js", ".jsx"]:
                await self._analyze_typescript_file(file_path, config)
            elif suffix in [".kt", ".kts"]:
                await self._analyze_kotlin_file(file_path, config)
        except Exception as e:
            logger.warning(f"Failed to analyze {file_path}: {e}")
    
    # ========== Python Analysis (AST-based) ==========
    
    async def _analyze_python_file(self, file_path: Path, config: BuilderConfig) -> None:
        """Analyze a Python file using AST."""
        import time
        start_time = time.time()
        symbols_before = self._graph.node_count
        edges_before = self._graph.edge_count
        
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)
        except Exception as e:
            logger.debug(f"Failed to parse Python file {file_path}: {e}")
            self._record_trace(file_path, "python", "ast", 0, 0, start_time, str(e))
            return
        
        # Add file node
        file_node = CodeNode(
            id=str(file_path.relative_to(self.workspace_path)),
            name=file_path.name,
            kind="file",
            file_path=file_path,
            language="python",
            start_line=1,
            end_line=len(content.split("\n")),
        )
        self._graph.add_node(file_node)
        
        # Walk AST
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                self._add_python_class(node, file_path, file_node.id)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Only top-level functions (not methods)
                if not any(isinstance(p, ast.ClassDef) for p in ast.walk(tree)):
                    self._add_python_function(node, file_path, file_node.id)
            elif isinstance(node, ast.Import):
                self._add_python_import(node, file_path, file_node.id)
            elif isinstance(node, ast.ImportFrom):
                self._add_python_import_from(node, file_path, file_node.id)
        
        # Record trace
        symbols_found = self._graph.node_count - symbols_before
        edges_found = self._graph.edge_count - edges_before
        self._record_trace(file_path, "python", "ast", symbols_found, edges_found, start_time)
    
    def _add_python_class(
        self,
        node: ast.ClassDef,
        file_path: Path,
        parent_id: str,
    ) -> None:
        """Add a Python class to the graph."""
        class_id = f"{parent_id}:{node.name}"
        
        # Check for security-relevant attributes
        handles_sensitive = any(
            base for base in node.bases
            if self._get_ast_name(base) in ["BaseModel", "Model", "User", "Auth"]
        )
        
        class_node = CodeNode(
            id=class_id,
            name=node.name,
            kind="class",
            file_path=file_path,
            language="python",
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            handles_sensitive_data=handles_sensitive,
        )
        self._graph.add_node(class_node)
        
        # Add containment edge
        self._graph.add_edge(CodeEdge(
            source_id=parent_id,
            target_id=class_id,
            edge_type=EdgeType.CONTAINS,
            file_path=file_path,
            line=node.lineno,
        ))
        
        # Add methods
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._add_python_method(item, file_path, class_id)
        
        # Add inheritance edges
        for base in node.bases:
            base_name = self._get_ast_name(base)
            if base_name:
                self._graph.add_edge(CodeEdge(
                    source_id=class_id,
                    target_id=f"external:{base_name}",
                    edge_type=EdgeType.EXTENDS,
                    file_path=file_path,
                    line=node.lineno,
                ))
    
    def _add_python_method(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        file_path: Path,
        class_id: str,
    ) -> None:
        """Add a Python method to the graph."""
        method_id = f"{class_id}.{node.name}"
        
        # Check for route decorators (endpoints)
        is_endpoint = False
        requires_auth = False
        http_method = None
        route_path = None
        
        for decorator in node.decorator_list:
            dec_name = self._get_decorator_name(decorator)
            if dec_name in ["get", "post", "put", "patch", "delete", "route"]:
                is_endpoint = True
                http_method = dec_name.upper()
                # Try to extract path
                if isinstance(decorator, ast.Call) and decorator.args:
                    first_arg = decorator.args[0]
                    if isinstance(first_arg, ast.Constant):
                        route_path = str(first_arg.value)
            elif dec_name in ["login_required", "authenticated", "requires_auth"]:
                requires_auth = True
        
        kind = "endpoint" if is_endpoint else "method"
        
        method_node = CodeNode(
            id=method_id,
            name=node.name,
            kind=kind,
            file_path=file_path,
            language="python",
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            requires_auth=requires_auth,
            handles_user_input=is_endpoint,
            signature=self._get_function_signature(node),
            attributes={
                "http_method": http_method,
                "route_path": route_path,
            } if is_endpoint else {},
        )
        self._graph.add_node(method_node)
        
        # Add containment edge
        self._graph.add_edge(CodeEdge(
            source_id=class_id,
            target_id=method_id,
            edge_type=EdgeType.CONTAINS,
            file_path=file_path,
            line=node.lineno,
        ))
    
    def _add_python_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        file_path: Path,
        parent_id: str,
    ) -> None:
        """Add a top-level Python function."""
        func_id = f"{parent_id}:{node.name}"
        
        func_node = CodeNode(
            id=func_id,
            name=node.name,
            kind="function",
            file_path=file_path,
            language="python",
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            signature=self._get_function_signature(node),
        )
        self._graph.add_node(func_node)
        
        self._graph.add_edge(CodeEdge(
            source_id=parent_id,
            target_id=func_id,
            edge_type=EdgeType.CONTAINS,
            file_path=file_path,
            line=node.lineno,
        ))
    
    def _add_python_import(
        self,
        node: ast.Import,
        file_path: Path,
        file_id: str,
    ) -> None:
        """Add import edges."""
        for alias in node.names:
            self._graph.add_edge(CodeEdge(
                source_id=file_id,
                target_id=f"module:{alias.name}",
                edge_type=EdgeType.IMPORTS,
                file_path=file_path,
                line=node.lineno,
                context=f"import {alias.name}",
            ))
    
    def _add_python_import_from(
        self,
        node: ast.ImportFrom,
        file_path: Path,
        file_id: str,
    ) -> None:
        """Add from-import edges."""
        module = node.module or ""
        for alias in node.names:
            self._graph.add_edge(CodeEdge(
                source_id=file_id,
                target_id=f"module:{module}.{alias.name}",
                edge_type=EdgeType.IMPORTS,
                file_path=file_path,
                line=node.lineno,
                context=f"from {module} import {alias.name}",
            ))
    
    def _get_ast_name(self, node: ast.expr | None) -> str:
        """Get name from AST node."""
        if node is None:
            return ""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return ""
    
    def _get_decorator_name(self, decorator: ast.expr) -> str:
        """Get decorator name."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        if isinstance(decorator, ast.Attribute):
            return decorator.attr
        if isinstance(decorator, ast.Call):
            return self._get_decorator_name(decorator.func)
        return ""
    
    def _get_function_signature(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> str:
        """Build function signature string."""
        args = []
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                try:
                    arg_str += f": {ast.unparse(arg.annotation)}"
                except Exception:
                    pass
            args.append(arg_str)
        
        sig = f"def {node.name}({', '.join(args)})"
        if node.returns:
            try:
                sig += f" -> {ast.unparse(node.returns)}"
            except Exception:
                pass
        
        return sig
    
    # ========== TypeScript Analysis (LSP or Regex) ==========
    
    async def _analyze_typescript_file(
        self,
        file_path: Path,
        config: BuilderConfig,
    ) -> None:
        """Analyze a TypeScript file using LSP or regex fallback."""
        import time
        start_time = time.time()
        symbols_before = self._graph.node_count
        edges_before = self._graph.edge_count
        method_used = "regex"  # Default
        
        # Add file node
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            self._record_trace(file_path, "typescript", "error", 0, 0, start_time, str(e))
            return
        
        file_id = str(file_path.relative_to(self.workspace_path))
        file_node = CodeNode(
            id=file_id,
            name=file_path.name,
            kind="file",
            file_path=file_path,
            language="typescript",
            start_line=1,
            end_line=len(content.split("\n")),
        )
        self._graph.add_node(file_node)
        
        # Try LSP first
        if self._lsp_available and self._lsp_manager:
            try:
                symbols = await self._lsp_manager.get_document_symbols(file_path)
                if symbols:  # Only use LSP result if we got symbols
                    method_used = "lsp"
                    for symbol in symbols:
                        self._add_lsp_symbol(symbol, file_path, file_id)
                    # Record trace and return
                    symbols_found = self._graph.node_count - symbols_before
                    edges_found = self._graph.edge_count - edges_before
                    self._record_trace(file_path, "typescript", method_used, symbols_found, edges_found, start_time)
                    return
            except Exception as e:
                # Mark LSP as unavailable if connection lost
                if "connection" in str(e).lower():
                    self._lsp_available = False
                logger.debug(f"LSP analysis failed for {file_path}, using regex: {e}")
        
        # Regex fallback
        await self._analyze_typescript_regex(content, file_path, file_id)
        
        # Record trace
        symbols_found = self._graph.node_count - symbols_before
        edges_found = self._graph.edge_count - edges_before
        self._record_trace(file_path, "typescript", method_used, symbols_found, edges_found, start_time)
    
    def _add_lsp_symbol(
        self,
        symbol: Any,  # LSP Symbol
        file_path: Path,
        parent_id: str,
    ) -> None:
        """Add an LSP symbol to the graph."""
        from context_graph.lsp.models import SymbolKind
        
        # Map LSP SymbolKind to our node kinds
        kind_map = {
            SymbolKind.CLASS: "class",
            SymbolKind.INTERFACE: "interface",
            SymbolKind.FUNCTION: "function",
            SymbolKind.METHOD: "method",
            SymbolKind.PROPERTY: "property",
            SymbolKind.VARIABLE: "variable",
            SymbolKind.CONSTANT: "constant",
            SymbolKind.ENUM: "enum",
        }
        
        kind = kind_map.get(symbol.kind, "symbol")
        node_id = f"{parent_id}:{symbol.name}"
        
        node = CodeNode(
            id=node_id,
            name=symbol.name,
            kind=kind,
            file_path=file_path,
            language="typescript",
            start_line=symbol.location.start_line,
            end_line=symbol.location.end_line,
            is_exported=symbol.is_exported,
            is_deprecated=symbol.is_deprecated,
            type_annotation=symbol.type_annotation,
            signature=symbol.detail,
            documentation=symbol.documentation,
        )
        self._graph.add_node(node)
        
        # Add containment edge
        self._graph.add_edge(CodeEdge(
            source_id=parent_id,
            target_id=node_id,
            edge_type=EdgeType.CONTAINS,
            file_path=file_path,
            line=symbol.location.start_line,
        ))
        
        # Recursively add children
        for child in symbol.children:
            self._add_lsp_symbol(child, file_path, node_id)
    
    async def _analyze_typescript_regex(
        self,
        content: str,
        file_path: Path,
        file_id: str,
    ) -> None:
        """Analyze TypeScript using regex patterns (fallback)."""
        
        # Classes
        class_pattern = r'(?:export\s+)?class\s+(\w+)'
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            line = content[:match.start()].count("\n") + 1
            
            node = CodeNode(
                id=f"{file_id}:{class_name}",
                name=class_name,
                kind="class",
                file_path=file_path,
                language="typescript",
                start_line=line,
                is_exported="export" in match.group(0),
            )
            self._graph.add_node(node)
            
            self._graph.add_edge(CodeEdge(
                source_id=file_id,
                target_id=node.id,
                edge_type=EdgeType.CONTAINS,
                file_path=file_path,
                line=line,
            ))
        
        # Functions
        func_pattern = r'(?:export\s+)?(?:async\s+)?function\s+(\w+)'
        for match in re.finditer(func_pattern, content):
            func_name = match.group(1)
            line = content[:match.start()].count("\n") + 1
            
            node = CodeNode(
                id=f"{file_id}:{func_name}",
                name=func_name,
                kind="function",
                file_path=file_path,
                language="typescript",
                start_line=line,
                is_exported="export" in match.group(0),
            )
            self._graph.add_node(node)
            
            self._graph.add_edge(CodeEdge(
                source_id=file_id,
                target_id=node.id,
                edge_type=EdgeType.CONTAINS,
                file_path=file_path,
                line=line,
            ))
        
        # Interfaces
        interface_pattern = r'(?:export\s+)?interface\s+(\w+)'
        for match in re.finditer(interface_pattern, content):
            iface_name = match.group(1)
            line = content[:match.start()].count("\n") + 1
            
            node = CodeNode(
                id=f"{file_id}:{iface_name}",
                name=iface_name,
                kind="interface",
                file_path=file_path,
                language="typescript",
                start_line=line,
                is_exported="export" in match.group(0),
            )
            self._graph.add_node(node)
        
        # Imports
        import_pattern = r'import\s+(?:\{[^}]+\}|\*\s+as\s+\w+|\w+)\s+from\s+[\'"]([^\'"]+)[\'"]'
        for match in re.finditer(import_pattern, content):
            module_path = match.group(1)
            line = content[:match.start()].count("\n") + 1
            
            self._graph.add_edge(CodeEdge(
                source_id=file_id,
                target_id=f"module:{module_path}",
                edge_type=EdgeType.IMPORTS,
                file_path=file_path,
                line=line,
                context=match.group(0),
            ))
        
        # Express/NestJS routes
        route_pattern = r'@(Get|Post|Put|Patch|Delete)\s*\(\s*[\'"`]?([^\'")\s]*)[\'"`]?\s*\)'
        for match in re.finditer(route_pattern, content):
            method = match.group(1)
            path = match.group(2)
            line = content[:match.start()].count("\n") + 1
            
            node = CodeNode(
                id=f"{file_id}:endpoint:{method}:{path}",
                name=f"{method} {path}",
                kind="endpoint",
                file_path=file_path,
                language="typescript",
                start_line=line,
                handles_user_input=True,
                attributes={"http_method": method.upper(), "route_path": path},
            )
            self._graph.add_node(node)
    
    # ========== Kotlin Analysis ==========
    
    async def _analyze_kotlin_file(
        self,
        file_path: Path,
        config: BuilderConfig,
    ) -> None:
        """Analyze a Kotlin file using LSP or regex fallback."""
        import time
        start_time = time.time()
        symbols_before = self._graph.node_count
        edges_before = self._graph.edge_count
        method_used = "regex"  # Default
        
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            self._record_trace(file_path, "kotlin", "error", 0, 0, start_time, str(e))
            return
        
        file_id = str(file_path.relative_to(self.workspace_path))
        file_node = CodeNode(
            id=file_id,
            name=file_path.name,
            kind="file",
            file_path=file_path,
            language="kotlin",
            start_line=1,
            end_line=len(content.split("\n")),
        )
        self._graph.add_node(file_node)
        
        # Try LSP first (same as TypeScript)
        if self._lsp_available and self._lsp_manager:
            try:
                symbols = await self._lsp_manager.get_document_symbols(file_path)
                if symbols:
                    method_used = "lsp"
                    for symbol in symbols:
                        self._add_lsp_symbol(symbol, file_path, file_id)
                    symbols_found = self._graph.node_count - symbols_before
                    edges_found = self._graph.edge_count - edges_before
                    self._record_trace(file_path, "kotlin", method_used, symbols_found, edges_found, start_time)
                    return
            except Exception as e:
                logger.debug(f"LSP analysis failed for {file_path}, using regex: {e}")
        
        # Regex fallback for Kotlin
        await self._analyze_kotlin_regex(content, file_path, file_id)
        
        # Record trace
        symbols_found = self._graph.node_count - symbols_before
        edges_found = self._graph.edge_count - edges_before
        self._record_trace(file_path, "kotlin", method_used, symbols_found, edges_found, start_time)
    
    async def _analyze_kotlin_regex(
        self,
        content: str,
        file_path: Path,
        file_id: str,
    ) -> None:
        """Analyze Kotlin using regex patterns (fallback)."""
        
        # Classes
        class_pattern = r'(?:data\s+)?class\s+(\w+)'
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            line = content[:match.start()].count("\n") + 1
            
            node = CodeNode(
                id=f"{file_id}:{class_name}",
                name=class_name,
                kind="class",
                file_path=file_path,
                language="kotlin",
                start_line=line,
            )
            self._graph.add_node(node)
        
        # Functions
        func_pattern = r'(?:suspend\s+)?fun\s+(\w+)'
        for match in re.finditer(func_pattern, content):
            func_name = match.group(1)
            line = content[:match.start()].count("\n") + 1
            
            node = CodeNode(
                id=f"{file_id}:{func_name}",
                name=func_name,
                kind="function",
                file_path=file_path,
                language="kotlin",
                start_line=line,
            )
            self._graph.add_node(node)
    
    # ========== Cross-file Analysis (LSP-powered) ==========
    
    async def _build_references(self, config: BuilderConfig) -> None:
        """Build reference edges using LSP."""
        if not self._lsp_manager:
            return
        
        # For each exported symbol, find references
        for node in self._graph.nodes:
            if node.is_exported and node.kind in ["function", "class", "interface"]:
                try:
                    refs = await self._lsp_manager.find_references(
                        node.file_path,
                        node.start_line - 1,  # LSP uses 0-based lines
                        0,
                    )
                    
                    node.reference_count = len(refs)
                    
                    for ref in refs:
                        ref_file = ref.location.file_path
                        ref_file_id = str(ref_file.relative_to(self.workspace_path))
                        
                        self._graph.add_edge(CodeEdge(
                            source_id=ref_file_id,
                            target_id=node.id,
                            edge_type=EdgeType.REFERENCES,
                            file_path=ref_file,
                            line=ref.location.start_line,
                        ))
                        
                except Exception as e:
                    logger.debug(f"Failed to get references for {node.id}: {e}")
    
    async def _build_call_hierarchy(self, config: BuilderConfig) -> None:
        """Build call hierarchy edges using LSP."""
        if not self._lsp_manager:
            return
        
        # For each function/method, get call hierarchy
        for node in self._graph.nodes:
            if node.kind in ["function", "method", "endpoint"]:
                try:
                    incoming, outgoing = await self._lsp_manager.get_call_hierarchy(
                        node.file_path,
                        node.start_line - 1,
                        0,
                    )
                    
                    # Add incoming call edges (who calls this)
                    for caller in incoming:
                        caller_file = caller.location.file_path
                        try:
                            caller_file_id = str(caller_file.relative_to(self.workspace_path))
                            caller_id = f"{caller_file_id}:{caller.name}"
                        except ValueError:
                            caller_id = f"external:{caller.name}"
                        
                        self._graph.add_edge(CodeEdge(
                            source_id=caller_id,
                            target_id=node.id,
                            edge_type=EdgeType.CALLS,
                            file_path=caller_file,
                            line=caller.call_location.start_line if caller.call_location else 0,
                        ))
                    
                    # Add outgoing call edges (what this calls)
                    for callee in outgoing:
                        callee_file = callee.location.file_path
                        try:
                            callee_file_id = str(callee_file.relative_to(self.workspace_path))
                            callee_id = f"{callee_file_id}:{callee.name}"
                        except ValueError:
                            callee_id = f"external:{callee.name}"
                        
                        self._graph.add_edge(CodeEdge(
                            source_id=node.id,
                            target_id=callee_id,
                            edge_type=EdgeType.CALLS,
                            file_path=node.file_path,
                            line=callee.call_location.start_line if callee.call_location else 0,
                        ))
                        
                except Exception as e:
                    logger.debug(f"Failed to get call hierarchy for {node.id}: {e}")
    
    # ========== Metrics Calculation ==========
    
    def _calculate_metrics(self) -> None:
        """Calculate derived metrics for all nodes."""
        for node in self._graph.nodes:
            # Calculate incoming reference count
            refs = self._graph.get_incoming_edges(node.id, EdgeType.REFERENCES)
            calls = self._graph.get_incoming_edges(node.id, EdgeType.CALLS)
            node.reference_count = len(refs) + len(calls)
            
            # Detect layer based on patterns
            node.layer = self._detect_layer(node)
    
    def _detect_layer(self, node: CodeNode) -> str:
        """Detect architectural layer from node name/attributes."""
        name_lower = node.name.lower()
        
        if node.kind == "endpoint":
            return "controller"
        
        layer_patterns = {
            "controller": ["controller", "handler", "route", "api"],
            "service": ["service", "manager", "provider", "usecase"],
            "repository": ["repository", "repo", "dao", "store", "database"],
            "model": ["model", "entity", "schema", "dto"],
            "utility": ["util", "helper", "utils", "common"],
        }
        
        for layer, patterns in layer_patterns.items():
            for pattern in patterns:
                if pattern in name_lower:
                    return layer
        
        return ""
