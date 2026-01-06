"""
Markdown Report Generator - Generate comprehensive security review reports.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from context_graph.core.models import SecurityFinding, Severity
from context_graph.security.review_engine import ReviewResult


class MarkdownReportGenerator:
    """Generate markdown security review reports."""
    
    def __init__(self) -> None:
        self.severity_icons = {
            Severity.CRITICAL: "🔴",
            Severity.HIGH: "🟠",
            Severity.MEDIUM: "🟡",
            Severity.LOW: "🟢",
            Severity.INFO: "🔵",
        }
    
    def generate(self, result: ReviewResult) -> str:
        """Generate complete markdown report."""
        sections = [
            self._generate_header(result),
            self._generate_executive_summary(result),
            self._generate_change_analysis(result),
            self._generate_findings_summary(result),
            self._generate_detailed_findings(result),
            self._generate_recommendations(result),
            self._generate_appendix(result),
        ]
        
        return "\n\n---\n\n".join(sections)
    
    def save(self, result: ReviewResult, output_path: Path) -> None:
        """Generate and save report to file."""
        report = self.generate(result)
        output_path.write_text(report, encoding="utf-8")
    
    def _generate_header(self, result: ReviewResult) -> str:
        """Generate report header."""
        return f"""# Security Review Report

**Feature:** {result.intent.title}

**Review Date:** {result.reviewed_at.strftime("%Y-%m-%d %H:%M")}

**Risk Rating:** {self._risk_badge(result.risk_rating)}

**Review ID:** `{result.review_id}`"""
    
    def _generate_executive_summary(self, result: ReviewResult) -> str:
        """Generate executive summary section."""
        findings = result.all_findings
        
        by_severity = {
            "Critical": sum(1 for f in findings if f.severity == Severity.CRITICAL),
            "High": sum(1 for f in findings if f.severity == Severity.HIGH),
            "Medium": sum(1 for f in findings if f.severity == Severity.MEDIUM),
            "Low": sum(1 for f in findings if f.severity == Severity.LOW),
        }
        
        summary = f"""## Executive Summary

{result.executive_summary}

### Findings Overview

| Severity | Count |
|----------|-------|
| 🔴 Critical | {by_severity["Critical"]} |
| 🟠 High | {by_severity["High"]} |
| 🟡 Medium | {by_severity["Medium"]} |
| 🟢 Low | {by_severity["Low"]} |
| **Total** | **{len(findings)}** |"""
        
        if result.delta_result:
            summary += f"""

### Risk Score

