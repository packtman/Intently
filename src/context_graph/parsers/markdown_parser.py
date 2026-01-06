"""
Markdown PRD Parser - Extract structured intent from Markdown PRDs.

Supports standard Markdown format with sections for:
- Overview/Summary
- Features
- User Stories
- Technical Requirements
- Security Considerations
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from context_graph.core.models import Intent, Entity, EntityType
from context_graph.parsers.prd_parser import PRDParser


@dataclass
class MarkdownSection:
    """A section in a Markdown document."""
    
    title: str
    level: int
    content: str
    subsections: list["MarkdownSection"]


class MarkdownPRDParser(PRDParser):
    """
    Parse Markdown PRDs into structured Intent.
    
    Understands common PRD section patterns:
    - # Title
    - ## Overview / Summary / Background
    - ## Features / Requirements
    - ## User Stories
    - ## Technical Specification
    - ## Security / Privacy
    - ## API Changes
    """
    
    def __init__(self) -> None:
        self.section_aliases = {
            "overview": ["overview", "summary", "background", "introduction", "about"],
            "features": ["features", "requirements", "functionality", "capabilities"],
            "user_stories": ["user stories", "use cases", "scenarios", "user flows"],
            "technical": ["technical", "architecture", "design", "implementation"],
            "security": ["security", "privacy", "compliance", "access control"],
            "api": ["api", "endpoints", "routes", "interface"],
            "data": ["data", "models", "schema", "database"],
        }
    
    def parse(self, content: str, source: str = "") -> Intent:
        """Parse Markdown PRD content."""
        sections = self._parse_sections(content)
        
        intent = Intent(
            title=self._extract_title(content, sections),
            summary=self._extract_by_section_type("overview", sections),
            features=self._extract_list_items("features", sections),
            user_stories=self._extract_user_stories(sections),
            data_entities=self._extract_data_entities(content, sections),
            api_changes=self._extract_api_changes(sections),
            auth_requirements=self._extract_auth_requirements(content, sections),
            data_sensitivity=self._extract_data_sensitivity(content, sections),
            external_integrations=self._extract_integrations(content, sections),
            source_document=source,
            raw_content=content,
        )
        
        return intent
    
    def parse_file(self, file_path: Path) -> Intent:
        """Parse a Markdown PRD file."""
        content = file_path.read_text(encoding="utf-8")
        return self.parse(content, str(file_path))
    
    def _parse_sections(self, content: str) -> list[MarkdownSection]:
        """Parse Markdown into hierarchical sections."""
        sections: list[MarkdownSection] = []
        current_section: MarkdownSection | None = None
        current_content: list[str] = []
        
        lines = content.split("\n")
        
        for line in lines:
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            
            if heading_match:
                # Save previous section
                if current_section:
                    current_section.content = "\n".join(current_content).strip()
                    sections.append(current_section)
                
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                
                current_section = MarkdownSection(
                    title=title,
                    level=level,
                    content="",
                    subsections=[],
                )
                current_content = []
            elif current_section:
                current_content.append(line)
        
        # Save last section
        if current_section:
            current_section.content = "\n".join(current_content).strip()
            sections.append(current_section)
        
        return sections
    
    def _find_sections_by_type(
        self, 
        section_type: str, 
        sections: list[MarkdownSection]
    ) -> list[MarkdownSection]:
        """Find sections matching a type alias."""
        aliases = self.section_aliases.get(section_type, [section_type])
        matching = []
        
        for section in sections:
            title_lower = section.title.lower()
            for alias in aliases:
                if alias in title_lower:
                    matching.append(section)
                    break
        
        return matching
    
    def _extract_title(
        self, 
        content: str, 
        sections: list[MarkdownSection]
    ) -> str:
        """Extract document title."""
        for section in sections:
            if section.level == 1:
                return section.title
        
        # Fallback: first line
        first_line = content.split("\n")[0].strip()
        return first_line.lstrip("# ") if first_line else "Untitled PRD"
    
    def _extract_by_section_type(
        self, 
        section_type: str, 
        sections: list[MarkdownSection]
    ) -> str:
        """Extract content from sections matching a type."""
        matching = self._find_sections_by_type(section_type, sections)
        
        if matching:
            return "\n\n".join(s.content for s in matching)
        return ""
    
    def _extract_list_items(
        self, 
        section_type: str, 
        sections: list[MarkdownSection]
    ) -> list[str]:
        """Extract list items from sections matching a type."""
        matching = self._find_sections_by_type(section_type, sections)
        items: list[str] = []
        
        for section in matching:
            # Find list items
            for line in section.content.split("\n"):
                line = line.strip()
                if re.match(r'^[-*•]\s+', line):
                    item = re.sub(r'^[-*•]\s+', '', line)
                    items.append(item)
                elif re.match(r'^\d+\.\s+', line):
                    item = re.sub(r'^\d+\.\s+', '', line)
                    items.append(item)
        
        return items
    
    def _extract_user_stories(
        self, 
        sections: list[MarkdownSection]
    ) -> list[str]:
        """Extract user stories from content."""
        stories: list[str] = []
        
        # Check dedicated user stories section
        story_sections = self._find_sections_by_type("user_stories", sections)
        
        for section in story_sections:
            # Find "As a..." patterns
            pattern = r'As an?\s+.+?(?:,\s*I\s+want\s+.+?)?(?:so\s+that\s+.+?)?(?:\.|$)'
            matches = re.findall(pattern, section.content, re.IGNORECASE | re.DOTALL)
            stories.extend(m.strip() for m in matches)
        
        # Also check all content for user story patterns
        for section in sections:
            matches = re.findall(
                r'As an?\s+[^.]+\.', 
                section.content, 
                re.IGNORECASE
            )
            for match in matches:
                if match.strip() not in stories:
                    stories.append(match.strip())
        
        return stories
    
    def _extract_data_entities(
        self, 
        content: str, 
        sections: list[MarkdownSection]
    ) -> list[Entity]:
        """Extract data entities from the PRD."""
        entities: list[Entity] = []
        seen_names: set[str] = set()
        
        # Look for data model sections
        data_sections = self._find_sections_by_type("data", sections)
        
        for section in data_sections:
            # Look for entity definitions (often in tables or lists)
            # Pattern: **EntityName** or `EntityName`
            bold_entities = re.findall(r'\*\*(\w+)\*\*', section.content)
            code_entities = re.findall(r'`(\w+)`', section.content)
            
            for name in bold_entities + code_entities:
                if name not in seen_names and len(name) > 2:
                    seen_names.add(name)
                    entities.append(Entity(
                        name=name,
                        entity_type=EntityType.DATA,
                        description=f"Data entity from PRD: {section.title}",
                        source=f"prd:{section.title}",
                    ))
        
        # Look for sensitive data patterns
        sensitive_patterns = [
            (r'\b(email|password|ssn|phone|address)\b', EntityType.PII),
            (r'\b(api[_-]?key|secret|token|credential)\b', EntityType.SECRET),
            (r'\b(user|customer|admin|account)\b', EntityType.USER),
        ]
        
        content_lower = content.lower()
        for pattern, entity_type in sensitive_patterns:
            matches = re.findall(pattern, content_lower)
            for match in matches:
                name = match.replace("_", " ").replace("-", " ").title()
                if name not in seen_names:
                    seen_names.add(name)
                    entities.append(Entity(
                        name=name,
                        entity_type=entity_type,
                        description=f"Sensitive data identified in PRD",
                        source="prd:content_scan",
                        is_sensitive=entity_type in [EntityType.PII, EntityType.SECRET],
                    ))
        
        return entities
    
    def _extract_api_changes(
        self, 
        sections: list[MarkdownSection]
    ) -> list[dict[str, Any]]:
        """Extract API changes from the PRD."""
        changes: list[dict[str, Any]] = []
        
        api_sections = self._find_sections_by_type("api", sections)
        
        for section in api_sections:
            # Look for endpoint patterns
            # GET /api/users, POST /api/auth/login, etc.
            endpoint_pattern = r'(GET|POST|PUT|PATCH|DELETE)\s+(/\S+)'
            matches = re.findall(endpoint_pattern, section.content, re.IGNORECASE)
            
            for method, path in matches:
                changes.append({
                    "method": method.upper(),
                    "path": path,
                    "source": f"prd:{section.title}",
                })
            
            # Look for endpoint descriptions in lists
            # - `/api/users` - Get all users
            list_pattern = r'[-*]\s+`?(/\S+)`?\s*[-:]\s*(.+)'
            list_matches = re.findall(list_pattern, section.content)
            
            for path, description in list_matches:
                if not any(c["path"] == path for c in changes):
                    changes.append({
                        "path": path,
                        "description": description.strip(),
                        "source": f"prd:{section.title}",
                    })
        
        return changes
    
    def _extract_auth_requirements(
        self, 
        content: str, 
        sections: list[MarkdownSection]
    ) -> list[str]:
        """Extract authentication requirements."""
        requirements: list[str] = []
        
        # Check security sections
        security_sections = self._find_sections_by_type("security", sections)
        
        auth_keywords = [
            "authentication", "authorization", "login", "logout",
            "permission", "role", "access control", "oauth", "sso",
            "jwt", "token", "session", "mfa", "2fa", "rbac"
        ]
        
        for section in security_sections:
            for line in section.content.split("\n"):
                line_lower = line.lower()
                for keyword in auth_keywords:
                    if keyword in line_lower:
                        requirements.append(line.strip())
                        break
        
        # Also scan full content
        for line in content.split("\n"):
            line_lower = line.lower()
            if "must authenticate" in line_lower or "requires auth" in line_lower:
                if line.strip() not in requirements:
                    requirements.append(line.strip())
        
        return list(set(requirements))
    
    def _extract_data_sensitivity(
        self, 
        content: str, 
        sections: list[MarkdownSection]
    ) -> list[str]:
        """Extract data sensitivity mentions."""
        sensitivity: list[str] = []
        
        keywords = [
            "pii", "personal data", "sensitive", "confidential",
            "encrypted", "gdpr", "hipaa", "pci", "sox"
        ]
        
        for line in content.split("\n"):
            line_lower = line.lower()
            for keyword in keywords:
                if keyword in line_lower:
                    sensitivity.append(line.strip())
                    break
        
        return list(set(sensitivity))
    
    def _extract_integrations(
        self, 
        content: str, 
        sections: list[MarkdownSection]
    ) -> list[str]:
        """Extract external integrations."""
        integrations: list[str] = []
        
        # Common third-party services
        services = [
            "stripe", "paypal", "twilio", "sendgrid", "mailchimp",
            "aws", "gcp", "azure", "firebase", "supabase",
            "github", "gitlab", "bitbucket", "jira", "slack",
            "okta", "auth0", "cognito", "keycloak"
        ]
        
        for line in content.split("\n"):
            line_lower = line.lower()
            for service in services:
                if service in line_lower:
                    integrations.append(line.strip())
                    break
        
        # Also look for generic integration mentions
        if "third-party" in content.lower() or "external api" in content.lower():
            for line in content.split("\n"):
                if "third-party" in line.lower() or "external" in line.lower():
                    integrations.append(line.strip())
        
        return list(set(integrations))

