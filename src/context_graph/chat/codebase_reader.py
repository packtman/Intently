"""
Codebase reader — keyword search over AST symbols with optional
vector-based hybrid search.

Builds a CodebaseIndex from HybridAnalyzer AST results, supporting
token-based keyword matching and Reciprocal Rank Fusion when a
VectorIndex is available.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

MAX_SNIPPET_LINES = 80
MAX_TOTAL_LINES = 300


@dataclass
class CodeSnippet:
    """A code snippet retrieved from the codebase."""

    file_path: str
    start_line: int
    end_line: int
    text: str
    symbol_name: str = ""
    score: float = 0.0


@dataclass
class SymbolEntry:
    """A symbol extracted from AST analysis."""

    name: str
    kind: str  # "class", "function", "interface"
    file_path: str
    line: int
    end_line: int | None = None


@dataclass
class CodebaseIndex:
    """In-memory index of AST symbols for keyword search."""

    symbols: list[SymbolEntry] = field(default_factory=list)
    file_count: int = 0
    class_count: int = 0
    function_count: int = 0

    @classmethod
    def from_ast_results(cls, ast_results: dict[str, Any]) -> CodebaseIndex:
        """Build index from HybridAnalyzer AST results dict."""
        index = cls()
        index.file_count = len(ast_results)

        for rel_path, ast_result in ast_results.items():
            for cls_info in getattr(ast_result, "classes", []):
                index.symbols.append(SymbolEntry(
                    name=cls_info.get("name", ""),
                    kind=cls_info.get("kind", "class"),
                    file_path=rel_path,
                    line=cls_info.get("line", 0),
                    end_line=cls_info.get("end_line"),
                ))
                index.class_count += 1

            for func_info in getattr(ast_result, "functions", []):
                index.symbols.append(SymbolEntry(
                    name=func_info.get("name", ""),
                    kind="function",
                    file_path=rel_path,
                    line=func_info.get("line", 0),
                    end_line=func_info.get("end_line"),
                ))
                index.function_count += 1

        return index


def _tokenize(text: str) -> set[str]:
    """Split text into lowercase tokens for keyword matching."""
    tokens = re.findall(r"[a-zA-Z][a-z]*|[A-Z]+(?=[A-Z][a-z]|\d|\b)", text)
    words = re.findall(r"\b\w{2,}\b", text.lower())
    return {t.lower() for t in tokens} | set(words)


class CodebaseReader:
    """Reads and searches a codebase using AST symbols and optional vector index."""

    def __init__(
        self,
        codebase_path: str | Path,
        index: CodebaseIndex,
        vector_index: Any | None = None,
    ) -> None:
        self.codebase_path = Path(codebase_path)
        self.index = index
        self.vector_index = vector_index

    # ------------------------------------------------------------------
    # Keyword search (unchanged legacy behaviour)
    # ------------------------------------------------------------------

    def search(self, query: str, max_results: int = 5) -> list[CodeSnippet]:
        """Token-overlap keyword search over AST symbols."""
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scored: list[tuple[float, SymbolEntry]] = []
        for sym in self.index.symbols:
            sym_tokens = _tokenize(sym.name)
            overlap = query_tokens & sym_tokens
            if overlap:
                scored.append((len(overlap), sym))

        scored.sort(key=lambda x: x[0], reverse=True)

        snippets: list[CodeSnippet] = []
        total_lines = 0
        for _score, sym in scored[:max_results * 2]:
            if len(snippets) >= max_results:
                break
            snippet = self._read_symbol(sym)
            if snippet is None:
                continue
            line_count = snippet.end_line - snippet.start_line + 1
            if total_lines + line_count > MAX_TOTAL_LINES:
                continue
            snippet.score = _score
            snippets.append(snippet)
            total_lines += line_count

        return snippets

    # ------------------------------------------------------------------
    # Hybrid search (keyword + vector via RRF)
    # ------------------------------------------------------------------

    def hybrid_search(self, query: str, max_results: int = 10) -> list[CodeSnippet]:
        """Combine keyword and vector search with Reciprocal Rank Fusion."""
        keyword_results = self.search(query, max_results=max_results)

        vector_results: list[CodeSnippet] = []
        if self.vector_index is not None:
            try:
                raw = self.vector_index.search(query, max_results=max_results)
                for r in raw:
                    vector_results.append(CodeSnippet(
                        file_path=r.file_path,
                        start_line=r.start_line,
                        end_line=r.end_line,
                        text=r.text,
                        score=r.score,
                    ))
            except Exception as exc:
                logger.warning("Vector search failed, using keyword only: %s", exc)

        if not vector_results:
            return keyword_results

        k = 60
        rrf_scores: dict[str, float] = {}
        snippet_map: dict[str, CodeSnippet] = {}

        for rank, snippet in enumerate(keyword_results):
            key = f"{snippet.file_path}:{snippet.start_line}-{snippet.end_line}"
            rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank + 1)
            snippet_map[key] = snippet

        for rank, snippet in enumerate(vector_results):
            key = f"{snippet.file_path}:{snippet.start_line}-{snippet.end_line}"
            rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank + 1)
            if key not in snippet_map:
                snippet_map[key] = snippet

        merged = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        deduped: list[CodeSnippet] = []
        for key, rrf_score in merged:
            snippet = snippet_map[key]
            if self._overlaps_existing(snippet, deduped):
                continue
            snippet.score = rrf_score
            deduped.append(snippet)
            if len(deduped) >= max_results:
                break

        for snippet in deduped:
            if not snippet.text:
                loaded = self._read_lines(snippet.file_path, snippet.start_line, snippet.end_line)
                if loaded:
                    snippet.text = loaded

        return deduped

    # ------------------------------------------------------------------
    # Structure summary
    # ------------------------------------------------------------------

    def get_structure_summary(self) -> str:
        """Return a brief summary of the indexed codebase."""
        lines = [
            f"Files: {self.index.file_count}",
            f"Classes: {self.index.class_count}",
            f"Functions: {self.index.function_count}",
        ]
        return " | ".join(lines)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _read_symbol(self, sym: SymbolEntry) -> CodeSnippet | None:
        """Read the source code for a symbol from disk."""
        file_path = self.codebase_path / sym.file_path
        if not file_path.is_file():
            return None

        try:
            all_lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            return None

        start = max(sym.line - 1, 0)
        end = min(sym.end_line or (start + MAX_SNIPPET_LINES), len(all_lines))
        if end - start > MAX_SNIPPET_LINES:
            end = start + MAX_SNIPPET_LINES

        text = "\n".join(all_lines[start:end])
        return CodeSnippet(
            file_path=sym.file_path,
            start_line=start + 1,
            end_line=end,
            text=text,
            symbol_name=sym.name,
        )

    def _read_lines(self, rel_path: str, start: int, end: int) -> str | None:
        file_path = self.codebase_path / rel_path
        if not file_path.is_file():
            return None
        try:
            all_lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
            return "\n".join(all_lines[max(start - 1, 0):end])
        except Exception:
            return None

    @staticmethod
    def _overlaps_existing(candidate: CodeSnippet, existing: list[CodeSnippet]) -> bool:
        """Check if candidate overlaps >50% with any existing snippet."""
        for ex in existing:
            if candidate.file_path != ex.file_path:
                continue
            overlap_start = max(candidate.start_line, ex.start_line)
            overlap_end = min(candidate.end_line, ex.end_line)
            overlap_lines = max(0, overlap_end - overlap_start + 1)
            candidate_lines = candidate.end_line - candidate.start_line + 1
            if candidate_lines > 0 and overlap_lines / candidate_lines > 0.5:
                return True
        return False
