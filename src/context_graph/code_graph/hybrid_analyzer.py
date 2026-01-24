"""
Hybrid Analyzer - AST for speed, LSP only when needed.

Strategy:
1. AST-first: Fast initial analysis (milliseconds)
2. LSP on-demand: Only when AST can't answer:
   - Cross-file references ("who calls this?")
   - Type resolution ("what type is this?")
   - Call hierarchy ("trace data flow")
   - Diagnostics ("any type errors?")

This gives you 80% instantly and the extra 20% when you ask for it.
"""

from __future__ import annotations

import ast
import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class ASTResult:
    """Result from fast AST analysis."""
    
    file_path: Path
    classes: list[dict[str, Any]] = field(default_factory=list)
    functions: list[dict[str, Any]] = field(default_factory=list)
    imports: list[dict[str, Any]] = field(default_factory=list)
    calls: list[dict[str, Any]] = field(default_factory=list)
    
    # Markers for things AST can't resolve
    unresolved_calls: list[dict[str, Any]] = field(default_factory=list)
    unresolved_types: list[dict[str, Any]] = field(default_factory=list)
    
    @property
    def needs_lsp(self) -> bool:
        """Does this file have unresolved items that need LSP?"""
        return bool(self.unresolved_calls or self.unresolved_types)


@dataclass 
class LSPQuery:
    """A specific query for LSP to answer."""
    
    query_type: str  # "references", "type", "call_hierarchy", "diagnostics"
    file_path: Path
    line: int
    character: int
    symbol_name: str = ""
    context: str = ""


@dataclass
class HybridResult:
    """Combined result from AST + optional LSP."""
    
    # Fast AST results (always available)
    ast_results: dict[str, ASTResult] = field(default_factory=dict)
    
    # LSP results (only when queried)
    lsp_results: dict[str, Any] = field(default_factory=dict)
    
    # Pending queries that need LSP
    pending_queries: list[LSPQuery] = field(default_factory=list)
    
    # Stats
    ast_time_ms: float = 0.0
    lsp_time_ms: float = 0.0
    files_analyzed: int = 0
    lsp_queries_made: int = 0


