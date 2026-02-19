"""
Embedding-based vector index for semantic codebase search.

Chunks source files into overlapping blocks, generates embeddings
(OpenAI text-embedding-3-small or TF-IDF fallback), and stores them
in ChromaDB for fast nearest-neighbour retrieval.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SOURCE_EXTENSIONS: set[str] = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".java", ".rb", ".rs",
    ".kt", ".swift", ".dart", ".c", ".cpp", ".h", ".hpp", ".cs", ".php",
    ".ex", ".exs", ".scala", ".clj", ".vue", ".svelte",
}

CONFIG_FILENAMES: set[str] = {
    "package.json", "tsconfig.json", "pyproject.toml", "Dockerfile",
    "docker-compose.yml", "docker-compose.yaml", "Makefile", "Cargo.toml",
    "go.mod", "build.gradle", "pom.xml", "setup.py", "setup.cfg",
    ".eslintrc.json", ".prettierrc", "vite.config.ts", "vite.config.js",
    "next.config.js", "next.config.mjs", "webpack.config.js",
    "tailwind.config.js", "tailwind.config.ts",
}

SKIP_DIRS: set[str] = {
    "node_modules", ".git", "__pycache__", "dist", "build", "venv",
    ".venv", ".next", ".nuxt", "target", "vendor", "coverage",
    ".mypy_cache",
}

MAX_SOURCE_FILES = 2000
MAX_FILE_SIZE_BYTES = 1_000_000  # 1 MB
EMBEDDING_BATCH_SIZE = 100


@dataclass
class CodeChunk:
    """A chunk of source code with location metadata."""

    file_path: str
    start_line: int
    end_line: int
    text: str
    header: str = ""

    @property
    def embedding_text(self) -> str:
        return f"{self.header}{self.text}"


@dataclass
class VectorSearchResult:
    """A single result from vector similarity search."""

    file_path: str
    start_line: int
    end_line: int
    text: str
    score: float


def chunk_file(
    file_path: Path,
    codebase_root: Path,
    chunk_size: int = 60,
    overlap: int = 10,
) -> list[CodeChunk]:
    """Split a source file into overlapping line-based chunks."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    if not content.strip():
        return []

    lines = content.splitlines()
    rel_path = str(file_path.relative_to(codebase_root))
    chunks: list[CodeChunk] = []
    step = max(chunk_size - overlap, 1)
    i = 0

    while i < len(lines):
        end = min(i + chunk_size, len(lines))
        chunk_lines = lines[i:end]
        text = "\n".join(chunk_lines)
        header = f"# File: {rel_path} (lines {i + 1}-{end})\n"
        chunks.append(CodeChunk(
            file_path=rel_path,
            start_line=i + 1,
            end_line=end,
            text=text,
            header=header,
        ))
        if end >= len(lines):
            break
        i += step

    return chunks


def _project_hash(codebase_path: str) -> str:
    return hashlib.sha256(codebase_path.encode()).hexdigest()[:16]


def _discover_files(codebase_root: Path) -> list[Path]:
    """Walk the codebase and collect indexable source/config files."""
    files: list[Path] = []

    for item in codebase_root.rglob("*"):
        if any(skip in item.parts for skip in SKIP_DIRS):
            continue
        if not item.is_file():
            continue
        if item.stat().st_size > MAX_FILE_SIZE_BYTES:
            continue
        if item.suffix.lower() in SOURCE_EXTENSIONS or item.name in CONFIG_FILENAMES:
            files.append(item)
        if len(files) >= MAX_SOURCE_FILES:
            break

    return files


