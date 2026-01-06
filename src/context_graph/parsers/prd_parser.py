"""
PRD Parser - Extract structured intent from Product Requirement Documents.

Uses LLM to semantically understand PRDs and extract security-relevant information.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from context_graph.core.models import Intent, Entity, EntityType


class PRDParser(ABC):
    """Abstract base class for PRD parsers."""
    
    @abstractmethod
    def parse(self, content: str, source: str = "") -> Intent:
        """
        Parse PRD content and extract structured intent.
        
        Args:
            content: The PRD content as text
            source: Source identifier (file path, URL, etc.)
            
        Returns:
            Intent object with extracted information
        """
        pass
    
    @abstractmethod
    def parse_file(self, file_path: Path) -> Intent:
        """
        Parse a PRD file.
        
        Args:
            file_path: Path to the PRD file
            
        Returns:
            Intent object with extracted information
        """
        pass
    
    def extract_entities_from_text(self, text: str) -> list[Entity]:
        """
        Extract potential entities from text using pattern matching.
        
        This is a fallback when LLM is not available.
        """
        entities = []
        
        # Common patterns for security-relevant entities
        patterns = {
            "user": ["user", "customer", "admin", "owner", "member"],
            "data": ["data", "information", "record", "document"],
            "api": ["api", "endpoint", "route", "webhook"],
            "pii": ["email", "password", "ssn", "phone", "address", "name"],
            "secret": ["token", "key", "secret", "credential", "password"],
        }
        
        text_lower = text.lower()
        
        for entity_type, keywords in patterns.items():
            for keyword in keywords:
                if keyword in text_lower:
                    entity = Entity(
                        name=keyword,
                        entity_type=EntityType(entity_type) if entity_type in [e.value for e in EntityType] else EntityType.DATA,
                        description=f"Extracted from PRD: contains '{keyword}'",
                        source="prd_pattern_match",
                        is_sensitive=entity_type in ["pii", "secret"],
                    )
                    entities.append(entity)
        
        return entities


class SimplePRDParser(PRDParser):
    """
    Simple PRD parser using pattern matching.
    
    Use this when LLM is not configured or for testing.
    """
    
    def parse(self, content: str, source: str = "") -> Intent:
        """Parse PRD using pattern matching."""
        lines = content.split("\n")
        
        intent = Intent(
            title=self._extract_title(lines),
            summary=self._extract_summary(lines),
            features=self._extract_features(lines),
            user_stories=self._extract_user_stories(lines),
            data_entities=self.extract_entities_from_text(content),
            auth_requirements=self._extract_auth_requirements(content),
            data_sensitivity=self._extract_data_sensitivity(content),
            external_integrations=self._extract_integrations(content),
            source_document=source,
            raw_content=content,
        )
        
        return intent
    
    def parse_file(self, file_path: Path) -> Intent:
        """Parse a PRD file."""
        content = file_path.read_text()
        return self.parse(content, str(file_path))
    
    def _extract_title(self, lines: list[str]) -> str:
        """Extract title from first heading."""
        for line in lines:
            if line.startswith("# "):
                return line[2:].strip()
        return "Untitled PRD"
    
    def _extract_summary(self, lines: list[str]) -> str:
        """Extract summary - first paragraph after title."""
        in_summary = False
        summary_lines = []
        
        for line in lines:
            if line.startswith("# "):
                in_summary = True
                continue
            if in_summary:
                if line.startswith("#"):
                    break
                if line.strip():
                    summary_lines.append(line.strip())
                elif summary_lines:
                    break
        
        return " ".join(summary_lines)
    
    def _extract_features(self, lines: list[str]) -> list[str]:
        """Extract feature list items."""
        features = []
        in_features = False
        
        for line in lines:
            lower = line.lower()
            if "feature" in lower and line.startswith("#"):
                in_features = True
                continue
            if in_features:
                if line.startswith("#"):
                    in_features = False
                elif line.strip().startswith(("-", "*", "•")):
                    features.append(line.strip().lstrip("-*• "))
        
        return features
    
    def _extract_user_stories(self, lines: list[str]) -> list[str]:
        """Extract user stories (As a... I want... So that...)."""
        stories = []
        current_story = []
        
        for line in lines:
            lower = line.lower()
            if "as a" in lower or "as an" in lower:
                if current_story:
                    stories.append(" ".join(current_story))
                current_story = [line.strip()]
            elif current_story and ("i want" in lower or "so that" in lower):
                current_story.append(line.strip())
            elif current_story and line.strip() == "":
                stories.append(" ".join(current_story))
                current_story = []
        
        if current_story:
            stories.append(" ".join(current_story))
        
        return stories
    
    def _extract_auth_requirements(self, content: str) -> list[str]:
        """Extract authentication/authorization requirements."""
        requirements = []
        keywords = [
            "authentication", "authorization", "login", "logout",
            "permission", "role", "access control", "oauth", "sso",
            "jwt", "token", "session", "mfa", "2fa"
        ]
        
        lines = content.split("\n")
        for line in lines:
            lower = line.lower()
            for keyword in keywords:
                if keyword in lower:
                    requirements.append(line.strip())
                    break
        
        return list(set(requirements))  # Dedupe
    
    def _extract_data_sensitivity(self, content: str) -> list[str]:
        """Extract mentions of sensitive data."""
        sensitivity = []
        keywords = [
            "pii", "personal", "sensitive", "confidential", "private",
            "encrypted", "password", "secret", "credential", "ssn",
            "credit card", "financial", "health", "hipaa", "gdpr"
        ]
        
        lines = content.split("\n")
        for line in lines:
            lower = line.lower()
            for keyword in keywords:
                if keyword in lower:
                    sensitivity.append(line.strip())
                    break
        
        return list(set(sensitivity))
    
    def _extract_integrations(self, content: str) -> list[str]:
        """Extract external integration mentions."""
        integrations = []
        keywords = [
            "api", "integration", "third-party", "external",
            "webhook", "oauth", "stripe", "twilio", "aws", "gcp",
            "azure", "firebase", "sendgrid", "slack", "github"
        ]
        
        lines = content.split("\n")
        for line in lines:
            lower = line.lower()
            for keyword in keywords:
                if keyword in lower:
                    integrations.append(line.strip())
                    break
        
        return list(set(integrations))

