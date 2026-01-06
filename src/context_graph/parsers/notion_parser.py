"""
Notion PRD Parser - Extract structured intent from Notion pages.

Uses Notion API to fetch and parse PRD content.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from context_graph.core.models import Intent, Entity, EntityType
from context_graph.parsers.prd_parser import PRDParser
from context_graph.parsers.markdown_parser import MarkdownPRDParser


class NotionPRDParser(PRDParser):
    """
    Parse PRDs from Notion pages.
    
    Fetches content via Notion API and converts to markdown for parsing.
    """
    
    def __init__(self, notion_token: str | None = None) -> None:
        self.notion_token = notion_token or os.getenv("NOTION_API_KEY")
        self._markdown_parser = MarkdownPRDParser()
    
    def parse(self, content: str, source: str = "") -> Intent:
        """
        Parse Notion content (already converted to markdown).
        
        For direct Notion API integration, use parse_page() instead.
        """
        return self._markdown_parser.parse(content, source)
    
    def parse_file(self, file_path: Path) -> Intent:
        """Parse a file exported from Notion."""
        content = file_path.read_text(encoding="utf-8")
        return self.parse(content, str(file_path))
    
    async def parse_page(self, page_id: str) -> Intent:
        """
        Parse a Notion page by ID.
        
        Note: This requires the Notion MCP integration to be configured.
        For standalone use, export the page to markdown first.
        """
        # This would use the Notion API directly
        # For now, provide instructions for using with MCP
        raise NotImplementedError(
            "Direct Notion API parsing requires async HTTP client. "
            "Use the Notion MCP tools to fetch page content, then pass to parse()."
        )
    
    def parse_notion_export(self, content: str, source: str = "") -> Intent:
        """
        Parse a Notion page exported to markdown.
        
        Handles Notion-specific markdown quirks:
        - Callout blocks
        - Toggle blocks
        - Database references
        - Page mentions
        """
        # Clean up Notion-specific formatting
        cleaned = self._clean_notion_markdown(content)
        
        # Parse with enhanced entity extraction
        intent = self._markdown_parser.parse(cleaned, source)
        
        # Extract Notion-specific elements
        intent.data_entities.extend(self._extract_notion_entities(content))
        
        return intent
    
    def _clean_notion_markdown(self, content: str) -> str:
        """Clean Notion-specific markdown artifacts."""
        cleaned = content
        
        # Remove Notion callout icons
        cleaned = re.sub(r'^[💡📌⚠️ℹ️🔥✅❌]\s*', '', cleaned, flags=re.MULTILINE)
        
        # Convert Notion callouts to blockquotes
        cleaned = re.sub(
            r'<aside>\s*(.*?)\s*</aside>',
            r'> \1',
            cleaned,
            flags=re.DOTALL
        )
        
        # Handle toggle blocks (convert to nested content)
        cleaned = re.sub(
            r'<details>\s*<summary>(.*?)</summary>\s*(.*?)\s*</details>',
            r'### \1\n\2',
            cleaned,
            flags=re.DOTALL
        )
        
        # Clean up page/database mentions
        cleaned = re.sub(
            r'\[@([^\]]+)\]\([^)]+\)',
            r'**\1**',
            cleaned
        )
        
        return cleaned
    
    def _extract_notion_entities(self, content: str) -> list[Entity]:
        """Extract entities from Notion-specific content."""
        entities: list[Entity] = []
        seen: set[str] = set()
        
        # Extract database mentions (often data models)
        db_pattern = r'→\s*(\w+)\s*database'
        for match in re.finditer(db_pattern, content, re.IGNORECASE):
            name = match.group(1)
            if name not in seen:
                seen.add(name)
                entities.append(Entity(
                    name=name,
                    entity_type=EntityType.DATABASE,
                    description=f"Notion database reference: {name}",
                    source="notion:database_mention",
                ))
        
        # Extract relation properties (indicates data relationships)
        relation_pattern = r'Relation to\s+(\w+)'
        for match in re.finditer(relation_pattern, content, re.IGNORECASE):
            name = match.group(1)
            if name not in seen:
                seen.add(name)
                entities.append(Entity(
                    name=name,
                    entity_type=EntityType.DATA,
                    description=f"Related entity: {name}",
                    source="notion:relation",
                ))
        
        return entities


class GoogleDocsPRDParser(PRDParser):
    """
    Parse PRDs from Google Docs.
    
    Supports exported markdown/HTML or direct API access.
    """
    
    def __init__(self) -> None:
        self._markdown_parser = MarkdownPRDParser()
    
    def parse(self, content: str, source: str = "") -> Intent:
        """Parse Google Docs content (exported to text/markdown)."""
        # Clean up Google Docs export artifacts
        cleaned = self._clean_gdocs_content(content)
        return self._markdown_parser.parse(cleaned, source)
    
    def parse_file(self, file_path: Path) -> Intent:
        """Parse an exported Google Docs file."""
        suffix = file_path.suffix.lower()
        
        if suffix == ".html":
            content = self._convert_html_to_markdown(file_path)
        else:
            content = file_path.read_text(encoding="utf-8")
        
        return self.parse(content, str(file_path))
    
    def _clean_gdocs_content(self, content: str) -> str:
        """Clean Google Docs export artifacts."""
        cleaned = content
        
        # Remove Google Docs specific formatting
        cleaned = re.sub(r'\[a\]|\[b\]|\[\d+\]', '', cleaned)  # Reference markers
        
        # Clean up smart quotes
        cleaned = cleaned.replace('"', '"').replace('"', '"')
        cleaned = cleaned.replace(''', "'").replace(''', "'")
        
        # Normalize bullet points
        cleaned = re.sub(r'^[○●◆]\s*', '- ', cleaned, flags=re.MULTILINE)
        
        return cleaned
    
    def _convert_html_to_markdown(self, file_path: Path) -> str:
        """Convert HTML export to markdown."""
        html_content = file_path.read_text(encoding="utf-8")
        
        # Simple HTML to markdown conversion
        markdown = html_content
        
        # Headers
        for i in range(6, 0, -1):
            markdown = re.sub(
                rf'<h{i}[^>]*>(.*?)</h{i}>',
                r'#' * i + r' \1\n',
                markdown,
                flags=re.IGNORECASE | re.DOTALL
            )
        
        # Lists
        markdown = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', markdown, flags=re.DOTALL)
        markdown = re.sub(r'</?[uo]l[^>]*>', '', markdown)
        
        # Paragraphs
        markdown = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', markdown, flags=re.DOTALL)
        
        # Bold/Italic
        markdown = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', markdown)
        markdown = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', markdown)
        markdown = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', markdown)
        markdown = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', markdown)
        
        # Links
        markdown = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)', markdown)
        
        # Remove remaining HTML tags
        markdown = re.sub(r'<[^>]+>', '', markdown)
        
        # Clean up whitespace
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)
        
        return markdown.strip()