**{result.delta_result.delta.risk_score:.0f}/100** - {self._risk_description(result.delta_result.delta.risk_score)}"""
        
        return summary
    
    def _generate_change_analysis(self, result: ReviewResult) -> str:
        """Generate change analysis section."""
        if not result.delta_result:
            return "## Change Analysis\n\nNo delta analysis available."
        
        delta = result.delta_result
        
        sections = ["## Change Analysis", ""]
        
        # New endpoints
        if delta.new_endpoints:
            sections.append("### New API Endpoints")
            sections.append("")
            for ep in delta.new_endpoints:
                method = ep.get("method", "ANY")
                path = ep.get("path", "unknown")
                auth = "🔒" if ep.get("requires_auth") or ep.get("auth_required") else "🔓"
                sections.append(f"- `{method} {path}` {auth}")
            sections.append("")
        
        # Modified endpoints
        if delta.modified_endpoints:
            sections.append("### Modified Endpoints")
            sections.append("")
            for ep in delta.modified_endpoints:
                path = ep.get("path", "unknown")
                changes = ep.get("changes", [])
                sections.append(f"- `{path}`")
                for change in changes:
                    sections.append(f"  - {change}")
            sections.append("")
        
        # New data models
        if delta.new_data_models:
            sections.append("### New Data Models")
            sections.append("")
            for model in delta.new_data_models:
                name = model.get("name", "unknown")
                sensitive = "⚠️ Sensitive" if model.get("is_sensitive") else ""
                sections.append(f"- **{name}** {sensitive}")
            sections.append("")
        
        # Security impact
        if delta.attack_surface_changes:
            sections.append("### Attack Surface Changes")
            sections.append("")
            for change in delta.attack_surface_changes:
                sections.append(f"- {change}")
            sections.append("")
        
        if delta.trust_boundary_impacts:
            sections.append("### Trust Boundary Impacts")
            sections.append("")
            for impact in delta.trust_boundary_impacts:
                sections.append(f"- {impact}")
            sections.append("")
        
        return "\n".join(sections)
    
    def _generate_findings_summary(self, result: ReviewResult) -> str:
        """Generate findings summary table."""
        findings = result.all_findings
        
        if not findings:
            return "## Security Findings\n\nNo security findings identified. ✅"
        
        sections = [
            "## Security Findings",
            "",
            "| # | Severity | Title | Category |",
            "|---|----------|-------|----------|",
        ]
        
        for i, finding in enumerate(findings, 1):
            icon = self.severity_icons.get(finding.severity, "⚪")
            title = finding.title[:50] + "..." if len(finding.title) > 50 else finding.title
            category = finding.category.value if finding.category else "N/A"
            sections.append(f"| {i} | {icon} {finding.severity.value.title()} | {title} | {category} |")
        
        return "\n".join(sections)
    
    def _generate_detailed_findings(self, result: ReviewResult) -> str:
        """Generate detailed findings section."""
        findings = result.all_findings
        
        if not findings:
            return ""
        
        sections = ["## Detailed Findings", ""]
        
        for i, finding in enumerate(findings, 1):
            icon = self.severity_icons.get(finding.severity, "⚪")
            
            sections.append(f"### {i}. {icon} {finding.title}")
            sections.append("")
            sections.append(f"**Severity:** {finding.severity.value.title()}")
            if finding.category:
                sections.append(f"**Category:** {finding.category.value}")
            sections.append(f"**Confidence:** {finding.confidence:.0%}")
            sections.append("")
            sections.append("#### Description")
            sections.append("")
            sections.append(finding.description)
            sections.append("")
            
            if finding.recommendation:
                sections.append("#### Recommendation")
                sections.append("")
                sections.append(finding.recommendation)
                sections.append("")
            
            if finding.mitigations:
                sections.append("#### Mitigations")
                sections.append("")
                for mitigation in finding.mitigations:
                    sections.append(f"- {mitigation}")
                sections.append("")
            
            sections.append("")
        
        return "\n".join(sections)
    
    def _generate_recommendations(self, result: ReviewResult) -> str:
        """Generate prioritized recommendations."""
        findings = result.all_findings
        
        if not findings:
            return ""
        
        # Group by severity
        critical = [f for f in findings if f.severity == Severity.CRITICAL]
        high = [f for f in findings if f.severity == Severity.HIGH]
        
        sections = [
            "## Prioritized Recommendations",
            "",
            "### Immediate Actions Required",
            ""
        ]
        
        if critical:
            for f in critical:
                sections.append(f"1. **{f.title}** - {f.recommendation or 'Review and address immediately'}")
        elif high:
            sections.append("No critical findings. Address high-severity items before release:")
            for f in high:
                sections.append(f"- **{f.title}** - {f.recommendation}")
        else:
            sections.append("No critical or high-severity findings. Review medium and low severity items for defense in depth.")
        
        sections.append("")
        sections.append("### Before Production Release")
        sections.append("")
        sections.append("- [ ] All critical findings addressed")
        sections.append("- [ ] All high findings addressed or risk accepted")
        sections.append("- [ ] Security testing completed")
        sections.append("- [ ] Code review by security team")
        
        return "\n".join(sections)
    
    def _generate_appendix(self, result: ReviewResult) -> str:
        """Generate appendix with metadata."""
        sections = [
            "## Appendix",
            "",
            "### Analysis Metadata",
            "",
            f"- **PRD Title:** {result.intent.title}",
            f"- **Review Timestamp:** {result.reviewed_at.isoformat()}",
            f"- **Pattern Findings:** {len(result.pattern_findings)}",
            f"- **LLM Findings:** {len(result.llm_findings)}",
            f"- **Graph Findings:** {len(result.graph_findings)}",
            "",
        ]
        
        if result.llm_result:
            sections.append("### LLM Analysis Details")
            sections.append("")
            sections.append(f"- **Providers Used:** {', '.join(result.llm_result.providers_used)}")
            sections.append(f"- **Total Tokens:** {result.llm_result.total_tokens}")
            sections.append(f"- **Latency:** {result.llm_result.total_latency_ms:.0f}ms")
            sections.append(f"- **Average Confidence:** {result.llm_result.average_confidence:.0%}")
        
        return "\n".join(sections)
    
    def _risk_badge(self, rating: str) -> str:
        """Generate risk rating badge."""
        badges = {
            "CRITICAL": "🔴 **CRITICAL**",
            "HIGH": "🟠 **HIGH**",
            "MEDIUM": "🟡 **MEDIUM**",
            "LOW": "🟢 **LOW**",
            "MINIMAL": "✅ **MINIMAL**",
        }
        return badges.get(rating, rating)
    
    def _risk_description(self, score: float) -> str:
        """Get risk description from score."""
        if score >= 80:
            return "Critical risk - immediate attention required"
        elif score >= 60:
            return "High risk - significant security concerns"
        elif score >= 40:
            return "Medium risk - review before release"
        elif score >= 20:
            return "Low risk - minor concerns"
        else:
            return "Minimal risk"