class HybridAnalyzer:
    """
    Hybrid AST + LSP analyzer.
    
    Usage:
        analyzer = HybridAnalyzer(workspace_path)
        
        # Fast: Get AST results immediately
        result = analyzer.analyze_fast()
        
        # Only when needed: Ask LSP specific questions
        refs = await analyzer.find_references("MyClass", file, line)
        types = await analyzer.get_type_info(file, line, char)
        callers = await analyzer.get_callers("my_function", file, line)
    """
    
    def __init__(self, workspace_path: Path) -> None:
        self.workspace_path = workspace_path
        self._lsp_client = None
        self._lsp_initialized = False
        self._ast_cache: dict[str, ASTResult] = {}
        self._lsp_cache: dict[str, Any] = {}
    
    # ========== FAST: AST Analysis ==========
    
    def analyze_fast(
        self,
        file_paths: list[Path] | None = None,
        languages: list[str] | None = None,
    ) -> HybridResult:
        """
        Fast AST-only analysis. Returns immediately.
        
        This gives you 80% of the information in milliseconds.
        """
        import time
        start = time.time()
        
        result = HybridResult()
        languages = languages or ["python", "typescript", "kotlin"]
        
        # Discover files if not provided
        if file_paths is None:
            file_paths = self._discover_files(languages)
        
        # Analyze each file with AST
        for file_path in file_paths:
            try:
                ast_result = self._analyze_file_ast(file_path)
                if ast_result:
                    rel_path = str(file_path.relative_to(self.workspace_path))
                    result.ast_results[rel_path] = ast_result
                    self._ast_cache[rel_path] = ast_result
                    
                    # Track what needs LSP
                    if ast_result.needs_lsp:
                        for call in ast_result.unresolved_calls:
                            result.pending_queries.append(LSPQuery(
                                query_type="references",
                                file_path=file_path,
                                line=call.get("line", 0),
                                character=call.get("col", 0),
                                symbol_name=call.get("name", ""),
                                context="cross-file call resolution",
                            ))
            except Exception as e:
                logger.debug(f"Failed to analyze {file_path}: {e}")
        
        result.files_analyzed = len(result.ast_results)
        result.ast_time_ms = (time.time() - start) * 1000
        
        return result
    
    def _discover_files(self, languages: list[str]) -> list[Path]:
        """Discover files to analyze."""
        extensions = {
            "python": [".py"],
            "typescript": [".ts", ".tsx", ".js", ".jsx"],
            "kotlin": [".kt", ".kts"],
        }
        
        files = []
        exclude = ["node_modules", "__pycache__", ".git", ".venv", "venv", "dist", "build"]
        
        for lang in languages:
            for ext in extensions.get(lang, []):
                for file_path in self.workspace_path.rglob(f"*{ext}"):
                    if not any(exc in str(file_path) for exc in exclude):
                        files.append(file_path)
        
        return files[:1000]  # Limit
    
    def _analyze_file_ast(self, file_path: Path) -> ASTResult | None:
        """Analyze a single file with AST."""
        suffix = file_path.suffix.lower()
        
        if suffix == ".py":
            return self._analyze_python_ast(file_path)
        elif suffix in [".ts", ".tsx", ".js", ".jsx"]:
            return self._analyze_typescript_regex(file_path)
        elif suffix in [".kt", ".kts"]:
            return self._analyze_kotlin_regex(file_path)
        
        return None
    
    def _analyze_python_ast(self, file_path: Path) -> ASTResult:
        """Analyze Python file with AST."""
        result = ASTResult(file_path=file_path)
        
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)
        except Exception:
            return result
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                result.classes.append({
                    "name": node.name,
                    "line": node.lineno,
                    "end_line": node.end_lineno,
                    "bases": [self._get_name(b) for b in node.bases],
                    "methods": [m.name for m in node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))],
                })
            
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                result.functions.append({
                    "name": node.name,
                    "line": node.lineno,
                    "end_line": node.end_lineno,
                    "args": [a.arg for a in node.args.args],
                    "decorators": [self._get_name(d) for d in node.decorator_list],
                })
            
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    result.imports.append({
                        "module": alias.name,
                        "alias": alias.asname,
                        "line": node.lineno,
                    })
            
            elif isinstance(node, ast.ImportFrom):
                result.imports.append({
                    "module": node.module or "",
                    "names": [a.name for a in node.names],
                    "line": node.lineno,
                })
            
            elif isinstance(node, ast.Call):
                call_info = {
                    "line": node.lineno,
                    "col": node.col_offset,
                }
                
                if isinstance(node.func, ast.Attribute):
                    call_info["name"] = node.func.attr
                    call_info["on"] = "?"  # AST doesn't know the type
                    result.unresolved_calls.append(call_info)  # Mark for LSP
                elif isinstance(node.func, ast.Name):
                    call_info["name"] = node.func.id
                
                result.calls.append(call_info)
        
        return result
    
    def _analyze_typescript_regex(self, file_path: Path) -> ASTResult:
        """Analyze TypeScript with regex (fast fallback)."""
        import re
        result = ASTResult(file_path=file_path)
        
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return result
        
        # Classes
        for match in re.finditer(r'(?:export\s+)?class\s+(\w+)', content):
            line = content[:match.start()].count("\n") + 1
            result.classes.append({"name": match.group(1), "line": line})
        
        # Functions
        for match in re.finditer(r'(?:export\s+)?(?:async\s+)?function\s+(\w+)', content):
            line = content[:match.start()].count("\n") + 1
            result.functions.append({"name": match.group(1), "line": line})
        
        # Arrow functions (const x = () => or const x = async () =>)
        for match in re.finditer(r'(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>', content):
            line = content[:match.start()].count("\n") + 1
            result.functions.append({"name": match.group(1), "line": line})
        
        # Interfaces
        for match in re.finditer(r'(?:export\s+)?interface\s+(\w+)', content):
            line = content[:match.start()].count("\n") + 1
            result.classes.append({"name": match.group(1), "line": line, "kind": "interface"})
        
        # Imports - these are cross-file, mark for LSP
        for match in re.finditer(r'import\s+.*from\s+[\'"]([^\'"]+)[\'"]', content):
            line = content[:match.start()].count("\n") + 1
            result.imports.append({"module": match.group(1), "line": line})
            # Mark as unresolved - we don't know what's actually exported
            result.unresolved_calls.append({
                "name": match.group(1),
                "line": line,
                "context": "import resolution",
            })
        
        return result
    
    def _analyze_kotlin_regex(self, file_path: Path) -> ASTResult:
        """Analyze Kotlin with regex (fast fallback)."""
        import re
        result = ASTResult(file_path=file_path)
        
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return result
        
        # Classes
        for match in re.finditer(r'(?:data\s+)?class\s+(\w+)', content):
            line = content[:match.start()].count("\n") + 1
            result.classes.append({"name": match.group(1), "line": line})
        
        # Functions
        for match in re.finditer(r'(?:suspend\s+)?fun\s+(\w+)', content):
            line = content[:match.start()].count("\n") + 1
            result.functions.append({"name": match.group(1), "line": line})
        
        return result
    
    def _get_name(self, node: ast.expr | None) -> str:
        """Get name from AST node."""
        if node is None:
            return ""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        if isinstance(node, ast.Call):
            return self._get_name(node.func)
        return ""
    
    # ========== SLOW: LSP Queries (on-demand) ==========
    
    async def _ensure_lsp(self) -> bool:
        """Lazily initialize LSP only when needed."""
        if self._lsp_initialized:
            return self._lsp_client is not None
        
        self._lsp_initialized = True
        
        try:
            from context_graph.lsp.client import LSPClient, DEFAULT_SERVER_CONFIGS
            
            # Start Python LSP (most useful for cross-file)
            config = DEFAULT_SERVER_CONFIGS.get("python")
            if config:
                self._lsp_client = LSPClient(config, self.workspace_path)
                await self._lsp_client.start()
                logger.info("LSP initialized on-demand")
                return True
        except Exception as e:
            logger.warning(f"LSP not available: {e}")
        
        return False
    
    async def find_references(
        self,
        symbol_name: str,
        file_path: Path,
        line: int,
        character: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Find all references to a symbol across the codebase.
        
        This is the 20% that AST cannot do - cross-file analysis.
        LSP is started lazily only when this is called.
        """
        cache_key = f"refs:{file_path}:{line}:{character}"
        if cache_key in self._lsp_cache:
            return self._lsp_cache[cache_key]
        
        if not await self._ensure_lsp():
            return []
        
        try:
            refs = await self._lsp_client.find_references(file_path, line, character)
            result = [
                {
                    "file": ref.location.uri.replace("file://", ""),
                    "line": ref.location.start_line + 1,
                    "character": ref.location.start_character,
                }
                for ref in refs
            ]
            self._lsp_cache[cache_key] = result
            return result
        except Exception as e:
            logger.debug(f"LSP find_references failed: {e}")
            return []
    
    async def get_type_info(
        self,
        file_path: Path,
        line: int,
        character: int,
    ) -> str | None:
        """
        Get type information for a position.
        
        AST doesn't know types. LSP does.
        """
        cache_key = f"type:{file_path}:{line}:{character}"
        if cache_key in self._lsp_cache:
            return self._lsp_cache[cache_key]
        
        if not await self._ensure_lsp():
            return None
        
        try:
            hover = await self._lsp_client.get_hover_info(file_path, line, character)
            if hover:
                self._lsp_cache[cache_key] = hover.type_string
                return hover.type_string
        except Exception as e:
            logger.debug(f"LSP hover failed: {e}")
        
        return None
    
    async def get_callers(
        self,
        function_name: str,
        file_path: Path,
        line: int,
        character: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Find all callers of a function (incoming call hierarchy).
        
        AST sees calls in one file. LSP sees calls across files.
        """
        cache_key = f"callers:{file_path}:{line}:{character}"
        if cache_key in self._lsp_cache:
            return self._lsp_cache[cache_key]
        
        if not await self._ensure_lsp():
            return []
        
        try:
            incoming, _ = await self._lsp_client.get_call_hierarchy(file_path, line, character)
            result = [
                {
                    "name": caller.name,
                    "file": caller.location.uri.replace("file://", ""),
                    "line": caller.location.start_line + 1,
                }
                for caller in incoming
            ]
            self._lsp_cache[cache_key] = result
            return result
        except Exception as e:
            logger.debug(f"LSP call hierarchy failed: {e}")
            return []
    
    async def get_callees(
        self,
        function_name: str,
        file_path: Path,
        line: int,
        character: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Find all functions called by a function (outgoing call hierarchy).
        """
        cache_key = f"callees:{file_path}:{line}:{character}"
        if cache_key in self._lsp_cache:
            return self._lsp_cache[cache_key]
        
        if not await self._ensure_lsp():
            return []
        
        try:
            _, outgoing = await self._lsp_client.get_call_hierarchy(file_path, line, character)
            result = [
                {
                    "name": callee.name,
                    "file": callee.location.uri.replace("file://", ""),
                    "line": callee.location.start_line + 1,
                }
                for callee in outgoing
            ]
            self._lsp_cache[cache_key] = result
            return result
        except Exception as e:
            logger.debug(f"LSP call hierarchy failed: {e}")
            return []
    
    async def get_diagnostics(self, file_path: Path | None = None) -> list[dict[str, Any]]:
        """
        Get diagnostics (type errors, unused vars, etc.)
        
        This is pure LSP - AST has no concept of "errors".
        """
        # Use pyright CLI instead of LSP for better reliability
        import subprocess
        import json
        
        try:
            cmd = ["pyright", "--outputjson"]
            if file_path:
                cmd.append(str(file_path))
            else:
                cmd.append(str(self.workspace_path))
            
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            data = json.loads(proc.stdout)
            
            diagnostics = []
            for diag in data.get("generalDiagnostics", []):
                diagnostics.append({
                    "file": diag.get("file", ""),
                    "line": diag.get("range", {}).get("start", {}).get("line", 0) + 1,
                    "severity": ["", "error", "warning", "info"][diag.get("severity", 0)],
                    "message": diag.get("message", ""),
                })
            
            return diagnostics
        except Exception as e:
            logger.debug(f"Diagnostics failed: {e}")
            return []
    
    async def close(self) -> None:
        """Clean up LSP connection if it was started."""
        if self._lsp_client:
            try:
                await self._lsp_client.stop()
            except Exception:
                pass
            self._lsp_client = None


# ========== Convenience Functions ==========

def analyze_fast(workspace_path: Path) -> HybridResult:
    """Quick synchronous analysis using AST only."""
    analyzer = HybridAnalyzer(workspace_path)
    return analyzer.analyze_fast()


async def analyze_with_references(
    workspace_path: Path,
    symbols: list[str] | None = None,
) -> HybridResult:
    """
    Analyze with cross-file references for specific symbols.
    
    If symbols is None, analyzes all exported symbols.
    """
    analyzer = HybridAnalyzer(workspace_path)
    result = analyzer.analyze_fast()
    
    # Find references for requested symbols
    if symbols:
        for rel_path, ast_result in result.ast_results.items():
            file_path = workspace_path / rel_path
            
            for cls in ast_result.classes:
                if cls["name"] in symbols:
                    refs = await analyzer.find_references(
                        cls["name"], file_path, cls["line"] - 1, 0
                    )
                    result.lsp_results[f"{rel_path}:{cls['name']}:refs"] = refs
            
            for func in ast_result.functions:
                if func["name"] in symbols:
                    refs = await analyzer.find_references(
                        func["name"], file_path, func["line"] - 1, 0
                    )
                    result.lsp_results[f"{rel_path}:{func['name']}:refs"] = refs
    
    await analyzer.close()
    return result
