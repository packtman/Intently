"""Tracing subsystem for scan pipeline observability."""

from context_graph.tracing.collector import (
    TraceEvent,
    TraceCollector,
    NullTraceCollector,
    get_collector,
    remove_collector,
)

__all__ = [
    "TraceEvent",
    "TraceCollector",
    "NullTraceCollector",
    "get_collector",
    "remove_collector",
]
