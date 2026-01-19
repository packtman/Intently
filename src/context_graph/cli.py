"""
CLI for Context Graph Security Reviews.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file in project root
_project_root = Path(__file__).parent.parent.parent
_env_file = _project_root / ".env"
if _env_file.exists():
    load_dotenv(_env_file)
else:
    load_dotenv()
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.markdown import Markdown

from context_graph.parsers import MarkdownPRDParser
from context_graph.analyzers import (
    MultiLanguageAnalyzer, 
    PythonAnalyzer, 
    KotlinAnalyzer,
    TypeScriptAnalyzer,
    YAMLAnalyzer,
    JSONAnalyzer,
)
from context_graph.security.review_engine import SecurityReviewEngine, ReviewConfig
from context_graph.reports.markdown_report import MarkdownReportGenerator
from context_graph.integrations.github import GitHubIntegration, ClonedRepo


app = typer.Typer(
    name="context-graph",
    help="Context Graph - Security Review Platform",
    add_completion=False,
)

console = Console()


def _resolve_codebase_path(codebase: str, github_token: Optional[str] = None) -> tuple[Path, Optional[ClonedRepo]]:
    """
    Resolve codebase path - handles local paths and GitHub URLs.
    
    Returns (path, cloned_repo) where cloned_repo is set if we cloned from GitHub.
    """
    # Check if it's a GitHub URL or owner/repo format
    is_github = (
        codebase.startswith("https://github.com") or
        codebase.startswith("github.com") or
        codebase.startswith("git@github.com") or
        ("/" in codebase and not codebase.startswith("/") and not codebase.startswith("."))
    )
    
    if is_github:
        console.print(f"[cyan]Cloning from GitHub:[/cyan] {codebase}")
        github = GitHubIntegration(token=github_token or os.getenv("GITHUB_TOKEN"))
        cloned = github.clone(codebase)
        console.print(f"[green]✓[/green] Cloned to {cloned.path}")
        return cloned.path, cloned
    else:
        return Path(codebase), None


@app.command()
def review(
    prd: Path = typer.Argument(..., help="Path to PRD file (markdown)"),
    codebase: str = typer.Argument(..., help="Path to codebase or GitHub URL (e.g., owner/repo)"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file for report"),
    format: str = typer.Option("markdown", "--format", "-f", help="Output format: markdown, json"),
    use_llm: bool = typer.Option(False, "--llm", help="Use LLM for analysis"),
    branch: Optional[str] = typer.Option(None, "--branch", "-b", help="GitHub branch to analyze"),
    pr: Optional[int] = typer.Option(None, "--pr", help="GitHub PR number to analyze"),
    github_token: Optional[str] = typer.Option(None, "--github-token", envvar="GITHUB_TOKEN", help="GitHub token for private repos"),
) -> None:
    """
    Run a security review on a PRD against a codebase.
    
    Codebase can be:
    - Local path: /path/to/code or ./relative/path
    - GitHub URL: https://github.com/owner/repo
    - GitHub shorthand: owner/repo
    
    Examples:
        context-graph review prd.md ./my-app --llm
        context-graph review prd.md owner/repo --branch main
        context-graph review prd.md owner/repo --pr 123
    """
    console.print(Panel.fit(
        "[bold blue]Context Graph[/bold blue] - Security Review",
        subtitle="PRD → Code Impact Analysis"
    ))
    
    # Validate PRD
    if not prd.exists():
        console.print(f"[red]Error:[/red] PRD file not found: {prd}")
        raise typer.Exit(1)
    
    # Resolve codebase (local or GitHub)
    cloned_repo: Optional[ClonedRepo] = None
    
    try:
        # Handle GitHub URLs with branch/PR options
        is_github = (
            codebase.startswith("https://github.com") or
            codebase.startswith("github.com") or
            ("/" in codebase and not codebase.startswith("/") and not codebase.startswith("."))
        )
        
        if is_github:
            console.print(f"[cyan]📦 Cloning from GitHub:[/cyan] {codebase}")
            if branch:
                console.print(f"   Branch: {branch}")
            if pr:
                console.print(f"   PR: #{pr}")
            
            github = GitHubIntegration(token=github_token)
            cloned_repo = github.clone(codebase, branch=branch, pr=pr)
            codebase_path = cloned_repo.path
            console.print(f"[green]✓[/green] Cloned to {codebase_path}")
        else:
            codebase_path = Path(codebase)
            if not codebase_path.exists():
                console.print(f"[red]Error:[/red] Codebase directory not found: {codebase}")
                raise typer.Exit(1)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Parse PRD
            task = progress.add_task("Parsing PRD...", total=None)
            parser = MarkdownPRDParser()
            intent = parser.parse_file(prd)
            progress.update(task, description="✓ PRD parsed")
            
            # Analyze codebase (auto-detect all languages)
            task = progress.add_task("Analyzing codebase...", total=None)
            analyzer = MultiLanguageAnalyzer()
            analyzer.add_analyzer(PythonAnalyzer())
            analyzer.add_analyzer(KotlinAnalyzer())
            analyzer.add_analyzer(TypeScriptAnalyzer())
            analyzer.add_analyzer(YAMLAnalyzer())
            analyzer.add_analyzer(JSONAnalyzer())
            state = analyzer.analyze_codebase(codebase_path)
            progress.update(task, description=f"✓ Analyzed {state.files_analyzed} files")
            
            # Run review
            task = progress.add_task("Running security analysis...", total=None)
            
            config = ReviewConfig(
                use_llm=use_llm,
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            )
            
            engine = SecurityReviewEngine(config)
            result = asyncio.run(engine.review(intent, state))
            progress.update(task, description=f"✓ Found {len(result.all_findings)} findings")
    
    finally:
        # Cleanup cloned repo
        if cloned_repo:
            cloned_repo.cleanup()
            console.print("[dim]Cleaned up temporary clone[/dim]")
    
    # Display results
    console.print()
    
    # Summary table
    table = Table(title="Security Review Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    
    table.add_row("Feature", intent.title)
    table.add_row("Risk Rating", _colorize_risk(result.risk_rating))
    table.add_row("Total Findings", str(len(result.all_findings)))
    table.add_row("Critical", str(result.critical_count))
    table.add_row("High", str(result.high_count))
    
    console.print(table)
    console.print()
    
    # Findings
    if result.all_findings:
        console.print("[bold]Top Findings:[/bold]")
        for i, finding in enumerate(result.all_findings[:5], 1):
            severity_icon = _severity_icon(finding.severity.value)
            console.print(f"  {i}. {severity_icon} {finding.title}")
        
        if len(result.all_findings) > 5:
            console.print(f"  ... and {len(result.all_findings) - 5} more")
    else:
        console.print("[green]✓ No security findings identified[/green]")
    
    # Generate report
    if output:
        generator = MarkdownReportGenerator()
        report = generator.generate(result)
        output.write_text(report)
        console.print(f"\n[green]Report saved to:[/green] {output}")
    else:
        console.print("\n[dim]Use --output to save the full report[/dim]")


@app.command()
def parse(
    prd: Path = typer.Argument(..., help="Path to PRD file"),
) -> None:
    """
    Parse a PRD and show extracted intent.
    """
    if not prd.exists():
        console.print(f"[red]Error:[/red] File not found: {prd}")
        raise typer.Exit(1)
    
    parser = MarkdownPRDParser()
    intent = parser.parse_file(prd)
    
    console.print(Panel.fit(f"[bold]{intent.title}[/bold]"))
    
    if intent.summary:
        console.print(f"\n[bold]Summary:[/bold]\n{intent.summary[:200]}...")
    
    if intent.features:
        console.print("\n[bold]Features:[/bold]")
        for feature in intent.features[:10]:
            console.print(f"  • {feature}")
    
    if intent.data_entities:
        console.print("\n[bold]Data Entities:[/bold]")
        for entity in intent.data_entities[:10]:
            sensitive = "🔒" if entity.is_sensitive else ""
            console.print(f"  • {entity.name} ({entity.entity_type.value}) {sensitive}")
    
    if intent.api_changes:
        console.print("\n[bold]API Changes:[/bold]")
        for api in intent.api_changes[:10]:
            console.print(f"  • {api.get('method', 'ANY')} {api.get('path', 'unknown')}")


@app.command()
def analyze(
    codebase: str = typer.Argument(..., help="Path to codebase or GitHub URL (e.g., owner/repo)"),
    language: list[str] = typer.Option(["auto"], "--lang", "-l", help="Languages: python, kotlin, typescript, yaml, json, auto"),
    branch: Optional[str] = typer.Option(None, "--branch", "-b", help="GitHub branch to analyze"),
    github_token: Optional[str] = typer.Option(None, "--github-token", envvar="GITHUB_TOKEN"),
) -> None:
    """
    Analyze a codebase and show current state.
    
    Supports local paths and GitHub URLs.
    
    Languages: python, kotlin, typescript, yaml, json, or 'auto' to detect all.
    """
    cloned_repo: Optional[ClonedRepo] = None
    
    try:
        # Resolve codebase
        is_github = (
            codebase.startswith("https://github.com") or
            codebase.startswith("github.com") or
            ("/" in codebase and not codebase.startswith("/") and not codebase.startswith("."))
        )
        
        if is_github:
            console.print(f"[cyan]📦 Cloning from GitHub:[/cyan] {codebase}")
            github = GitHubIntegration(token=github_token)
            cloned_repo = github.clone(codebase, branch=branch)
            codebase_path = cloned_repo.path
        else:
            codebase_path = Path(codebase)
            if not codebase_path.exists():
                console.print(f"[red]Error:[/red] Directory not found: {codebase}")
                raise typer.Exit(1)
        
        analyzer = MultiLanguageAnalyzer()
        
        # Auto-detect or use specified languages
        use_all = "auto" in language or "all" in language
        
        if use_all or "python" in language:
            analyzer.add_analyzer(PythonAnalyzer())
        if use_all or "kotlin" in language:
            analyzer.add_analyzer(KotlinAnalyzer())
        if use_all or "typescript" in language or "javascript" in language or "ts" in language or "js" in language:
            analyzer.add_analyzer(TypeScriptAnalyzer())
        if use_all or "yaml" in language or "yml" in language or "openapi" in language:
            analyzer.add_analyzer(YAMLAnalyzer())
        if use_all or "json" in language:
            analyzer.add_analyzer(JSONAnalyzer())
        
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("Analyzing...", total=None)
            state = analyzer.analyze_codebase(codebase_path)
        
        console.print(Panel.fit(f"[bold]Codebase Analysis[/bold]\n{codebase}"))
        
        table = Table()
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Files Analyzed", str(state.files_analyzed))
        table.add_row("Lines of Code", f"{state.lines_of_code:,}")
        table.add_row("API Endpoints", str(len(state.api_endpoints)))
        table.add_row("Data Models", str(len(state.data_models)))
        table.add_row("Security Controls", ", ".join(state.existing_controls[:5]) or "None detected")
        
        console.print(table)
        
        if state.api_endpoints:
            console.print("\n[bold]API Endpoints:[/bold]")
            for ep in state.api_endpoints[:10]:
                method = ep.get("method", "ANY")
                path = ep.get("path", "unknown")
                auth = "🔒" if ep.get("requires_auth") else "🔓"
                console.print(f"  {auth} {method} {path}")
    
    finally:
        if cloned_repo:
            cloned_repo.cleanup()


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h"),
    port: int = typer.Option(8000, "--port", "-p"),
    reload: bool = typer.Option(False, "--reload", "-r"),
) -> None:
    """
    Start the web UI server.
    """
    console.print(Panel.fit(
        "[bold blue]Context Graph[/bold blue] - Web Server",
        subtitle=f"http://{host}:{port}"
    ))
    
    import uvicorn
    uvicorn.run(
        "context_graph.api.main:app",
        host=host,
        port=port,
        reload=reload,
    )


def _colorize_risk(rating: str) -> str:
    """Colorize risk rating."""
    colors = {
        "CRITICAL": "[bold red]CRITICAL[/bold red]",
        "HIGH": "[red]HIGH[/red]",
        "MEDIUM": "[yellow]MEDIUM[/yellow]",
        "LOW": "[green]LOW[/green]",
        "MINIMAL": "[bold green]MINIMAL[/bold green]",
    }
    return colors.get(rating, rating)


def _severity_icon(severity: str) -> str:
    """Get icon for severity."""
    icons = {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🟡",
        "low": "🟢",
        "info": "🔵",
    }
    return icons.get(severity.lower(), "⚪")


if __name__ == "__main__":
    app()

