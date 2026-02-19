"""Product-aware chat module for Intently."""

from context_graph.chat.product_chat import ProductChat
from context_graph.chat.codebase_reader import CodebaseReader

__all__ = ["ProductChat", "CodebaseReader", "VectorIndex"]


def __getattr__(name: str):
    if name == "CodebaseReader":
        from context_graph.chat.codebase_reader import CodebaseReader
        return CodebaseReader
    if name == "VectorIndex":
        from context_graph.chat.vector_index import VectorIndex
        return VectorIndex
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
