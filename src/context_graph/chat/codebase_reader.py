"""
Codebase Reader — reads code from the filesystem, guided by the AST index.

Provides smart file retrieval for the codebase-aware chat: given a natural
language query, finds the most relevant code snippets by matching against
the structural index (classes, functions, models, endpoints) already
extracted during review.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

MAX_SNIPPET_LINES = 80
MAX_TOTAL_CONTEXT_LINES = 300


@dataclass
class CodeSnippet:
    """A snippet of code read from the codebase."""

    file: str
    start_line: int
    end_line: int
    text: str
    symbol_name: str = ""
    symbol_type: str = ""  # "class", "function", "endpoint", "model"
    relevance_score: float = 0.0


@dataclass
class CodebaseIndex:
    """In-memory index built from review State for fast keyword lookup."""

    entries: list[dict[str, Any]] = field(default_factory=list)

    def search(self, tokens: set[str], max_results: int = 5) -> list[dict[str, Any]]:
        """Score each entry by how many query tokens match its name/keywords."""
        scored = []
        for entry in self.entries:
            name_lower = entry.get("name", "").lower()
            name_tokens = set(re.split(r"[_\s]+", name_lower)) | {name_lower}
            # Also split camelCase
            name_tokens |= set(
                t.lower() for t in re.findall(r"[A-Z][a-z]+|[a-z]+", entry.get("name", ""))
            )
            overlap = tokens & name_tokens
            if overlap:
                scored.append((len(overlap), entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored[:max_results]]


class CodebaseReader:
    """Reads code from the filesystem, guided by the structural index.

    The reader never does a full-codebase scan at query time. Instead it uses
    the pre-built index (from review State or HybridAnalyzer AST results)
    to locate relevant symbols and reads only those line ranges from disk.
    """

    def __init__(
        self,
        codebase_path: str | Path,
        state: Any | None = None,
    ) -> None:
        self.root = Path(codebase_path)
        self._index = self._build_index(state)

    # ------------------------------------------------------------------
    # Index building — one-time, from existing State data
    # ------------------------------------------------------------------

    def _build_index(self, state: Any | None) -> CodebaseIndex:
        """Build a lightweight in-memory index from the review State."""
        index = CodebaseIndex()
        if state is None:
            return index

        for ep in getattr(state, "api_endpoints", []) or []:
            if isinstance(ep, dict):
                index.entries.append({
                    "name": ep.get("path", ep.get("name", "")),
                    "type": "endpoint",
                    "method": ep.get("method", ""),
                    "file": ep.get("file", ""),
                    "line": ep.get("line", 0),
                })

        for model in getattr(state, "data_models", []) or []:
            if isinstance(model, dict):
                index.entries.append({
                    "name": model.get("name", ""),
                    "type": "model",
                    "file": model.get("file", ""),
                    "line": model.get("line", 0),
                })

        for entity in getattr(state, "entities", []) or []:
            etype = getattr(entity, "entity_type", None)
            etype_str = etype.value if hasattr(etype, "value") else str(etype) if etype else "unknown"
            source = getattr(entity, "source", "") or ""
            index.entries.append({
                "name": getattr(entity, "name", ""),
                "type": etype_str,
                "file": source,
                "line": 0,
            })

        return index

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(self, query: str, max_results: int = 5) -> list[CodeSnippet]:
        """Find code snippets relevant to a natural-language query."""
        tokens = self._tokenize(query)
        matches = self._index.search(tokens, max_results=max_results * 2)

        snippets: list[CodeSnippet] = []
        total_lines = 0
        seen_files: dict[str, set[int]] = {}

        for match in matches:
            if total_lines >= MAX_TOTAL_CONTEXT_LINES:
                break
            file_path = match.get("file", "")
            if not file_path:
                continue

            abs_path = self._resolve_path(file_path)
            if abs_path is None:
                continue

            start_line = max(1, match.get("line", 1))
            snippet = self._read_symbol(abs_path, match.get("name", ""), start_line)
            if snippet is None:
                continue

            file_key = str(abs_path)
            if file_key in seen_files and start_line in seen_files[file_key]:
                continue
            seen_files.setdefault(file_key, set()).add(start_line)

            snippet.symbol_type = match.get("type", "")
            snippet.relevance_score = len(tokens & self._name_tokens(match.get("name", "")))
            snippets.append(snippet)
            total_lines += snippet.end_line - snippet.start_line + 1

            if len(snippets) >= max_results:
                break

        snippets.sort(key=lambda s: s.relevance_score, reverse=True)
        return snippets

    def read_entity(self, entity_name: str) -> CodeSnippet | None:
        """Read the code for a specific named entity."""
        for entry in self._index.entries:
            if entry.get("name", "").lower() == entity_name.lower():
                file_path = entry.get("file", "")
                if not file_path:
                    continue
                abs_path = self._resolve_path(file_path)
                if abs_path is None:
                    continue
                snippet = self._read_symbol(abs_path, entry.get("name", ""), entry.get("line", 1))
                if snippet:
                    snippet.symbol_type = entry.get("type", "")
                    return snippet
        return None

    def read_file_range(self, file_path: str, start: int, end: int) -> str | None:
        """Read a specific line range from a file."""
        abs_path = self._resolve_path(file_path)
        if abs_path is None:
            return None
        return self._read_lines(abs_path, start, end)

    def get_structure_summary(self) -> dict[str, Any]:
        """Return a summary of the codebase structure for the LLM context."""
        endpoints = [e for e in self._index.entries if e["type"] == "endpoint"]
        models = [e for e in self._index.entries if e["type"] == "model"]
        classes = [e for e in self._index.entries if e["type"] in ("class", "CLASS")]
        functions = [e for e in self._index.entries if e["type"] in ("function", "FUNCTION")]

        return {
            "codebase_path": str(self.root),
            "total_indexed_symbols": len(self._index.entries),
            "endpoints": [
                {"name": e["name"], "method": e.get("method", ""), "file": self._rel(e.get("file", ""))}
                for e in endpoints[:30]
            ],
            "data_models": [
                {"name": m["name"], "file": self._rel(m.get("file", ""))}
                for m in models[:30]
            ],
            "key_classes": [
                {"name": c["name"], "file": self._rel(c.get("file", ""))}
                for c in classes[:20]
            ],
            "key_functions": [
                {"name": f["name"], "file": self._rel(f.get("file", ""))}
                for f in functions[:20]
            ],
        }

    # ------------------------------------------------------------------
    # File reading helpers
    # ------------------------------------------------------------------

    def _resolve_path(self, file_path: str) -> Path | None:
        """Resolve a file path (absolute or relative) to an existing file."""
        p = Path(file_path)
        if p.is_absolute() and p.is_file():
            return p
        rel = self.root / file_path
        if rel.is_file():
            return rel
        # Try stripping the codebase root prefix if stored as absolute
        try:
            relative = p.relative_to(self.root)
            candidate = self.root / relative
            if candidate.is_file():
                return candidate
        except ValueError:
            pass
        return None

    def _read_lines(self, path: Path, start: int, end: int) -> str | None:
        """Read lines [start, end] from a file (1-indexed)."""
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            s = max(0, start - 1)
            e = min(len(lines), end)
            return "\n".join(lines[s:e])
        except Exception as exc:
            logger.debug("Failed to read %s: %s", path, exc)
            return None

    def _read_symbol(self, path: Path, symbol_name: str, hint_line: int) -> CodeSnippet | None:
        """Read a symbol (class/function) from a file.

        Uses the hint line as starting point, then tries to detect the
        symbol boundary using simple indentation heuristics.
        """
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None

        lines = content.splitlines()
        if not lines:
            return None

        start = max(0, hint_line - 1)

        # If hint_line is 0 (no line info), try to find the symbol by name
        if hint_line <= 1 and symbol_name:
            for i, line in enumerate(lines):
                if re.search(rf"\b(class|def|async\s+def|function|export)\s+{re.escape(symbol_name)}\b", line):
                    start = i
                    break

        # Determine the end by looking for the next symbol at the same or lower indent
        if start < len(lines):
            first_line = lines[start]
            base_indent = len(first_line) - len(first_line.lstrip())
            end = start + 1
            for i in range(start + 1, min(len(lines), start + MAX_SNIPPET_LINES)):
                line = lines[i]
                if not line.strip():
                    end = i + 1
                    continue
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= base_indent and re.match(
                    r"\s*(class |def |async def |function |export |@)", line
                ):
                    break
                end = i + 1
        else:
            end = start + 1

        end = min(end, start + MAX_SNIPPET_LINES, len(lines))
        text = "\n".join(lines[start:end])
        rel_file = self._rel(str(path))

        return CodeSnippet(
            file=rel_file,
            start_line=start + 1,
            end_line=end,
            text=text,
            symbol_name=symbol_name,
        )

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _rel(self, file_path: str) -> str:
        """Convert an absolute path to a path relative to root."""
        try:
            return str(Path(file_path).relative_to(self.root))
        except ValueError:
            return file_path

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        """Split a natural-language query into search tokens."""
        text_lower = text.lower()
        # Split on whitespace and punctuation
        raw = re.split(r"[\s,;:?!.()\[\]{}/\\\"'`]+", text_lower)
        tokens = {t for t in raw if len(t) >= 2}
        # Also split camelCase / PascalCase words found in the query
        for word in list(tokens):
            parts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)", word)
            tokens |= {p.lower() for p in parts if len(p) >= 2}
        # Remove very common stop words
        tokens -= {
            "the", "is", "at", "in", "of", "to", "and", "or", "for", "with",
            "how", "does", "what", "show", "me", "can", "do", "my", "this",
            "that", "it", "an", "be", "on", "as", "by", "from", "are", "was",
            "which", "where", "when", "who", "all", "about", "our",
        }
        return tokens

    @staticmethod
    def _name_tokens(name: str) -> set[str]:
        """Split a symbol name into matchable tokens."""
        parts = re.split(r"[_\s/]+", name.lower())
        tokens = set(parts)
        tokens |= {
            t.lower() for t in re.findall(r"[A-Z][a-z]+|[a-z]+", name)
        }
        tokens |= {name.lower()}
        return tokens
