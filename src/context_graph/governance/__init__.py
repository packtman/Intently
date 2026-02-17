"""Governance module — approval gates and policy enforcement."""

from context_graph.governance.gate_evaluator import GateEvaluator, ApprovalGate, GateResult

__all__ = ["GateEvaluator", "ApprovalGate", "GateResult"]
