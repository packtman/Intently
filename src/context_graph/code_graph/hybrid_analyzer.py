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
    
    def _discover_files(self, languages: list[str] | None = None) -> list[Path]:
        """Discover source files to analyze. If languages is None, discover all supported types."""
        all_extensions = {
            "python": [".py"],
            "typescript": [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"],
            "kotlin": [".kt", ".kts"],
            "go": [".go"],
            "java": [".java"],
            "ruby": [".rb"],
            "php": [".php"],
            "rust": [".rs"],
            "c": [".c", ".h"],
            "cpp": [".cpp", ".cc", ".cxx", ".hpp", ".hxx"],
            "csharp": [".cs"],
            "swift": [".swift"],
            "dart": [".dart"],
        }
        
        if languages is None:
            exts_to_scan = [ext for exts in all_extensions.values() for ext in exts]
        else:
            exts_to_scan = [ext for lang in languages for ext in all_extensions.get(lang, [])]
        
        files = []
        exclude_dirs = {
            "node_modules", "__pycache__", ".git", ".venv", "venv",
            "dist", "build", ".next", ".nuxt", "target", "vendor",
            ".tox", "egg-info", ".eggs", "coverage", ".mypy_cache",
        }
        
        for file_path in self.workspace_path.rglob("*"):
            if not file_path.is_file():
                continue
            if any(part in exclude_dirs for part in file_path.parts):
                continue
            if file_path.suffix.lower() in exts_to_scan:
                files.append(file_path)
        
        return files[:2000]
    
    def _analyze_file_ast(self, file_path: Path) -> ASTResult | None:
        """Analyze a single file with AST or regex depending on language."""
        suffix = file_path.suffix.lower()
        
        if suffix == ".py":
            return self._analyze_python_ast(file_path)
        elif suffix in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"):
            return self._analyze_typescript_regex(file_path)
        elif suffix in (".kt", ".kts"):
            return self._analyze_kotlin_regex(file_path)
        elif suffix == ".go":
            return self._analyze_go_regex(file_path)
        elif suffix == ".java":
            return self._analyze_java_regex(file_path)
        elif suffix == ".rb":
            return self._analyze_ruby_regex(file_path)
        elif suffix == ".rs":
            return self._analyze_rust_regex(file_path)
        elif suffix == ".php":
            return self._analyze_php_regex(file_path)
        elif suffix in (".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".hxx"):
            return self._analyze_c_regex(file_path)
        elif suffix == ".cs":
            return self._analyze_csharp_regex(file_path)
        elif suffix == ".swift":
            return self._analyze_swift_regex(file_path)
        elif suffix == ".dart":
            return self._analyze_dart_regex(file_path)
        
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
        """Analyze TypeScript/JavaScript with regex patterns."""
        import re
        result = ASTResult(file_path=file_path)
        
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return result
        
        seen_names: set[str] = set()
        
        def _line(pos: int) -> int:
            return content[:pos].count("\n") + 1
        
        # Classes
        for m in re.finditer(r'(?:export\s+)?(?:default\s+)?(?:abstract\s+)?class\s+(\w+)', content):
            name = m.group(1)
            if name not in seen_names:
                seen_names.add(name)
                result.classes.append({"name": name, "line": _line(m.start()), "kind": "class"})
        
        # Interfaces
        for m in re.finditer(r'(?:export\s+)?interface\s+(\w+)', content):
            name = m.group(1)
            if name not in seen_names:
                seen_names.add(name)
                result.classes.append({"name": name, "line": _line(m.start()), "kind": "interface"})
        
        # Type aliases
        for m in re.finditer(r'(?:export\s+)?type\s+(\w+)\s*[=<]', content):
            name = m.group(1)
            if name not in seen_names:
                seen_names.add(name)
                result.classes.append({"name": name, "line": _line(m.start()), "kind": "type"})
        
        # Enums
        for m in re.finditer(r'(?:export\s+)?(?:const\s+)?enum\s+(\w+)', content):
            name = m.group(1)
            if name not in seen_names:
                seen_names.add(name)
                result.classes.append({"name": name, "line": _line(m.start()), "kind": "enum"})
        
        # Named function declarations
        for m in re.finditer(r'(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+(\w+)', content):
            name = m.group(1)
            decorators = self._detect_ts_route_markers(content, m.start(), name)
            if name not in seen_names:
                seen_names.add(name)
                result.functions.append({"name": name, "line": _line(m.start()), "decorators": decorators})
        
        # Arrow functions assigned to const/let/var
        for m in re.finditer(r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*(?::\s*[^=]+)?\s*=\s*(?:async\s*)?\(?', content):
            name = m.group(1)
            remaining = content[m.end():m.end() + 200]
            if re.match(r'[^)]*\)\s*(?::\s*[^=]+)?\s*=>', remaining) or '=>' in remaining[:100]:
                decorators = self._detect_ts_route_markers(content, m.start(), name)
                if name not in seen_names:
                    seen_names.add(name)
                    result.functions.append({"name": name, "line": _line(m.start()), "decorators": decorators})
        
        # Express/Hono/Koa route patterns: app.get('/path', ...), router.post('/path', ...)
        for m in re.finditer(
            r'(?:app|router|server)\.(get|post|put|delete|patch|all|use)\s*\(\s*[\'"]([^\'"]+)[\'"]',
            content,
        ):
            method = m.group(1).upper()
            route_path = m.group(2)
            route_name = f"{method} {route_path}"
            if route_name not in seen_names:
                seen_names.add(route_name)
                result.functions.append({
                    "name": route_name,
                    "line": _line(m.start()),
                    "decorators": [method.lower()],
                    "route_path": route_path,
                })
        
        # Next.js App Router: export async function GET/POST/PUT/DELETE/PATCH
        for m in re.finditer(r'export\s+(?:async\s+)?function\s+(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\b', content):
            method = m.group(1)
            route_name = f"Next.js {method} handler"
            rel = str(file_path.relative_to(self.workspace_path)) if file_path.is_relative_to(self.workspace_path) else str(file_path)
            if route_name not in seen_names:
                seen_names.add(route_name)
                result.functions.append({
                    "name": route_name,
                    "line": _line(m.start()),
                    "decorators": [method.lower()],
                    "route_path": rel,
                })
        
        # Imports
        for m in re.finditer(r'import\s+.*?from\s+[\'"]([^\'"]+)[\'"]', content):
            result.imports.append({"module": m.group(1), "line": _line(m.start())})
        
        return result
    
    @staticmethod
    def _detect_ts_route_markers(content: str, pos: int, name: str) -> list[str]:
        """Detect if a TS/JS function is a route handler by checking decorators or context."""
        markers: list[str] = []
        # Check for NestJS-style decorators above the function
        preceding = content[max(0, pos - 300):pos]
        import re
        for m in re.finditer(r'@(Get|Post|Put|Delete|Patch|Controller|Injectable|Module)\b', preceding):
            markers.append(m.group(1).lower())
        # Check if function name itself is a HTTP method (Next.js App Router)
        if name.upper() in ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"):
            markers.append(name.lower())
        return markers
    
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
    
    def _analyze_go_regex(self, file_path: Path) -> ASTResult:
        """Analyze Go source files."""
        import re
        result = ASTResult(file_path=file_path)
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return result
        
        def _line(pos: int) -> int:
            return content[:pos].count("\n") + 1
        
        for m in re.finditer(r'type\s+(\w+)\s+struct\b', content):
            result.classes.append({"name": m.group(1), "line": _line(m.start()), "kind": "struct"})
        for m in re.finditer(r'type\s+(\w+)\s+interface\b', content):
            result.classes.append({"name": m.group(1), "line": _line(m.start()), "kind": "interface"})
        for m in re.finditer(r'func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\(', content):
            result.functions.append({"name": m.group(1), "line": _line(m.start())})
        # Gin/Echo/Chi route patterns
        for m in re.finditer(r'\.(GET|POST|PUT|DELETE|PATCH|Handle|HandleFunc)\s*\(\s*[\'"]([^\'"]+)[\'"]', content):
            method = m.group(1).upper()
            result.functions.append({
                "name": f"{method} {m.group(2)}",
                "line": _line(m.start()),
                "decorators": [method.lower()],
                "route_path": m.group(2),
            })
        return result
    
    def _analyze_java_regex(self, file_path: Path) -> ASTResult:
        """Analyze Java source files."""
        import re
        result = ASTResult(file_path=file_path)
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return result
        
        def _line(pos: int) -> int:
            return content[:pos].count("\n") + 1
        
        for m in re.finditer(r'(?:public|private|protected)?\s*(?:abstract\s+)?(?:class|record)\s+(\w+)', content):
            result.classes.append({"name": m.group(1), "line": _line(m.start())})
        for m in re.finditer(r'(?:public|private|protected)?\s*interface\s+(\w+)', content):
            result.classes.append({"name": m.group(1), "line": _line(m.start()), "kind": "interface"})
        for m in re.finditer(r'(?:public|private|protected)\s+(?:static\s+)?(?:[\w<>\[\],\s]+)\s+(\w+)\s*\(', content):
            name = m.group(1)
            if name not in ("if", "for", "while", "switch", "catch", "class", "new"):
                decorators: list[str] = []
                preceding = content[max(0, m.start() - 200):m.start()]
                for dm in re.finditer(r'@(GetMapping|PostMapping|PutMapping|DeleteMapping|RequestMapping|GET|POST|PUT|DELETE)\b', preceding):
                    decorators.append(dm.group(1).lower().replace("mapping", ""))
                result.functions.append({"name": name, "line": _line(m.start()), "decorators": decorators})
        return result
    
    def _analyze_ruby_regex(self, file_path: Path) -> ASTResult:
        """Analyze Ruby source files."""
        import re
        result = ASTResult(file_path=file_path)
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return result
        
        def _line(pos: int) -> int:
            return content[:pos].count("\n") + 1
        
        for m in re.finditer(r'class\s+(\w+)', content):
            result.classes.append({"name": m.group(1), "line": _line(m.start())})
        for m in re.finditer(r'module\s+(\w+)', content):
            result.classes.append({"name": m.group(1), "line": _line(m.start()), "kind": "module"})
        for m in re.finditer(r'def\s+(\w+[?!]?)', content):
            result.functions.append({"name": m.group(1), "line": _line(m.start())})
        # Rails routes
        for m in re.finditer(r'(get|post|put|patch|delete)\s+[\'"]([^\'"]+)[\'"]', content):
            result.functions.append({
                "name": f"{m.group(1).upper()} {m.group(2)}",
                "line": _line(m.start()),
                "decorators": [m.group(1)],
                "route_path": m.group(2),
            })
        return result
    
    def _analyze_rust_regex(self, file_path: Path) -> ASTResult:
        """Analyze Rust source files."""
        import re
        result = ASTResult(file_path=file_path)
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return result
        
        def _line(pos: int) -> int:
            return content[:pos].count("\n") + 1
        
        for m in re.finditer(r'(?:pub\s+)?struct\s+(\w+)', content):
            result.classes.append({"name": m.group(1), "line": _line(m.start()), "kind": "struct"})
        for m in re.finditer(r'(?:pub\s+)?enum\s+(\w+)', content):
            result.classes.append({"name": m.group(1), "line": _line(m.start()), "kind": "enum"})
        for m in re.finditer(r'(?:pub\s+)?trait\s+(\w+)', content):
            result.classes.append({"name": m.group(1), "line": _line(m.start()), "kind": "trait"})
        for m in re.finditer(r'(?:pub\s+)?(?:async\s+)?fn\s+(\w+)', content):
            decorators: list[str] = []
            preceding = content[max(0, m.start() - 200):m.start()]
            for dm in re.finditer(r'#\[(get|post|put|delete|patch)\s*\(', preceding):
                decorators.append(dm.group(1))
            result.functions.append({"name": m.group(1), "line": _line(m.start()), "decorators": decorators})
        return result
    
    def _analyze_php_regex(self, file_path: Path) -> ASTResult:
        """Analyze PHP source files."""
        import re
        result = ASTResult(file_path=file_path)
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return result
        
        def _line(pos: int) -> int:
            return content[:pos].count("\n") + 1
        
        for m in re.finditer(r'(?:abstract\s+)?class\s+(\w+)', content):
            result.classes.append({"name": m.group(1), "line": _line(m.start())})
        for m in re.finditer(r'interface\s+(\w+)', content):
            result.classes.append({"name": m.group(1), "line": _line(m.start()), "kind": "interface"})
        for m in re.finditer(r'(?:public|private|protected|static|\s)+function\s+(\w+)', content):
            result.functions.append({"name": m.group(1), "line": _line(m.start())})
        for m in re.finditer(r'function\s+(\w+)\s*\(', content):
            result.functions.append({"name": m.group(1), "line": _line(m.start())})
        # Laravel routes
        for m in re.finditer(r'Route::(get|post|put|patch|delete)\s*\(\s*[\'"]([^\'"]+)[\'"]', content):
            result.functions.append({
                "name": f"{m.group(1).upper()} {m.group(2)}",
                "line": _line(m.start()),
                "decorators": [m.group(1)],
                "route_path": m.group(2),
            })
        return result
    
    def _analyze_c_regex(self, file_path: Path) -> ASTResult:
        """Analyze C/C++ source files."""
        import re
        result = ASTResult(file_path=file_path)
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return result
        
        def _line(pos: int) -> int:
            return content[:pos].count("\n") + 1
        
        for m in re.finditer(r'(?:class|struct)\s+(\w+)', content):
            result.classes.append({"name": m.group(1), "line": _line(m.start())})
        for m in re.finditer(r'(?:[\w*&:<>]+\s+)+(\w+)\s*\([^)]*\)\s*(?:const\s*)?(?:override\s*)?(?:noexcept\s*)?{', content):
            name = m.group(1)
            if name not in ("if", "for", "while", "switch", "catch", "return"):
                result.functions.append({"name": name, "line": _line(m.start())})
        return result
    
    def _analyze_csharp_regex(self, file_path: Path) -> ASTResult:
        """Analyze C# source files."""
        import re
        result = ASTResult(file_path=file_path)
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return result
        
        def _line(pos: int) -> int:
            return content[:pos].count("\n") + 1
        
        for m in re.finditer(r'(?:public|internal|private|protected)?\s*(?:abstract\s+|static\s+)?class\s+(\w+)', content):
            result.classes.append({"name": m.group(1), "line": _line(m.start())})
        for m in re.finditer(r'interface\s+(\w+)', content):
            result.classes.append({"name": m.group(1), "line": _line(m.start()), "kind": "interface"})
        for m in re.finditer(r'(?:public|private|protected|internal)\s+(?:static\s+)?(?:async\s+)?(?:[\w<>\[\]?]+)\s+(\w+)\s*\(', content):
            name = m.group(1)
            if name not in ("if", "for", "while", "switch", "catch", "class", "new"):
                decorators: list[str] = []
                preceding = content[max(0, m.start() - 200):m.start()]
                for dm in re.finditer(r'\[(HttpGet|HttpPost|HttpPut|HttpDelete|HttpPatch|Route)\b', preceding):
                    decorators.append(dm.group(1).lower().replace("http", ""))
                result.functions.append({"name": name, "line": _line(m.start()), "decorators": decorators})
        return result
    
    def _analyze_swift_regex(self, file_path: Path) -> ASTResult:
        """Analyze Swift source files."""
        import re
        result = ASTResult(file_path=file_path)
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return result
        
        def _line(pos: int) -> int:
            return content[:pos].count("\n") + 1
        
        for m in re.finditer(r'(?:class|struct)\s+(\w+)', content):
            result.classes.append({"name": m.group(1), "line": _line(m.start())})
        for m in re.finditer(r'protocol\s+(\w+)', content):
            result.classes.append({"name": m.group(1), "line": _line(m.start()), "kind": "protocol"})
        for m in re.finditer(r'(?:public\s+|private\s+|internal\s+|open\s+)?(?:static\s+)?func\s+(\w+)', content):
            result.functions.append({"name": m.group(1), "line": _line(m.start())})
        for m in re.finditer(r'enum\s+(\w+)', content):
            result.classes.append({"name": m.group(1), "line": _line(m.start()), "kind": "enum"})
        return result
    
    def _analyze_dart_regex(self, file_path: Path) -> ASTResult:
        """Analyze Dart source files."""
        import re
        result = ASTResult(file_path=file_path)
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return result
        
        def _line(pos: int) -> int:
            return content[:pos].count("\n") + 1
        
        for m in re.finditer(r'(?:abstract\s+)?class\s+(\w+)', content):
            result.classes.append({"name": m.group(1), "line": _line(m.start())})
        for m in re.finditer(r'(?:Future|void|int|String|bool|double|dynamic|[\w<>]+)\s+(\w+)\s*\(', content):
            name = m.group(1)
            if name not in ("if", "for", "while", "switch", "catch", "return", "class"):
                result.functions.append({"name": name, "line": _line(m.start())})
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
