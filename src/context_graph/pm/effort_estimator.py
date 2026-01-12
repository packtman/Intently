"""
Effort Estimator - Code-grounded time estimates for PRD implementation.

Uses codebase analysis to estimate:
- How long implementation will take
- Which patterns already exist
- Complexity of required changes
"""

from __future__ import annotations

from context_graph.core.models import (
    EffortEstimation,
    Finding,
    EngineeringFinding,
    ArchitectureFinding,
    State,
)


class EffortEstimator:
    """Estimates implementation effort based on codebase analysis."""
    
    def estimate(
        self,
        findings: list[Finding],
        codebase_state: State | None = None,
    ) -> EffortEstimation:
        """
        Estimate implementation effort.
        
        Args:
            findings: List of findings that need to be addressed
            codebase_state: Current codebase state for pattern matching
            
        Returns:
            EffortEstimation with time estimates and codebase support
        """
        # Calculate codebase support (percentage of patterns that exist)
        codebase_support = self._calculate_codebase_support(findings, codebase_state)
        
        # Estimate effort from engineering/architecture findings
        engineering_findings = [f for f in findings if isinstance(f, (EngineeringFinding, ArchitectureFinding))]
        
        # Base estimate: 1 day per finding (adjusted by complexity)
        total_days_min = 0
        total_days_likely = 0
        total_days_max = 0
        
        by_requirement = []
        
        for finding in findings:
            days = self._estimate_finding_effort(finding)
            
            total_days_min += days["min"]
            total_days_likely += days["likely"]
            total_days_max += days["max"]
            
            by_requirement.append({
                "title": finding.title,
                "min_days": days["min"],
                "likely_days": days["likely"],
                "max_days": days["max"],
                "dimension": finding.dimension.value if hasattr(finding.dimension, 'value') else str(finding.dimension),
            })
        
        # Adjust based on codebase support
        # If 80%+ patterns exist, reduce estimate by 20%
        if codebase_support >= 80:
            total_days_min = int(total_days_min * 0.8)
            total_days_likely = int(total_days_likely * 0.8)
            total_days_max = int(total_days_max * 0.8)
        elif codebase_support >= 60:
            total_days_min = int(total_days_min * 0.9)
            total_days_likely = int(total_days_likely * 0.9)
            total_days_max = int(total_days_max * 0.9)
        
        # Generate TLDR
        tldr = self._generate_tldr(total_days_likely, total_days_max, codebase_support, len(findings))
        
        return EffortEstimation(
            total_days={
                "min": total_days_min,
                "likely": total_days_likely,
                "max": total_days_max,
            },
            by_requirement=by_requirement,
            codebase_support=codebase_support,
            tldr=tldr,
        )
    
    def _estimate_finding_effort(self, finding: Finding) -> dict[str, int]:
        """Estimate effort for a single finding."""
        # Use existing estimates if available (engineering findings)
        if isinstance(finding, EngineeringFinding) and finding.estimated_days:
            # Parse "1-2 days" format
            days = self._parse_days_string(finding.estimated_days)
            if days:
                return {
                    "min": days["min"],
                    "likely": days["likely"],
                    "max": days["max"],
                }
        
        # Estimate based on severity
        severity_multiplier = {
            "critical": 3,
            "high": 2,
            "medium": 1,
            "low": 0.5,
            "info": 0.25,
        }
        
        severity = finding.severity.value if hasattr(finding.severity, 'value') else str(finding.severity)
        multiplier = severity_multiplier.get(severity, 1)
        
        base_days = 1 * multiplier
        
        return {
            "min": max(1, int(base_days * 0.5)),
            "likely": max(1, int(base_days)),
            "max": max(1, int(base_days * 2)),
        }
    
    def _parse_days_string(self, days_str: str) -> dict[str, int] | None:
        """Parse a days string like '1-2 days' or '1 week'."""
        import re
        
        # Match "1-2 days" or "1-2 weeks"
        match = re.match(r"(\d+)-(\d+)\s*(day|week)", days_str.lower())
        if match:
            min_val = int(match.group(1))
            max_val = int(match.group(2))
            unit = match.group(3)
            multiplier = 7 if unit == "week" else 1
            return {
                "min": min_val * multiplier,
                "likely": int((min_val + max_val) / 2) * multiplier,
                "max": max_val * multiplier,
            }
        
        # Match single number
        match = re.match(r"(\d+)\s*(day|week)", days_str.lower())
        if match:
            val = int(match.group(1))
            unit = match.group(2)
            multiplier = 7 if unit == "week" else 1
            return {
                "min": val * multiplier,
                "likely": val * multiplier,
                "max": val * multiplier * 2,
            }
        
        return None
    
    def _calculate_codebase_support(
        self,
        findings: list[Finding],
        codebase_state: State | None = None,
    ) -> float:
        """Calculate percentage of patterns that already exist in codebase."""
        if not codebase_state:
            return 0.0
        
        # Count findings that reference existing code patterns
        supported = 0
        total = len(findings)
        
        if total == 0:
            return 100.0
        
        for finding in findings:
            # If finding has source_reference, it means we found related code
            if finding.source_reference:
                supported += 1
            # If it's an engineering finding with affected_files, patterns exist
            elif isinstance(finding, EngineeringFinding) and finding.affected_files:
                supported += 1
        
        return (supported / total) * 100.0
    
    def _generate_tldr(
        self,
        likely_days: int,
        max_days: int,
        codebase_support: float,
        finding_count: int,
    ) -> str:
        """Generate human-readable summary."""
        # Calculate sprints (assuming 2-week sprints)
        sprints = likely_days / 10
        
        parts = []
        
        if likely_days > 0:
            parts.append(f"{likely_days} days")
        
        if sprints >= 1:
            parts.append(f"{sprints:.1f} sprints")
        
        if codebase_support > 0:
            parts.append(f"{codebase_support:.0f}% patterns exist")
        
        return ", ".join(parts) if parts else "Estimation pending"