class VectorIndex:
    """Embedding-based vector index backed by ChromaDB.

    Uses OpenAI embeddings when available, falls back to TF-IDF.
    """

    def __init__(self, codebase_path: str | Path) -> None:
        self.codebase_path = Path(codebase_path).resolve()
        self._hash = _project_hash(str(self.codebase_path))
        self._store_dir = Path.home() / ".intently" / "vector_store" / self._hash
        self._mtime_path = self._store_dir / "file_mtimes.json"
        self._collection = None
        self._use_openai = bool(os.getenv("OPENAI_API_KEY"))
        self._tfidf_vectorizer = None
        self._tfidf_matrix = None
        self._tfidf_chunks: list[CodeChunk] = []
        self._ready = False

    @property
    def is_ready(self) -> bool:
        return self._ready

    # ------------------------------------------------------------------
    # Build / Update
    # ------------------------------------------------------------------

    async def build_or_update(self) -> dict[str, int]:
        """Build or incrementally update the vector index.

        Returns stats: {"total_files", "new_chunks", "reused_files"}.
        """
        self._store_dir.mkdir(parents=True, exist_ok=True)

        files = _discover_files(self.codebase_path)
        old_mtimes = self._load_mtimes()
        new_mtimes: dict[str, float] = {}
        changed_files: list[Path] = []
        reused = 0

        for fp in files:
            rel = str(fp.relative_to(self.codebase_path))
            mtime = fp.stat().st_mtime
            new_mtimes[rel] = mtime
            if old_mtimes.get(rel) == mtime:
                reused += 1
            else:
                changed_files.append(fp)

        stale_keys = set(old_mtimes.keys()) - set(new_mtimes.keys())

        if self._use_openai:
            new_chunks = await self._build_chromadb(changed_files, stale_keys)
        else:
            new_chunks = self._build_tfidf(files)

        self._save_mtimes(new_mtimes)
        self._ready = True

        return {
            "total_files": len(files),
            "new_chunks": new_chunks,
            "reused_files": reused,
        }

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query: str, max_results: int = 10) -> list[VectorSearchResult]:
        if not self._ready:
            return []

        if self._use_openai and self._collection is not None:
            return self._search_chromadb(query, max_results)
        elif self._tfidf_vectorizer is not None:
            return self._search_tfidf(query, max_results)
        return []

    # ------------------------------------------------------------------
    # ChromaDB (OpenAI embeddings)
    # ------------------------------------------------------------------

    def _get_collection(self):
        if self._collection is not None:
            return self._collection

        import chromadb

        chroma_path = self._store_dir / "chroma"
        chroma_path.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(
            path=str(chroma_path),
        )
        self._collection = client.get_or_create_collection(
            name=f"codebase_{self._hash}",
            metadata={"hnsw:space": "cosine"},
        )
        return self._collection

    async def _build_chromadb(
        self,
        changed_files: list[Path],
        stale_keys: set[str],
    ) -> int:
        collection = self._get_collection()

        if stale_keys:
            for key in stale_keys:
                try:
                    existing = collection.get(where={"file_path": key})
                    if existing["ids"]:
                        collection.delete(ids=existing["ids"])
                except Exception:
                    pass

        all_chunks: list[CodeChunk] = []
        for fp in changed_files:
            rel = str(fp.relative_to(self.codebase_path))
            try:
                existing = collection.get(where={"file_path": rel})
                if existing["ids"]:
                    collection.delete(ids=existing["ids"])
            except Exception:
                pass
            all_chunks.extend(chunk_file(fp, self.codebase_path))

        if not all_chunks:
            return 0

        embeddings = await self._embed_openai([c.embedding_text for c in all_chunks])

        for batch_start in range(0, len(all_chunks), EMBEDDING_BATCH_SIZE):
            batch_end = min(batch_start + EMBEDDING_BATCH_SIZE, len(all_chunks))
            batch_chunks = all_chunks[batch_start:batch_end]
            batch_embeddings = embeddings[batch_start:batch_end]

            collection.add(
                ids=[
                    f"{c.file_path}:{c.start_line}-{c.end_line}"
                    for c in batch_chunks
                ],
                embeddings=batch_embeddings,
                documents=[c.text for c in batch_chunks],
                metadatas=[
                    {
                        "file_path": c.file_path,
                        "start_line": c.start_line,
                        "end_line": c.end_line,
                    }
                    for c in batch_chunks
                ],
            )

        return len(all_chunks)

    async def _embed_openai(self, texts: list[str]) -> list[list[float]]:
        from openai import AsyncOpenAI

        client = AsyncOpenAI()
        all_embeddings: list[list[float]] = []

        for batch_start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
            batch = texts[batch_start : batch_start + EMBEDDING_BATCH_SIZE]
            response = await client.embeddings.create(
                model="text-embedding-3-small",
                input=batch,
            )
            all_embeddings.extend([item.embedding for item in response.data])

        return all_embeddings

    def _search_chromadb(self, query: str, max_results: int) -> list[VectorSearchResult]:
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(self._search_chromadb_sync, query, max_results)
                return future.result(timeout=30)
        return self._search_chromadb_sync(query, max_results)

    def _search_chromadb_sync(self, query: str, max_results: int) -> list[VectorSearchResult]:
        try:
            from openai import OpenAI

            client = OpenAI()
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=[query],
            )
            query_embedding = response.data[0].embedding

            collection = self._get_collection()
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=max_results,
            )

            search_results: list[VectorSearchResult] = []
            if results and results["documents"]:
                docs = results["documents"][0]
                metas = results["metadatas"][0] if results["metadatas"] else [{}] * len(docs)
                distances = results["distances"][0] if results["distances"] else [0.0] * len(docs)

                for doc, meta, dist in zip(docs, metas, distances):
                    score = 1.0 - dist
                    search_results.append(VectorSearchResult(
                        file_path=meta.get("file_path", ""),
                        start_line=meta.get("start_line", 0),
                        end_line=meta.get("end_line", 0),
                        text=doc,
                        score=score,
                    ))

            return search_results
        except Exception as exc:
            logger.error("ChromaDB search failed: %s", exc)
            return []

    # ------------------------------------------------------------------
    # TF-IDF fallback (no API key needed)
    # ------------------------------------------------------------------

    def _build_tfidf(self, files: list[Path]) -> int:
        from sklearn.feature_extraction.text import TfidfVectorizer

        all_chunks: list[CodeChunk] = []
        for fp in files:
            all_chunks.extend(chunk_file(fp, self.codebase_path))

        if not all_chunks:
            self._tfidf_vectorizer = None
            self._tfidf_matrix = None
            self._tfidf_chunks = []
            return 0

        texts = [c.embedding_text for c in all_chunks]
        vectorizer = TfidfVectorizer(
            max_features=10000,
            sublinear_tf=True,
            stop_words="english",
            token_pattern=r"(?u)\b\w[\w.]+\b",
        )
        matrix = vectorizer.fit_transform(texts)

        self._tfidf_vectorizer = vectorizer
        self._tfidf_matrix = matrix
        self._tfidf_chunks = all_chunks

        return len(all_chunks)

    def _search_tfidf(self, query: str, max_results: int) -> list[VectorSearchResult]:
        from sklearn.metrics.pairwise import cosine_similarity

        if self._tfidf_vectorizer is None or self._tfidf_matrix is None:
            return []

        query_vec = self._tfidf_vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self._tfidf_matrix).flatten()

        top_indices = scores.argsort()[::-1][:max_results]

        results: list[VectorSearchResult] = []
        for idx in top_indices:
            score = float(scores[idx])
            if score <= 0:
                continue
            chunk = self._tfidf_chunks[idx]
            results.append(VectorSearchResult(
                file_path=chunk.file_path,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                text=chunk.text,
                score=score,
            ))

        return results

    # ------------------------------------------------------------------
    # Mtime tracking
    # ------------------------------------------------------------------

    def _load_mtimes(self) -> dict[str, float]:
        if self._mtime_path.exists():
            try:
                return json.loads(self._mtime_path.read_text())
            except Exception:
                pass
        return {}

    def _save_mtimes(self, mtimes: dict[str, float]) -> None:
        try:
            self._mtime_path.write_text(json.dumps(mtimes))
        except Exception as exc:
            logger.warning("Failed to save mtime cache: %s", exc)
