"""
Canvas Threat Analyzer — STRIDE-based threat analysis on visual canvas topologies.

Applies pattern-based rules to identify threats from data flow diagrams,
then optionally enriches results via LLM for deeper context-aware analysis.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class CanvasNodeType(str, Enum):
    ACTOR = "actor"
    PROCESS = "process"
    DATA_STORE = "data_store"
    EXTERNAL_ENTITY = "external"
    TRUST_BOUNDARY = "trust_boundary"


STRIDE_CATEGORIES = [
    "spoofing",
    "tampering",
    "repudiation",
    "information_disclosure",
    "denial_of_service",
    "elevation_of_privilege",
]

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _node_map(nodes: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {n["id"]: n for n in nodes}


def _boundary_contains(boundary: dict[str, Any], node: dict[str, Any]) -> bool:
    """Check if a node's center falls within a trust boundary rectangle."""
    nx = node.get("x", 0) + node.get("width", 120) / 2
    ny = node.get("y", 0) + node.get("height", 80) / 2
    bx, by = boundary.get("x", 0), boundary.get("y", 0)
    bw, bh = boundary.get("width", 200), boundary.get("height", 200)
    return bx <= nx <= bx + bw and by <= ny <= by + bh


def _node_boundary(
    node_id: str,
    nodes_map: dict[str, dict[str, Any]],
    boundaries: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Return the trust boundary containing a node, or None."""
    node = nodes_map.get(node_id)
    if not node:
        return None
    for b in boundaries:
        if _boundary_contains(b, node):
            return b
    return None


def _edge_crosses_boundary(
    edge: dict[str, Any],
    nodes_map: dict[str, dict[str, Any]],
    boundaries: list[dict[str, Any]],
) -> bool:
    src_b = _node_boundary(edge["source_id"], nodes_map, boundaries)
    tgt_b = _node_boundary(edge["target_id"], nodes_map, boundaries)
    if src_b is None and tgt_b is None:
        return False
    if src_b is None or tgt_b is None:
        return True
    return src_b["id"] != tgt_b["id"]


def _make_threat(
    category: str,
    title: str,
    description: str,
    severity: str,
    affected_node_ids: list[str],
    affected_edge_ids: list[str],
    mitigation: str,
    confidence: float = 0.75,
) -> dict[str, Any]:
    return {
        "id": str(uuid4()),
        "threat_id": f"STRIDE-{category[:3].upper()}-{str(uuid4())[:8]}",
        "category": category,
        "title": title,
        "description": description,
        "severity": severity,
        "affected_node_ids": affected_node_ids,
        "affected_edge_ids": affected_edge_ids,
        "mitigation": mitigation,
        "confidence": confidence,
        "source": "ai",
    }


class CanvasThreatAnalyzer:
    """Analyzes canvas topology for threats using STRIDE pattern rules."""

    def analyze_sync(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
        boundaries: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Run pattern-based STRIDE analysis on the canvas topology.

        Returns a list of ThreatOverlay dicts.
        """
        threats: list[dict[str, Any]] = []
        nmap = _node_map(nodes)

        threats.extend(self._check_spoofing(nodes, edges, nmap, boundaries))
        threats.extend(self._check_tampering(nodes, edges, nmap, boundaries))
        threats.extend(self._check_repudiation(nodes, edges, nmap, boundaries))
        threats.extend(self._check_info_disclosure(nodes, edges, nmap, boundaries))
        threats.extend(self._check_dos(nodes, edges, nmap, boundaries))
        threats.extend(self._check_elevation(nodes, edges, nmap, boundaries))

        threats.sort(key=lambda t: SEVERITY_ORDER.get(t["severity"], 99))
        return threats

    # ------------------------------------------------------------------
    # STRIDE checks
    # ------------------------------------------------------------------

    def _check_spoofing(
        self, nodes: list, edges: list, nmap: dict, boundaries: list
    ) -> list[dict[str, Any]]:
        threats = []
        for edge in edges:
            src = nmap.get(edge["source_id"])
            tgt = nmap.get(edge["target_id"])
            if not src or not tgt:
                continue
            if src.get("type") in ("actor", "external") and tgt.get("type") == "process":
                if not tgt.get("properties", {}).get("requires_auth"):
                    threats.append(
                        _make_threat(
                            "spoofing",
                            f"Unauthenticated access: {src.get('label', '?')} → {tgt.get('label', '?')}",
                            f"External entity '{src.get('label')}' can reach process "
                            f"'{tgt.get('label')}' without authentication.",
                            "high",
                            [src["id"], tgt["id"]],
                            [edge["id"]],
                            "Add authentication to the process before accepting requests from external entities.",
                        )
                    )
        return threats

    def _check_tampering(
        self, nodes: list, edges: list, nmap: dict, boundaries: list
    ) -> list[dict[str, Any]]:
        threats = []
        for edge in edges:
            src = nmap.get(edge["source_id"])
            tgt = nmap.get(edge["target_id"])
            if not src or not tgt:
                continue
            if tgt.get("type") == "data_store":
                if not src.get("properties", {}).get("validates_input"):
                    threats.append(
                        _make_threat(
                            "tampering",
                            f"Unvalidated write: {src.get('label', '?')} → {tgt.get('label', '?')}",
                            f"Process '{src.get('label')}' writes to data store "
                            f"'{tgt.get('label')}' without input validation.",
                            "medium",
                            [src["id"], tgt["id"]],
                            [edge["id"]],
                            "Add input validation and sanitization before writing to the data store.",
                        )
                    )
        return threats

    def _check_repudiation(
        self, nodes: list, edges: list, nmap: dict, boundaries: list
    ) -> list[dict[str, Any]]:
        threats = []
        sensitive_stores = [
            n for n in nodes
            if n.get("type") == "data_store"
            and n.get("properties", {}).get("handles_pii")
        ]
        for store in sensitive_stores:
            reading_edges = [
                e for e in edges if e["target_id"] == store["id"] or e["source_id"] == store["id"]
            ]
            has_audit = store.get("properties", {}).get("audit_logging")
            if not has_audit and reading_edges:
                threats.append(
                    _make_threat(
                        "repudiation",
                        f"Missing audit logging on '{store.get('label', '?')}'",
                        f"Sensitive data store '{store.get('label')}' lacks audit logging. "
                        "Actions on PII data cannot be traced back to actors.",
                        "medium",
                        [store["id"]],
                        [e["id"] for e in reading_edges[:3]],
                        "Enable audit logging on all access to sensitive data stores.",
                    )
                )
        return threats

    def _check_info_disclosure(
        self, nodes: list, edges: list, nmap: dict, boundaries: list
    ) -> list[dict[str, Any]]:
        threats = []
        for edge in edges:
            if not _edge_crosses_boundary(edge, nmap, boundaries):
                continue
            classification = edge.get("data_classification", "unclassified")
            protocol = edge.get("protocol", "").lower()
            if classification in ("pii", "credentials", "internal"):
                is_encrypted = protocol in ("https", "tls", "grpc", "ssh")
                if not is_encrypted:
                    src = nmap.get(edge["source_id"])
                    tgt = nmap.get(edge["target_id"])
                    threats.append(
                        _make_threat(
                            "information_disclosure",
                            f"Sensitive data crosses trust boundary unencrypted",
                            f"Data classified as '{classification}' flows from "
                            f"'{src.get('label', '?')}' to '{tgt.get('label', '?')}' "
                            f"across a trust boundary without encryption (protocol: {protocol or 'unknown'}).",
                            "high",
                            [edge["source_id"], edge["target_id"]],
                            [edge["id"]],
                            "Encrypt data in transit using TLS/HTTPS when crossing trust boundaries.",
                        )
                    )
        pii_stores = [
            n for n in nodes
            if n.get("type") == "data_store" and n.get("properties", {}).get("handles_pii")
        ]
        for store in pii_stores:
            if not store.get("properties", {}).get("encryption_at_rest"):
                threats.append(
                    _make_threat(
                        "information_disclosure",
                        f"PII store '{store.get('label', '?')}' lacks encryption at rest",
                        f"Data store '{store.get('label')}' handles PII but does not "
                        "have encryption at rest configured.",
                        "high",
                        [store["id"]],
                        [],
                        "Enable encryption at rest for all data stores containing PII.",
                    )
                )
        return threats

    def _check_dos(
        self, nodes: list, edges: list, nmap: dict, boundaries: list
    ) -> list[dict[str, Any]]:
        threats = []
        public_processes = [
            n for n in nodes
            if n.get("type") == "process"
            and any(
                nmap.get(e["source_id"], {}).get("type") in ("actor", "external")
                for e in edges
                if e["target_id"] == n["id"]
            )
        ]
        for proc in public_processes:
            if not proc.get("properties", {}).get("rate_limiting"):
                threats.append(
                    _make_threat(
                        "denial_of_service",
                        f"No rate limiting on '{proc.get('label', '?')}'",
                        f"Public-facing process '{proc.get('label')}' does not have "
                        "rate limiting, making it vulnerable to abuse.",
                        "medium",
                        [proc["id"]],
                        [],
                        "Implement rate limiting and request throttling on public-facing processes.",
                    )
                )
        return threats

    def _check_elevation(
        self, nodes: list, edges: list, nmap: dict, boundaries: list
    ) -> list[dict[str, Any]]:
        threats = []
        for edge in edges:
            src = nmap.get(edge["source_id"])
            tgt = nmap.get(edge["target_id"])
            if not src or not tgt:
                continue
            if src.get("type") == "external" and tgt.get("type") == "data_store":
                threats.append(
                    _make_threat(
                        "elevation_of_privilege",
                        f"Direct external access to data store '{tgt.get('label', '?')}'",
                        f"External entity '{src.get('label')}' has a direct data flow "
                        f"to data store '{tgt.get('label')}' bypassing process controls.",
                        "critical",
                        [src["id"], tgt["id"]],
                        [edge["id"]],
                        "Route all external access through an authenticated process layer with authorization checks.",
                    )
                )
        return threats


def generate_export_markdown(canvas: dict[str, Any]) -> str:
    """Generate a Markdown threat model document from canvas state."""
    lines: list[str] = []
    title = canvas.get("title", "Untitled Threat Model")
    lines.append(f"# Threat Model: {title}\n")
    lines.append(f"*Generated from Interactive Threat Canvas*\n")

    nodes = canvas.get("nodes", [])
    edges = canvas.get("edges", [])
    boundaries_list = canvas.get("boundaries", [])
    threats = canvas.get("threats", [])
    nmap = _node_map(nodes)

    # --- Elements by type ---
    actors = [n for n in nodes if n.get("type") == "actor"]
    processes = [n for n in nodes if n.get("type") == "process"]
    data_stores = [n for n in nodes if n.get("type") == "data_store"]
    externals = [n for n in nodes if n.get("type") == "external"]

    lines.append("## Data Flow Diagram Elements\n")

    if actors:
        lines.append("### Actors\n")
        lines.append("| Name | Properties |")
        lines.append("|------|-----------|")
        for a in actors:
            props = ", ".join(f"{k}={v}" for k, v in a.get("properties", {}).items()) or "—"
            lines.append(f"| {a.get('label', '?')} | {props} |")
        lines.append("")

    if processes:
        lines.append("### Processes\n")
        lines.append("| Name | Auth Required | Rate Limiting |")
        lines.append("|------|--------------|--------------|")
        for p in processes:
            props = p.get("properties", {})
            auth = "Yes" if props.get("requires_auth") else "No"
            rl = "Yes" if props.get("rate_limiting") else "No"
            lines.append(f"| {p.get('label', '?')} | {auth} | {rl} |")
        lines.append("")

    if data_stores:
        lines.append("### Data Stores\n")
        lines.append("| Name | Handles PII | Encryption at Rest |")
        lines.append("|------|------------|-------------------|")
        for ds in data_stores:
            props = ds.get("properties", {})
            pii = "Yes" if props.get("handles_pii") else "No"
            enc = "Yes" if props.get("encryption_at_rest") else "No"
            lines.append(f"| {ds.get('label', '?')} | {pii} | {enc} |")
        lines.append("")

    if externals:
        lines.append("### External Entities\n")
        lines.append("| Name | Properties |")
        lines.append("|------|-----------|")
        for e in externals:
            props = ", ".join(f"{k}={v}" for k, v in e.get("properties", {}).items()) or "—"
            lines.append(f"| {e.get('label', '?')} | {props} |")
        lines.append("")

    # --- Data Flows ---
    if edges:
        lines.append("## Data Flows\n")
        lines.append("| From | To | Classification | Protocol | Crosses Boundary |")
        lines.append("|------|----|---------------|----------|-----------------|")
        for edge in edges:
            src = nmap.get(edge["source_id"], {}).get("label", "?")
            tgt = nmap.get(edge["target_id"], {}).get("label", "?")
            cls = edge.get("data_classification", "unclassified")
            proto = edge.get("protocol", "—") or "—"
            crosses = "Yes" if _edge_crosses_boundary(edge, nmap, boundaries_list) else "No"
            lines.append(f"| {src} | {tgt} | {cls} | {proto} | {crosses} |")
        lines.append("")

    # --- Trust Boundaries ---
    if boundaries_list:
        lines.append("## Trust Boundaries\n")
        trust_labels = {0: "Untrusted", 1: "DMZ", 2: "Internal", 3: "Highly Trusted"}
        lines.append("| Boundary | Trust Level | Contained Elements |")
        lines.append("|----------|------------|-------------------|")
        for b in boundaries_list:
            contained = [
                n.get("label", "?") for n in nodes if _boundary_contains(b, n)
            ]
            level = trust_labels.get(b.get("trust_level", 0), str(b.get("trust_level", 0)))
            lines.append(f"| {b.get('label', '?')} | {level} | {', '.join(contained) or '—'} |")
        lines.append("")

    # --- Threats by STRIDE ---
    if threats:
        lines.append("## Identified Threats (STRIDE)\n")
        for cat in STRIDE_CATEGORIES:
            cat_threats = [t for t in threats if t.get("category") == cat]
            if not cat_threats:
                continue
            cat_title = cat.replace("_", " ").title()
            lines.append(f"### {cat_title}\n")
            lines.append("| Threat | Severity | Affected Elements | Mitigation |")
            lines.append("|--------|----------|-------------------|------------|")
            for t in cat_threats:
                affected_names = [
                    nmap.get(nid, {}).get("label", nid) for nid in t.get("affected_node_ids", [])
                ]
                lines.append(
                    f"| {t.get('title', '?')} | {t.get('severity', '?').upper()} "
                    f"| {', '.join(affected_names) or '—'} | {t.get('mitigation', '—')} |"
                )
            lines.append("")

        # --- Risk Summary ---
        lines.append("## Risk Summary\n")
        lines.append(f"- **Total threats:** {len(threats)}")
        for sev in ("critical", "high", "medium", "low"):
            count = sum(1 for t in threats if t.get("severity") == sev)
            if count:
                lines.append(f"- **{sev.title()}:** {count}")
        lines.append("")

        # --- Mitigations ---
        mitigations = []
        for t in sorted(threats, key=lambda t: SEVERITY_ORDER.get(t.get("severity", "low"), 99)):
            m = t.get("mitigation", "")
            if m and m not in mitigations:
                mitigations.append(m)
        if mitigations:
            lines.append("## Mitigations Priority List\n")
            for i, m in enumerate(mitigations, 1):
                lines.append(f"{i}. {m}")
            lines.append("")

    return "\n".join(lines)
