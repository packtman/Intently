"""
Storage abstractions for Context Graph.

Provides pluggable storage backends for reviews, comments, and collaboration data.

Available implementations:
- InMemoryReviewStorage / InMemoryCollaborationStorage: For development/testing
- SQLiteReviewStorage / SQLiteCollaborationStorage: For persistent local storage

Configuration:
- Set STORAGE_BACKEND=sqlite for persistent storage
- Set STORAGE_BACKEND=memory (default) for in-memory storage
- Use get_review_storage() / get_collaboration_storage() for configured instances
"""

from context_graph.storage.base import (
    ReviewStorage,
    CollaborationStorage,
)
from context_graph.storage.memory import (
    InMemoryReviewStorage,
    InMemoryCollaborationStorage,
)
from context_graph.storage.sqlite import (
    SQLiteReviewStorage,
    SQLiteCollaborationStorage,
    create_sqlite_storage,
)
from context_graph.storage.config import (
    get_review_storage,
    get_collaboration_storage,
    get_storage,
    get_storage_backend,
    get_storage_db_path,
    reset_storage,
)

__all__ = [
    # Abstract interfaces
    "ReviewStorage",
    "CollaborationStorage",
    # In-memory implementations (development/testing)
    "InMemoryReviewStorage",
    "InMemoryCollaborationStorage",
    # SQLite implementations (persistent storage)
    "SQLiteReviewStorage",
    "SQLiteCollaborationStorage",
    "create_sqlite_storage",
    # Configuration functions (use these for configured instances)
    "get_review_storage",
    "get_collaboration_storage",
    "get_storage",
    "get_storage_backend",
    "get_storage_db_path",
    "reset_storage",
]

