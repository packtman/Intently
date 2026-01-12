"""
PRD Change Generator - Converts findings into diff-style PRD suggestions.

This module implements the core PM-focused feature: converting security/engineering
findings into actionable PRD changes that PMs can accept/reject with one click.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from context_graph.core.models import (
    Finding,
    SecurityFinding,
    PrivacyFinding,
    ComplianceFinding,
    EngineeringFinding,
    ArchitectureFinding,
    PredictedQuestion,
    PRDChange,
    CodeEvidence,
    DiffHunk,
    ReviewDimension,
    Severity,
)


class PRDChangeGenerator:
    """Generates PRD changes from findings."""
    
    # Map dimensions to team names
    DIMENSION_TO_TEAM = {
        ReviewDimension.SECURITY: "security",
        ReviewDimension.PRIVACY: "privacy",
        ReviewDimension.COMPLIANCE: "compliance",
        ReviewDimension.ENGINEERING: "engineering",
        ReviewDimension.ARCHITECTURE: "infrastructure",
    }
    
    # Map severity to prediction severity
    SEVERITY_TO_PREDICTION = {
        Severity.CRITICAL: "blocker",
        Severity.HIGH: "blocker",
        Severity.MEDIUM: "likely",
        Severity.LOW: "possible",
        Severity.INFO: "possible",
    }
    
    def generate_changes(
        self,
        findings: list[Finding],
        prd_content: str,
        codebase_state: dict[str, Any] | None = None,
    ) -> list[PredictedQuestion]:
        """
        Generate predicted questions and PRD changes from findings.
        
        Args:
            findings: List of findings from review
            prd_content: Current PRD content
            codebase_state: Optional codebase state for code evidence
            
        Returns:
            List of predicted questions with associated PRD changes
        """
        predicted_questions = []
        
        for finding in findings:
            # Convert finding to predicted question
            question = self._finding_to_question(finding, codebase_state)
            
            # Generate PRD change for this question
            prd_change = self._generate_prd_change(finding, prd_content)
            question.suggested_change = prd_change
            
            predicted_questions.append(question)
        
        return predicted_questions
    
    def _finding_to_question(
        self,
        finding: Finding,
        codebase_state: dict[str, Any] | None = None,
    ) -> PredictedQuestion:
        """Convert a finding to a predicted question."""
        team = self.DIMENSION_TO_TEAM.get(finding.dimension, "engineering")
        severity = self.SEVERITY_TO_PREDICTION.get(finding.severity, "likely")
        
        # Generate question from finding title/description
        question_text = self._generate_question_text(finding)
        
        # Extract code evidence
        code_evidence = self._extract_code_evidence(finding, codebase_state)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(finding, code_evidence)
        
        return PredictedQuestion(
            question=question_text,
            team=team,
            severity=severity,
            reasoning=reasoning,
            code_evidence=code_evidence,
        )
    
    def _generate_question_text(self, finding: Finding) -> str:
        """Generate a question that a team would ask based on the finding."""
        # Use finding title as base, convert to question format
        title = finding.title
        
        # If title already looks like a question, use it
        if title.endswith("?") or title.startswith("What") or title.startswith("How"):
            return title
        
        # Convert statement to question
        # Pattern: "Missing rate limiting" -> "What about rate limiting?"
        # Pattern: "Session handling not specified" -> "What happens to existing sessions?"
        
        if "missing" in title.lower() or "not specified" in title.lower():
            # Extract the key concept
            key_concept = self._extract_key_concept(title)
            return f"What about {key_concept}?"
        elif "unclear" in title.lower() or "not clear" in title.lower():
            key_concept = self._extract_key_concept(title)
            return f"Can you clarify {key_concept}?"
        else:
            # Generic conversion
            return f"{title}?"
    
    def _extract_key_concept(self, text: str) -> str:
        """Extract the key concept from a finding title."""
        # Remove common prefixes
        text = re.sub(r"^(missing|no|unclear|not specified|lack of)\s+", "", text, flags=re.IGNORECASE)
        # Take first few words
        words = text.split()[:3]
        return " ".join(words).lower()
    
    def _extract_code_evidence(
        self,
        finding: Finding,
        codebase_state: dict[str, Any] | None = None,
    ) -> list[CodeEvidence]:
        """Extract code evidence from finding."""
        evidence = []
        
        # Use source_reference if available
        if finding.source_reference:
            # Try to parse file path and line number
            if ":" in finding.source_reference:
                parts = finding.source_reference.split(":")
                file_path = parts[0]
                line_num = int(parts[1]) if parts[1].isdigit() else None
                
                evidence.append(CodeEvidence(
                    file_path=file_path,
                    line_number=line_num,
                    context=finding.description or "",
                ))
            else:
                evidence.append(CodeEvidence(
                    file_path=finding.source_reference,
                    context=finding.description or "",
                ))
        
        # For engineering findings, use affected_files
        if isinstance(finding, EngineeringFinding) and finding.affected_files:
            for file_path in finding.affected_files[:3]:  # Limit to 3 files
                evidence.append(CodeEvidence(
                    file_path=file_path,
                    context="Affected by this finding",
                ))
        
        return evidence
    
    def _generate_reasoning(
        self,
        finding: Finding,
        code_evidence: list[CodeEvidence],
    ) -> str:
        """Generate reasoning text explaining why this question will be asked."""
        parts = []
        
        # Add code evidence context
        if code_evidence:
            evidence_text = ", ".join([e.file_path for e in code_evidence[:2]])
            parts.append(f"Found in codebase: {evidence_text}")
        
        # Add finding description
        if finding.description:
            parts.append(finding.description)
        elif finding.recommendation:
            parts.append(finding.recommendation)
        
        return ". ".join(parts) if parts else "Based on codebase analysis"
    
    def _generate_prd_change(
        self,
        finding: Finding,
        prd_content: str,
    ) -> PRDChange:
        """Generate a PRD change suggestion from a finding."""
        # Determine section based on finding dimension
        section = self._determine_section(finding)
        
        # Find contextually appropriate insertion point in PRD
        # (not just end of section, but near related content)
        start_line, end_line = self._find_insertion_point(prd_content, section, finding)
        
        # Generate suggested text
        suggested_text = self._generate_suggested_text(finding, section)
        
        # Get current text at that location
        current_text = self._get_current_text(prd_content, start_line, end_line)
        
        # Determine change type
        change_type = "addition" if not current_text.strip() else "modification"
        
        # Generate diff hunks
        diff_hunks = self._generate_diff_hunks(current_text, suggested_text, start_line)
        
        return PRDChange(
            section=section,
            start_line=start_line,
            end_line=end_line,
            change_type=change_type,
            current_text=current_text,
            suggested_text=suggested_text,
            diff_hunks=diff_hunks,
            reasoning=finding.recommendation or finding.description or "Based on codebase analysis",
        )
    
    def _determine_section(self, finding: Finding) -> str:
        """Determine which PRD section this change belongs to."""
        dimension = finding.dimension
        
        section_map = {
            ReviewDimension.SECURITY: "## Security Requirements",
            ReviewDimension.PRIVACY: "## Privacy Requirements",
            ReviewDimension.COMPLIANCE: "## Compliance Requirements",
            ReviewDimension.ENGINEERING: "## Technical Requirements",
            ReviewDimension.ARCHITECTURE: "## Architecture Requirements",
        }
        
        return section_map.get(dimension, "## Technical Requirements")
    
    def _find_insertion_point(
        self,
        prd_content: str,
        section: str,
        finding: Finding | None = None,
    ) -> tuple[int, int]:
        """
        Find the contextually appropriate location to insert the change in the PRD.
        
        Unlike simple "append to end of section", this method:
        1. Searches for related content within the section
        2. Inserts near semantically similar content (e.g., auth near auth, data near data)
        3. Respects document structure (after existing bullets, near related subsections)
        """
        lines = prd_content.split("\n")
        
        # Find section boundaries
        section_line = -1
        for i, line in enumerate(lines):
            if section.lower() in line.lower() and line.startswith("#"):
                section_line = i
                break
        
        if section_line == -1:
            # Section doesn't exist, append at end
            return len(lines), len(lines)
        
        # Find end of section (next heading at same or higher level)
        section_level = len(lines[section_line]) - len(lines[section_line].lstrip("#"))
        section_end = section_line + 1
        
        for i in range(section_line + 1, len(lines)):
            if lines[i].startswith("#"):
                line_level = len(lines[i]) - len(lines[i].lstrip("#"))
                if line_level <= section_level:
                    section_end = i
                    break
            section_end = i + 1
        
        # Now find the best insertion point WITHIN the section
        # Strategy: Find related content by keywords from the finding
        if finding:
            best_line = self._find_related_content(
                lines, section_line + 1, section_end, finding
            )
            if best_line is not None:
                return best_line, best_line
        
        # Fallback: Find a logical insertion point
        # Prefer: after existing bullet points, before next subsection
        insertion_line = self._find_logical_insertion_point(
            lines, section_line + 1, section_end
        )
        
        return insertion_line, insertion_line

    def _find_related_content(
        self,
        lines: list[str],
        start: int,
        end: int,
        finding: Finding,
    ) -> int | None:
        """Find line number of content related to this finding."""
        # Extract keywords from finding
        keywords = self._extract_keywords_from_finding(finding)
        if not keywords:
            return None
        
        # Score each line by keyword matches
        best_score = 0
        best_line = None
        
        for i in range(start, end):
            line_lower = lines[i].lower()
            score = sum(1 for kw in keywords if kw in line_lower)
            
            if score > best_score:
                best_score = score
                best_line = i
        
        # Only use if we found meaningful match (at least 1 keyword)
        if best_score > 0 and best_line is not None:
            # Insert AFTER the related line (next line)
            return best_line + 1
        
        return None

    def _extract_keywords_from_finding(self, finding: Finding) -> list[str]:
        """Extract searchable keywords from a finding."""
        keywords = []
        
        # Extract from title
        if finding.title:
            # Split and filter common words
            title_words = finding.title.lower().split()
            stopwords = {"the", "a", "an", "is", "are", "for", "to", "in", "of", "and", "or", "not", "be", "this", "that"}
            keywords.extend(w for w in title_words if w not in stopwords and len(w) > 2)
        
        # Add dimension-specific keywords
        dimension_keywords = {
            ReviewDimension.SECURITY: ["authentication", "authorization", "token", "session", "encrypt", "tls", "ssl", "access"],
            ReviewDimension.PRIVACY: ["data", "consent", "gdpr", "pii", "personal", "retention", "delete"],
            ReviewDimension.COMPLIANCE: ["audit", "log", "compliance", "regulation", "control"],
            ReviewDimension.ENGINEERING: ["api", "endpoint", "database", "performance", "scale"],
            ReviewDimension.ARCHITECTURE: ["service", "component", "integration", "dependency"],
        }
        
        if finding.dimension in dimension_keywords:
            keywords.extend(dimension_keywords[finding.dimension])
        
        return list(set(keywords))[:10]  # Limit to prevent over-matching

    def _find_logical_insertion_point(
        self,
        lines: list[str],
        start: int,
        end: int,
    ) -> int:
        """Find a logical place to insert content within a section."""
        # Strategy:
        # 1. If section has bullet points, insert after last bullet
        # 2. If section has subsections, insert before first subsection
        # 3. Otherwise, insert after first non-empty line (skip blank line after header)
        
        last_bullet_line = None
        first_subsection_line = None
        first_content_line = None
        
        for i in range(start, end):
            line = lines[i].strip()
            
            if line.startswith("- ") or line.startswith("* ") or (line and line[0].isdigit() and "." in line[:3]):
                last_bullet_line = i
            elif line.startswith("###"):
                if first_subsection_line is None:
                    first_subsection_line = i
            elif line and first_content_line is None:
                first_content_line = i
        
        # Priority: after last bullet > before subsection > after first content > start
        if last_bullet_line is not None:
            return last_bullet_line + 1
        if first_subsection_line is not None:
            return first_subsection_line
        if first_content_line is not None:
            return first_content_line + 1
        
        return start
    
    def _get_current_text(self, prd_content: str, start_line: int, end_line: int) -> str:
        """Get current text at the specified lines."""
        lines = prd_content.split("\n")
        if start_line >= len(lines):
            return ""
        return "\n".join(lines[start_line:end_line])
    
    def _generate_suggested_text(self, finding: Finding, section: str) -> str:
        """Generate the suggested text to add to PRD."""
        # Use recommendation if available, otherwise generate from finding
        if finding.recommendation:
            # Format as bullet point
            if not finding.recommendation.startswith("-"):
                return f"- {finding.recommendation}"
            return finding.recommendation
        
        # Generate from finding title/description
        if isinstance(finding, SecurityFinding):
            return self._generate_security_suggestion(finding)
        elif isinstance(finding, PrivacyFinding):
            return self._generate_privacy_suggestion(finding)
        elif isinstance(finding, ComplianceFinding):
            return self._generate_compliance_suggestion(finding)
        elif isinstance(finding, EngineeringFinding):
            return self._generate_engineering_suggestion(finding)
        elif isinstance(finding, ArchitectureFinding):
            return self._generate_architecture_suggestion(finding)
        else:
            # Generic
            return f"- {finding.title}"
    
    def _generate_security_suggestion(self, finding: SecurityFinding) -> str:
        """Generate security-specific suggestion."""
        # Use mitigations if available
        if finding.mitigations:
            return "\n".join([f"- {m}" for m in finding.mitigations])
        
        # Generate from category
        category_suggestions = {
            "injection": "- Input validation on all endpoints",
            "broken_authentication": "- Authentication required for this feature",
            "sensitive_data_exposure": "- Encryption required for sensitive data",
            "broken_access_control": "- Access control checks required",
            "security_misconfiguration": "- Security configuration review needed",
        }
        
        category_key = finding.category.value if hasattr(finding.category, 'value') else str(finding.category)
        if category_key in category_suggestions:
            return category_suggestions[category_key]
        
        return f"- {finding.title}"
    
    def _generate_privacy_suggestion(self, finding: PrivacyFinding) -> str:
        """Generate privacy-specific suggestion."""
        suggestions = []
        
        if finding.consent_required:
            suggestions.append("- User consent required for data processing")
        if finding.legal_basis_required:
            suggestions.append("- Legal basis for processing must be documented")
        if finding.applicable_regulations:
            regs = ", ".join(finding.applicable_regulations)
            suggestions.append(f"- Compliance with {regs} required")
        
        if finding.mitigations:
            suggestions.extend([f"- {m}" for m in finding.mitigations])
        
        return "\n".join(suggestions) if suggestions else f"- {finding.title}"
    
    def _generate_compliance_suggestion(self, finding: ComplianceFinding) -> str:
        """Generate compliance-specific suggestion."""
        suggestions = []
        
        if finding.control_id:
            suggestions.append(f"- {finding.framework.value.upper()} Control {finding.control_id}: {finding.control_description}")
        if finding.gap_description:
            suggestions.append(f"- Gap: {finding.gap_description}")
        if finding.mitigations:
            suggestions.extend([f"- {m}" for m in finding.mitigations])
        
        return "\n".join(suggestions) if suggestions else f"- {finding.title}"
    
    def _generate_engineering_suggestion(self, finding: EngineeringFinding) -> str:
        """Generate engineering-specific suggestion."""
        suggestions = []
        
        if finding.estimated_days:
            suggestions.append(f"- Estimated effort: {finding.estimated_days}")
        if finding.refactoring_suggestions:
            suggestions.extend([f"- {s}" for s in finding.refactoring_suggestions[:3]])
        if finding.mitigations:
            suggestions.extend([f"- {m}" for m in finding.mitigations])
        
        return "\n".join(suggestions) if suggestions else f"- {finding.title}"
    
    def _generate_architecture_suggestion(self, finding: ArchitectureFinding) -> str:
        """Generate architecture-specific suggestion."""
        suggestions = []
        
        if finding.design_alternatives:
            suggestions.append("### Design Alternatives:")
            suggestions.extend([f"- {alt}" for alt in finding.design_alternatives[:3]])
        if finding.mitigations:
            suggestions.extend([f"- {m}" for m in finding.mitigations])
        
        return "\n".join(suggestions) if suggestions else f"- {finding.title}"
    
    def _generate_diff_hunks(
        self,
        current_text: str,
        suggested_text: str,
        start_line: int,
    ) -> list[DiffHunk]:
        """Generate diff hunks for rendering."""
        hunks = []
        
        # Add context (current text)
        if current_text.strip():
            for i, line in enumerate(current_text.split("\n")):
                hunks.append(DiffHunk(
                    operation="context",
                    content=line,
                    line_number=start_line + i,
                ))
        
        # Add new lines
        for line in suggested_text.split("\n"):
            if line.strip():
                hunks.append(DiffHunk(
                    operation="add",
                    content=line,
                    line_number=None,  # New line, no original line number
                ))
        
        return hunks
