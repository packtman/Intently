"""
Storage configuration for Context Graph.

Provides a unified way to configure and access storage backends.
Both desktop app and webapp use this configuration.

Configuration:
- Set STORAGE_BACKEND=sqlite to use persistent SQLite storage
- Set STORAGE_BACKEND=memory (default) to use in-memory storage
- Set STORAGE_DB_PATH to customize the SQLite database path
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple

from context_graph.storage.base import ReviewStorage, CollaborationStorage

# Global storage instances (singleton pattern)
_review_storage: ReviewStorage | None = None
_collaboration_storage: CollaborationStorage | None = None
_storage_initialized = False


def get_storage_backend() -> str:
    """Get configured storage backend type."""
    return os.getenv("STORAGE_BACKEND", "memory").lower()


def get_storage_db_path() -> Path:
    """Get SQLite database path.
    
    Priority:
    1. STORAGE_DB_PATH environment variable
    2. CONTEXT_GRAPH_DATA_DIR/reviews.db
    3. ~/.context-graph/reviews.db
    """
    if path := os.getenv("STORAGE_DB_PATH"):
        return Path(path)
    
    if data_dir := os.getenv("CONTEXT_GRAPH_DATA_DIR"):
        return Path(data_dir) / "reviews.db"
    
    # Default: ~/.context-graph/reviews.db
    default_dir = Path.home() / ".context-graph"
    default_dir.mkdir(parents=True, exist_ok=True)
    return default_dir / "reviews.db"


def get_review_storage() -> ReviewStorage:
    """Get the configured review storage instance.
    
    Creates storage on first call based on environment configuration.
    """
    global _review_storage, _storage_initialized
    
    if _review_storage is None:
        _initialize_storage()
    
    return _review_storage  # type: ignore


def get_collaboration_storage() -> CollaborationStorage:
    """Get the configured collaboration storage instance.
    
    Creates storage on first call based on environment configuration.
    """
    global _collaboration_storage, _storage_initialized
    
    if _collaboration_storage is None:
        _initialize_storage()
    
    return _collaboration_storage  # type: ignore


def _initialize_storage() -> None:
    """Initialize storage backends based on configuration."""
    global _review_storage, _collaboration_storage, _storage_initialized
    
    if _storage_initialized:
        return
    
    backend = get_storage_backend()
    
    if backend == "sqlite":
        from context_graph.storage.sqlite import (
            SQLiteReviewStorage,
            SQLiteCollaborationStorage,
        )
        
        db_path = get_storage_db_path()
        print(f"📦 Storage: SQLite ({db_path})")
        
        _review_storage = SQLiteReviewStorage(db_path)
        _collaboration_storage = SQLiteCollaborationStorage(db_path)
    
    else:
        # Default: in-memory
        from context_graph.storage.memory import (
            InMemoryReviewStorage,
            InMemoryCollaborationStorage,
        )
        
        print("📦 Storage: In-memory (data will not persist)")
        
        _review_storage = InMemoryReviewStorage()
        _collaboration_storage = InMemoryCollaborationStorage()
    
    _storage_initialized = True


def reset_storage() -> None:
    """Reset storage instances (useful for testing)."""
    global _review_storage, _collaboration_storage, _storage_initialized
    _review_storage = None
    _collaboration_storage = None
    _storage_initialized = False


def get_storage() -> Tuple[ReviewStorage, CollaborationStorage]:
    """Get both storage instances.
    
    Returns:
        Tuple of (review_storage, collaboration_storage)
    """
    return get_review_storage(), get_collaboration_storage()
