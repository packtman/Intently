"""
PRD Templates Library — built-in and organization-specific templates.

Templates encode required sections, guidance text, and boilerplate.
They evolve based on review patterns — commonly flagged gaps become
required sections in templates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TemplateSection:
    """A section in a PRD template."""

    title: str
    required: bool = False
    guidance: str = ""
    boilerplate: str = ""


@dataclass
class PRDTemplate:
    """A PRD template with sections and metadata."""

    id: str
    name: str
    description: str
    category: str  # "feature", "api", "migration", "integration", "deprecation"
    sections: list[TemplateSection] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


class TemplateLibrary:
    """Manages built-in and org-specific PRD templates."""

    BUILT_IN_TEMPLATES: list[PRDTemplate] = [
        PRDTemplate(
            id="new-feature",
            name="New Feature",
            description="Standard template for new product features",
            category="feature",
            sections=[
                TemplateSection("Overview", required=True, guidance="What does this feature do and why?"),
                TemplateSection("User Stories", required=True, guidance="As a [user], I want [goal], so that [benefit]."),
                TemplateSection("Technical Requirements", required=True, guidance="Describe the technical implementation needed."),
                TemplateSection("API Changes", required=False, guidance="New or modified API endpoints."),
                TemplateSection("Data Model Changes", required=False, guidance="New tables, fields, or schema changes."),
                TemplateSection("Security Considerations", required=True, guidance="Authentication, authorization, data protection, trust boundaries."),
                TemplateSection("Privacy Impact", required=False, guidance="PII handling, data flows, consent requirements."),
                TemplateSection("Rollback Plan", required=True, guidance="How to revert if issues arise post-deployment."),
                TemplateSection("Acceptance Criteria", required=True, guidance="How do we know this is done and working?"),
            ],
            keywords=["feature", "new", "add", "implement", "build", "create"],
        ),
        PRDTemplate(
            id="api-change",
            name="API Change",
            description="Template for API modifications, additions, or deprecations",
            category="api",
            sections=[
                TemplateSection("Overview", required=True, guidance="What API changes are being made and why?"),
                TemplateSection("Current API State", required=True, guidance="Document the existing endpoints being changed."),
                TemplateSection("Proposed Changes", required=True, guidance="New endpoints, modified parameters, changed responses."),
                TemplateSection("Breaking Changes", required=True, guidance="List any breaking changes and migration path."),
                TemplateSection("Versioning Strategy", required=True, guidance="How will API versions be managed?"),
                TemplateSection("Authentication & Authorization", required=True, guidance="Auth requirements for new/changed endpoints."),
                TemplateSection("Rate Limiting", required=False, guidance="Rate limit configurations for new endpoints."),
                TemplateSection("Error Handling", required=True, guidance="Error responses and status codes."),
                TemplateSection("Migration Guide", required=False, guidance="Steps for consumers to migrate to the new API."),
                TemplateSection("Rollback Plan", required=True, guidance="How to revert API changes."),
            ],
            keywords=["api", "endpoint", "rest", "graphql", "route", "request", "response"],
        ),
        PRDTemplate(
            id="data-migration",
            name="Data Migration",
            description="Template for database schema changes and data migrations",
            category="migration",
            sections=[
                TemplateSection("Overview", required=True, guidance="What data is being migrated and why?"),
                TemplateSection("Current Schema", required=True, guidance="Describe the current data structure."),
                TemplateSection("Target Schema", required=True, guidance="Describe the target data structure."),
                TemplateSection("Migration Steps", required=True, guidance="Step-by-step migration procedure."),
                TemplateSection("Data Validation", required=True, guidance="How to verify data integrity after migration."),
                TemplateSection("Privacy Impact", required=True, guidance="PII handling during migration, data retention."),
                TemplateSection("Performance Impact", required=True, guidance="Expected downtime, resource requirements."),
                TemplateSection("Rollback Plan", required=True, guidance="How to revert if migration fails."),
                TemplateSection("Testing Plan", required=True, guidance="How to test the migration before production."),
            ],
            keywords=["migration", "database", "schema", "data", "migrate", "table", "column"],
        ),
        PRDTemplate(
            id="integration",
            name="Third-Party Integration",
            description="Template for integrating with external services",
            category="integration",
            sections=[
                TemplateSection("Overview", required=True, guidance="What service are we integrating with and why?"),
                TemplateSection("Integration Architecture", required=True, guidance="How does data flow between our system and the external service?"),
                TemplateSection("Authentication", required=True, guidance="API keys, OAuth, credentials management."),
                TemplateSection("Data Flow", required=True, guidance="What data is sent/received? Any PII?"),
                TemplateSection("Error Handling & Resilience", required=True, guidance="Retry logic, circuit breakers, fallbacks."),
                TemplateSection("Security Considerations", required=True, guidance="Trust boundaries, data exposure, vendor security."),
                TemplateSection("Compliance", required=False, guidance="Data processing agreements, regulatory requirements."),
                TemplateSection("Testing Strategy", required=True, guidance="Sandbox/staging environments, mock services."),
                TemplateSection("Rollback Plan", required=True, guidance="How to disable the integration."),
            ],
            keywords=["integration", "third-party", "external", "vendor", "api", "webhook", "sdk"],
        ),
    ]

    def __init__(self, custom_templates: list[PRDTemplate] | None = None) -> None:
        self._custom_templates = custom_templates or []

    def get_all_templates(self) -> list[PRDTemplate]:
        """Return all templates (built-in + custom)."""
        return self.BUILT_IN_TEMPLATES + self._custom_templates

    def get_template(self, template_id: str) -> PRDTemplate | None:
        """Get a specific template by ID."""
        for t in self.get_all_templates():
            if t.id == template_id:
                return t
        return None

    def suggest_template(self, prd_content: str) -> PRDTemplate | None:
        """Suggest a template based on PRD content keywords."""
        content_lower = prd_content.lower()
        best_match: PRDTemplate | None = None
        best_score = 0

        for template in self.get_all_templates():
            score = sum(1 for kw in template.keywords if kw in content_lower)
            if score > best_score:
                best_score = score
                best_match = template

        return best_match if best_score >= 2 else None

    def render_template(self, template_id: str) -> str:
        """Render a template as pre-filled markdown."""
        template = self.get_template(template_id)
        if not template:
            return ""

        lines = [f"# {template.name}\n"]
        lines.append(f"*{template.description}*\n")

        for section in template.sections:
            required_tag = " *(required)*" if section.required else ""
            lines.append(f"## {section.title}{required_tag}\n")
            if section.guidance:
                lines.append(f"<!-- Guidance: {section.guidance} -->\n")
            if section.boilerplate:
                lines.append(f"{section.boilerplate}\n")
            else:
                lines.append("TODO: Fill in this section.\n")

        return "\n".join(lines)
