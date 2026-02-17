"""
JSON Report Generator - Generate machine-readable security review reports.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from context_graph.core.models import SecurityFinding, Severity
from context_graph.security.review_engine import ReviewResult


class JSONReportGenerator:
    """Generate JSON security review reports for API consumption and dashboards."""
    
    def generate(self, result: ReviewResult) -> dict[str, Any]:
        """Generate complete JSON report."""
        report: dict[str, Any] = {
            "meta": self._generate_meta(result),
            "summary": self._generate_summary(result),
            "delta": self._generate_delta(result),
            "findings": self._generate_findings(result),
            "recommendations": self._generate_recommendations(result),
            "llm_analysis": self._generate_llm_analysis(result),
        }
        
        # Include false positive filter stats if filtering was applied
        fp_stats = self._generate_fp_filter_stats(result)
        if fp_stats:
            report["false_positive_filter"] = fp_stats
        
        return report
    
    def generate_json(self, result: ReviewResult, indent: int = 2) -> str:
        """Generate JSON string."""
        data = self.generate(result)
        return json.dumps(data, indent=indent, default=str)
    
    def save(self, result: ReviewResult, output_path: Path) -> None:
        """Generate and save report to file."""
        report = self.generate_json(result)
        output_path.write_text(report, encoding="utf-8")
    
    def _generate_meta(self, result: ReviewResult) -> dict[str, Any]:
        """Generate metadata section."""
        return {
            "review_id": str(result.review_id),
            "feature_title": result.intent.title,
            "reviewed_at": result.reviewed_at.isoformat(),
            "risk_rating": result.risk_rating,
            "version": "1.0",
        }
    
    def _generate_summary(self, result: ReviewResult) -> dict[str, Any]:
        """Generate summary section."""
        findings = result.all_findings
        
        return {
            "total_findings": len(findings),
            "by_severity": {
                "critical": sum(1 for f in findings if f.severity == Severity.CRITICAL),
                "high": sum(1 for f in findings if f.severity == Severity.HIGH),
                "medium": sum(1 for f in findings if f.severity == Severity.MEDIUM),
                "low": sum(1 for f in findings if f.severity == Severity.LOW),
                "info": sum(1 for f in findings if f.severity == Severity.INFO),
            },
            "risk_score": result.delta_result.delta.risk_score if result.delta_result else 0,
            "executive_summary": result.executive_summary,
        }
    
    def _generate_delta(self, result: ReviewResult) -> dict[str, Any]:
        """Generate delta section."""
        if not result.delta_result:
            return {}
        
        delta = result.delta_result
        
        return {
            "summary": delta.delta.summary,
            "new_endpoints": delta.new_endpoints,
            "modified_endpoints": delta.modified_endpoints,
            "new_data_models": delta.new_data_models,
            "new_data_flows": delta.new_data_flows,
            "attack_surface_changes": delta.attack_surface_changes,
            "trust_boundary_impacts": delta.trust_boundary_impacts,
            "auth_requirement_changes": delta.auth_requirement_changes,
            "risk_indicators": {
                "introduces_pii": delta.introduces_pii,
                "introduces_external_integration": delta.introduces_external_integration,
                "modifies_auth_flow": delta.modifies_auth_flow,
                "expands_attack_surface": delta.expands_attack_surface,
            },
        }
    
    def _generate_findings(self, result: ReviewResult) -> list[dict[str, Any]]:
        """Generate findings list."""
        return [
            {
                "id": str(finding.id),
                "title": finding.title,
                "description": finding.description,
                "severity": finding.severity.value,
                "category": finding.category.value if finding.category else None,
                "confidence": finding.confidence,
                "source_type": finding.source_type,
                "source_reference": finding.source_reference,
                "recommendation": finding.recommendation,
                "mitigations": finding.mitigations,
                "found_at": finding.found_at.isoformat(),
            }
            for finding in result.all_findings
        ]
    
    def _generate_recommendations(self, result: ReviewResult) -> dict[str, Any]:
        """Generate recommendations section."""
        findings = result.all_findings
        
        critical = [f for f in findings if f.severity == Severity.CRITICAL]
        high = [f for f in findings if f.severity == Severity.HIGH]
        
        return {
            "immediate_actions": [
                {
                    "finding_id": str(f.id),
                    "title": f.title,
                    "action": f.recommendation or "Review and address immediately",
                }
                for f in critical
            ],
            "before_release": [
                {
                    "finding_id": str(f.id),
                    "title": f.title,
                    "action": f.recommendation,
                }
                for f in high
            ],
            "checklist": [
                {"item": "All critical findings addressed", "required": True},
                {"item": "All high findings addressed or risk accepted", "required": True},
                {"item": "Security testing completed", "required": True},
                {"item": "Code review by security team", "required": False},
            ],
        }
    
    def _generate_llm_analysis(self, result: ReviewResult) -> dict[str, Any] | None:
        """Generate LLM analysis details."""
        if not result.llm_result:
            return None
        
        return {
            "providers_used": result.llm_result.providers_used,
            "total_tokens": result.llm_result.total_tokens,
            "total_latency_ms": result.llm_result.total_latency_ms,
            "average_confidence": result.llm_result.average_confidence,
            "consensus_items_count": len(result.llm_result.consensus_items),
            "divergent_items_count": len(result.llm_result.divergent_items),
        }
    
    def _generate_fp_filter_stats(self, result: ReviewResult) -> dict[str, Any] | None:
        """Generate false positive filter statistics."""
        if not result.fp_filter_stats:
            return None
        
        total_original = sum(s.original_count for s in result.fp_filter_stats)
        total_final = sum(s.final_count for s in result.fp_filter_stats)
        total_removed = sum(s.total_removed for s in result.fp_filter_stats)
        total_downgraded = sum(s.total_downgraded for s in result.fp_filter_stats)
        
        if total_removed == 0 and total_downgraded == 0:
            return None
        
        # Determine execution mode from the first stat entry
        exec_mode = result.fp_filter_stats[0].execution_mode if result.fp_filter_stats else "unknown"

        return {
            "enabled": True,
            "execution_mode": exec_mode,
            "total_original_findings": total_original,
            "total_final_findings": total_final,
            "total_removed": total_removed,
            "total_downgraded": total_downgraded,
            "overall_removal_rate": round(total_removed / total_original, 3) if total_original > 0 else 0,
            "by_dimension": [
                {
                    "dimension": stat.dimension,
                    "execution_mode": stat.execution_mode,
                    "original_count": stat.original_count,
                    "final_count": stat.final_count,
                    "removed": stat.total_removed,
                    "downgraded": stat.total_downgraded,
                    "strategies_run": stat.total_iterations,
                    "removal_rate": round(stat.removal_rate, 3),
                    "iteration_details": stat.iteration_details,
                }
                for stat in result.fp_filter_stats
                if stat.total_removed > 0 or stat.total_downgraded > 0
            ],
        }


class DashboardDataGenerator:
    """Generate data specifically formatted for dashboard visualization."""
    
    def generate(self, result: ReviewResult) -> dict[str, Any]:
        """Generate dashboard-friendly data."""
        return {
            "overview": self._overview_card(result),
            "severity_chart": self._severity_chart_data(result),
            "category_chart": self._category_chart_data(result),
            "risk_gauge": self._risk_gauge_data(result),
            "timeline": self._timeline_data(result),
            "findings_table": self._findings_table_data(result),
            "delta_summary": self._delta_summary_data(result),
            "llm_analysis": self._llm_analysis_data(result),
        }
    
    def _llm_analysis_data(self, result: ReviewResult) -> dict[str, Any] | None:
        """Data for LLM analysis section."""
        if not result.llm_result:
            return None
        
        # Extract detailed threat analysis from LLM responses
        threat_analysis = {}
        summary_details = {}
        
        for response in result.llm_result.responses:
            if response.structured_data:
                # Get threat analysis if available
                if "threat_analysis" in response.structured_data:
                    threat_analysis = response.structured_data["threat_analysis"]
                # Get detailed summary if available
                if "summary" in response.structured_data:
                    summary_details = response.structured_data["summary"]
        
        return {
            "used": True,
            "providers": result.llm_result.providers_used,
            "findings_count": len(result.llm_findings),
            "consensus_count": len(result.llm_result.consensus_items),
            "total_tokens": result.llm_result.total_tokens,
            "latency_ms": result.llm_result.total_latency_ms,
            "threat_analysis": threat_analysis,
            "summary_details": summary_details,
        }
    
    def _overview_card(self, result: ReviewResult) -> dict[str, Any]:
        """Data for overview card."""
        findings = result.all_findings
        
        # Count findings by dimension
        dimension_counts = {
            "security": len(result.security_findings),
            "privacy": len(result.privacy_findings),
            "compliance": len(result.compliance_findings),
            "engineering": len(result.engineering_findings),
            "architecture": len(result.architecture_findings),
        }
        
        # Get dimensions that were analyzed
        dimensions_analyzed = [d.value for d in result.dimensions_analyzed]
        
        return {
            "title": result.intent.title,
            "risk_rating": result.risk_rating,
            "total_findings": len(findings),
            "critical_count": result.critical_count,
            "high_count": result.high_count,
            "reviewed_at": result.reviewed_at.isoformat(),
            "dimensions_analyzed": dimensions_analyzed,
            "dimension_counts": dimension_counts,
        }
    
    def _severity_chart_data(self, result: ReviewResult) -> dict[str, Any]:
        """Data for severity pie/bar chart."""
        findings = result.all_findings
        
        return {
            "type": "pie",
            "labels": ["Critical", "High", "Medium", "Low", "Info"],
            "data": [
                sum(1 for f in findings if f.severity == Severity.CRITICAL),
                sum(1 for f in findings if f.severity == Severity.HIGH),
                sum(1 for f in findings if f.severity == Severity.MEDIUM),
                sum(1 for f in findings if f.severity == Severity.LOW),
                sum(1 for f in findings if f.severity == Severity.INFO),
            ],
            "colors": ["#ef4444", "#f97316", "#eab308", "#22c55e", "#3b82f6"],
        }
    
    def _category_chart_data(self, result: ReviewResult) -> dict[str, Any]:
        """Data for category bar chart."""
        findings = result.all_findings
        
        category_counts: dict[str, int] = {}
        for finding in findings:
            cat = finding.category.value if finding.category else "other"
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        return {
            "type": "bar",
            "labels": list(category_counts.keys()),
            "data": list(category_counts.values()),
        }
    
    def _risk_gauge_data(self, result: ReviewResult) -> dict[str, Any]:
        """Data for risk score gauge."""
        score = result.delta_result.delta.risk_score if result.delta_result else 0
        
        return {
            "type": "gauge",
            "value": score,
            "min": 0,
            "max": 100,
            "thresholds": [
                {"value": 20, "color": "#22c55e", "label": "Low"},
                {"value": 40, "color": "#eab308", "label": "Medium"},
                {"value": 60, "color": "#f97316", "label": "High"},
                {"value": 100, "color": "#ef4444", "label": "Critical"},
            ],
        }
    
    def _timeline_data(self, result: ReviewResult) -> list[dict[str, Any]]:
        """Data for findings timeline."""
        return [
            {
                "time": finding.found_at.isoformat(),
                "title": finding.title,
                "severity": finding.severity.value,
            }
            for finding in result.all_findings
        ]
    
    def _findings_table_data(self, result: ReviewResult) -> list[dict[str, Any]]:
        """Data for findings table with detailed LLM analysis."""
        findings_data = []
        
        # Get detailed findings from all LLM responses if available
        llm_findings_details = {}
        
        # Collect from all LLM results (security, privacy, compliance, engineering, architecture)
        llm_results = [
            result.llm_result,  # security
            result.privacy_llm_result,
            result.compliance_llm_result,
            result.engineering_llm_result,
            result.architecture_llm_result,
        ]
        
        for llm_result in llm_results:
            if llm_result:
                for response in llm_result.responses:
                    if response.structured_data and "findings" in response.structured_data:
                        for f in response.structured_data["findings"]:
                            if "id" in f:
                                llm_findings_details[f["id"]] = f
        
        for finding in result.all_findings:
            finding_id = str(finding.id)
            
            # Try to get detailed LLM data for this finding
            llm_detail = llm_findings_details.get(finding_id, {})
            
            # Get dimension from finding
            dimension = getattr(finding, 'dimension', None)
            dimension_value = dimension.value if dimension else "unknown"
            
            findings_data.append({
                "id": finding_id,
                "severity": finding.severity.value,
                "severity_order": ["critical", "high", "medium", "low", "info"].index(
                    finding.severity.value
                ),
                "title": finding.title,
                "description": finding.description or llm_detail.get("description", ""),
                "category": finding.category.value if finding.category else llm_detail.get("category", "N/A"),
                "dimension": dimension_value,  # security, privacy, or compliance
                "confidence": f"{finding.confidence:.0%}",
                "recommendation": finding.recommendation or llm_detail.get("recommendation", "—"),
                "source_type": finding.source_type or "pattern",
                "source_reference": finding.source_reference or "",
                # Additional LLM details
                "technical_details": llm_detail.get("technical_details", ""),
                "attack_scenario": llm_detail.get("attack_scenario", ""),
                "business_impact": llm_detail.get("business_impact", ""),
                "affected_components": llm_detail.get("affected_components", []),
                "prerequisites": llm_detail.get("prerequisites", ""),
                "implementation_guidance": llm_detail.get("implementation_guidance", ""),
                "references": llm_detail.get("references", []),
            })
        
        return findings_data
    
    def _delta_summary_data(self, result: ReviewResult) -> dict[str, Any]:
        """Data for delta summary cards."""
        if not result.delta_result:
            return {}
        
        delta = result.delta_result
        
        return {
            "cards": [
                {
                    "label": "New Endpoints",
                    "value": len(delta.new_endpoints),
                    "icon": "api",
                },
                {
                    "label": "Modified Endpoints",
                    "value": len(delta.modified_endpoints),
                    "icon": "edit",
                },
                {
                    "label": "New Data Models",
                    "value": len(delta.new_data_models),
                    "icon": "database",
                },
                {
                    "label": "External Integrations",
                    "value": 1 if delta.introduces_external_integration else 0,
                    "icon": "link",
                },
            ],
            "flags": {
                "introduces_pii": delta.introduces_pii,
                "modifies_auth": delta.modifies_auth_flow,
                "expands_attack_surface": delta.expands_attack_surface,
            },
        }

