"""
Trace event collector for scan pipeline observability.

Provides a thread-safe, append-only event log per review_id.  Each scan
phase calls ``collector.emit(...)`` to record granular progress events that
are then streamed to the frontend via SSE.

Usage::

    from context_graph.tracing import get_collector

    collector = get_collector(review_id)
    collector.emit("info", "prd_parse", "Parsing PRD...", features=12)
"""

from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class TraceEvent:
    """A single trace event emitted during a scan."""

    timestamp: str
    elapsed_ms: float
    level: str          # info | debug | warn | error
    phase: str          # prd_parse | codebase_analysis | llm_dispatch | fp_filter | report_gen | bulk
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TraceCollector:
    """Thread-safe, append-only trace event log for a single scan.

    Supports ``asyncio.Event``-based notification so an SSE endpoint can
    ``await`` new events without polling.
    """

    def __init__(self, review_id: str) -> None:
        self.review_id = review_id
        self._events: list[TraceEvent] = []
        self._lock = threading.Lock()
        self._start_time = time.monotonic()

        # asyncio event used to wake up SSE consumers when a new trace
        # event is appended.  Created lazily because the collector may
        # be instantiated outside an event loop.
        self._notify: asyncio.Event | None = None
        self._closed = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def emit(
        self,
        level: str,
        phase: str,
        message: str,
        **metadata: Any,
    ) -> TraceEvent:
        """Record a trace event and notify any waiting SSE consumers."""
        event = TraceEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            elapsed_ms=round((time.monotonic() - self._start_time) * 1000, 1),
            level=level,
            phase=phase,
            message=message,
            metadata=metadata if metadata else {},
        )
        with self._lock:
            self._events.append(event)
        # Wake up SSE listener (if any)
        if self._notify is not None:
            self._notify.set()
        return event

    def events_since(self, cursor: int = 0) -> list[TraceEvent]:
        """Return events from *cursor* onwards (non-blocking)."""
        with self._lock:
            return list(self._events[cursor:])

    @property
    def event_count(self) -> int:
        with self._lock:
            return len(self._events)

    async def wait_for_new(self, timeout: float = 30.0) -> bool:
        """Block until a new event is emitted or *timeout* seconds pass.

        Returns ``True`` if woken by a new event, ``False`` on timeout.
        """
        if self._notify is None:
            self._notify = asyncio.Event()
        self._notify.clear()
        try:
            await asyncio.wait_for(self._notify.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    def close(self) -> None:
        """Mark the collector as closed (scan finished)."""
        self._closed = True
        if self._notify is not None:
            self._notify.set()

    @property
    def is_closed(self) -> bool:
        return self._closed


class NullTraceCollector(TraceCollector):
    """No-op collector that silently discards all events.

    Used when the ``enable_scan_tracing`` feature flag is disabled so
    callers can call ``emit()`` / ``close()`` without guards.
    """

    def __init__(self) -> None:
        # Minimal init — skip the real constructor to avoid allocations
        self.review_id = "__null__"
        self._events: list[TraceEvent] = []
        self._lock = threading.Lock()
        self._start_time = time.monotonic()
        self._notify = None
        self._closed = True  # always closed so SSE exits immediately

    def emit(self, level: str, phase: str, message: str, **metadata: Any) -> TraceEvent:  # type: ignore[override]
        return TraceEvent(
            timestamp="", elapsed_ms=0, level=level,
            phase=phase, message=message, metadata={},
        )

    def close(self) -> None:
        pass


_NULL_COLLECTOR = NullTraceCollector()


# ======================================================================
# Global registry — one collector per review_id
# ======================================================================

_registry: dict[str, TraceCollector] = {}
_registry_lock = threading.Lock()


def get_collector(review_id: str) -> TraceCollector:
    """Get or create the ``TraceCollector`` for *review_id*.

    Returns a real collector only when the ``enable_scan_tracing``
    feature flag is enabled.  Otherwise returns the shared null
    collector which silently discards events.
    """
    from context_graph.config.features import get_features

    if not get_features().enable_scan_tracing:
        return _NULL_COLLECTOR

    with _registry_lock:
        if review_id not in _registry:
            _registry[review_id] = TraceCollector(review_id)
        return _registry[review_id]


def remove_collector(review_id: str) -> None:
    """Remove collector from registry (cleanup after scan completes)."""
    with _registry_lock:
        collector = _registry.pop(review_id, None)
        if collector is not None:
            collector.close()
