"""
Code Graph Configuration - Feature flags for LSP and graph analysis.

LSP is an OPTIONAL enhancement that provides richer code understanding.
The system works well without it, using Python AST + regex fallback.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class LSPConfig:
    """Configuration for optional LSP integration."""
    
    enabled: bool = True  # Try to use LSP if available
    timeout_seconds: float = 30.0
    
    # Server availability (detected at runtime)
    typescript_available: bool = False
    python_available: bool = False
    kotlin_available: bool = False


@dataclass
class GraphAnalysisConfig:
    """Configuration for graph-based code analysis."""
    
    enabled: bool = True
    
    # LSP settings (optional feature)
    lsp: LSPConfig = field(default_factory=LSPConfig)
    
    # Analysis features
    include_call_hierarchy: bool = True
    include_references: bool = True
    detect_unused_exports: bool = True
    
    # Performance
    max_files: int = 1000
    parallel_files: int = 10


def load_graph_config(config_path: Optional[Path] = None) -> GraphAnalysisConfig:
    """
    Load graph analysis configuration from YAML file.
    
    Falls back to sensible defaults if config not found.
    """
    config = GraphAnalysisConfig()
    
    # Try to find config file
    if config_path is None:
        # Look in common locations
        candidates = [
            Path("context-graph.yaml"),
            Path("context-graph.yml"),
            Path.home() / ".context-graph.yaml",
        ]
        for candidate in candidates:
            if candidate.exists():
                config_path = candidate
                break
    
    if config_path and config_path.exists():
        try:
            with open(config_path) as f:
                data = yaml.safe_load(f) or {}
            
            graph_data = data.get("codebase", {}).get("graph_analysis", {})
            
            config.enabled = graph_data.get("enabled", True)
            config.include_call_hierarchy = graph_data.get("include_call_hierarchy", True)
            config.include_references = graph_data.get("include_references", True)
            config.detect_unused_exports = graph_data.get("detect_unused_exports", True)
            
            lsp_data = graph_data.get("lsp", {})
            config.lsp.enabled = lsp_data.get("enabled", True)
            config.lsp.timeout_seconds = lsp_data.get("timeout_seconds", 30.0)
            
            logger.debug(f"Loaded graph config from {config_path}")
            
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {e}")
    
    return config


def check_lsp_availability(config: GraphAnalysisConfig) -> dict[str, bool]:
    """
    Check which LSP servers are available.
    
    Returns dict of language -> availability.
    """
    import shutil
    import subprocess
    
    availability = {
        "typescript": False,
        "python": False,
        "kotlin": False,
    }
    
    if not config.lsp.enabled:
        return availability
    
    # Check TypeScript LSP
    if shutil.which("typescript-language-server"):
        availability["typescript"] = True
        config.lsp.typescript_available = True
    
    # Check Python LSP (pyright)
    if shutil.which("pyright-langserver") or shutil.which("pyright"):
        availability["python"] = True
        config.lsp.python_available = True
    
    # Check Kotlin LSP
    if shutil.which("kotlin-language-server"):
        availability["kotlin"] = True
        config.lsp.kotlin_available = True
    
    return availability


def get_analysis_capabilities(config: GraphAnalysisConfig) -> dict[str, Any]:
    """
    Get a summary of available analysis capabilities.
    
    Useful for showing users what features are active.
    """
    availability = check_lsp_availability(config)
    
    capabilities = {
        "graph_analysis": config.enabled,
        "lsp_enabled": config.lsp.enabled,
        "lsp_servers": availability,
        "features": {
            "python_ast": True,  # Always available
            "typescript_ast": availability.get("typescript", False),
            "kotlin_ast": availability.get("kotlin", False),
            "call_hierarchy": config.include_call_hierarchy and any(availability.values()),
            "cross_file_references": config.include_references and any(availability.values()),
            "unused_export_detection": config.detect_unused_exports,
        },
        "fallback": {
            "typescript": "regex" if not availability.get("typescript") else "lsp",
            "kotlin": "regex" if not availability.get("kotlin") else "lsp",
            "python": "ast",  # Python always uses AST (built-in)
        },
    }
    
    return capabilities


def print_capabilities_summary(config: Optional[GraphAnalysisConfig] = None) -> None:
    """Print a human-readable summary of analysis capabilities."""
    if config is None:
        config = load_graph_config()
    
    caps = get_analysis_capabilities(config)
    
    print("\n" + "=" * 50)
    print("Code Analysis Capabilities")
    print("=" * 50)
    
    print(f"\nGraph Analysis: {'✅ Enabled' if caps['graph_analysis'] else '❌ Disabled'}")
    print(f"LSP Integration: {'✅ Enabled' if caps['lsp_enabled'] else '❌ Disabled'}")
    
    print("\nLanguage Support:")
    for lang, method in caps["fallback"].items():
        status = "✅ LSP" if method == "lsp" else ("✅ AST" if method == "ast" else "⚠️ Regex")
        print(f"  - {lang.capitalize()}: {status}")
    
    print("\nFeatures:")
    for feature, available in caps["features"].items():
        status = "✅" if available else "❌"
        print(f"  - {feature.replace('_', ' ').title()}: {status}")
    
    # Installation hints for missing LSP servers
    missing = [lang for lang, avail in caps["lsp_servers"].items() if not avail]
    if missing and caps["lsp_enabled"]:
        print("\n💡 To enable full LSP features, install:")
        if "typescript" in missing:
            print("   npm install -g typescript-language-server typescript")
        if "python" in missing:
            print("   pip install pyright")
        if "kotlin" in missing:
            print("   # Kotlin: https://github.com/fwcd/kotlin-language-server")
    
    print("")
