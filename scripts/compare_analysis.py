#!/usr/bin/env python3
"""
Compare Analysis Script - Compare traditional vs graph-enhanced analysis.

This script runs both the traditional regex/AST-based analysis and the new
LSP-powered graph analysis on a codebase, then compares the results.

Usage:
    python scripts/compare_analysis.py /path/to/codebase
    python scripts/compare_analysis.py /path/to/codebase --baseline baseline/review-xxx.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from context_graph.analyzers import (
    MultiLanguageAnalyzer,
    PythonAnalyzer,
    TypeScriptAnalyzer,
    KotlinAnalyzer,
    GraphEnhancedAnalyzer,
)
from context_graph.code_graph import (
    print_capabilities_summary,
    load_graph_config,
    get_analysis_capabilities,
)


def run_traditional_analysis(codebase_path: Path) -> dict:
    """Run the traditional regex/AST-based analysis."""
    print("\n" + "=" * 60)
    print("TRADITIONAL ANALYSIS (Regex + Python AST)")
    print("=" * 60)
    
    start_time = time.time()
    
    # Create multi-language analyzer
    analyzer = MultiLanguageAnalyzer()
    analyzer.add_analyzer(PythonAnalyzer())
    analyzer.add_analyzer(TypeScriptAnalyzer())
    analyzer.add_analyzer(KotlinAnalyzer())
    
    # Run analysis
    state = analyzer.analyze_codebase(codebase_path)
    
    elapsed_ms = (time.time() - start_time) * 1000
    
    result = {
        "method": "traditional",
        "timestamp": datetime.now().isoformat(),
        "elapsed_ms": elapsed_ms,
        "files_analyzed": state.files_analyzed,
        "lines_of_code": state.lines_of_code,
        "entities": len(state.entities),
        "relationships": len(state.relationships),
        "api_endpoints": len(state.api_endpoints),
        "data_models": len(state.data_models),
        "auth_patterns": len(state.auth_patterns),
        "existing_controls": len(state.existing_controls),
        "details": {
            "endpoints": [
                {"path": e.get("path"), "method": e.get("method"), "file": e.get("file")}
                for e in state.api_endpoints[:10]
            ],
            "models": [
                {"name": m.get("name"), "file": m.get("file")}
                for m in state.data_models[:10]
            ],
            "controls": state.existing_controls[:10],
        },
    }
    
    print(f"\nResults:")
    print(f"  Files analyzed: {state.files_analyzed}")
    print(f"  Lines of code: {state.lines_of_code}")
    print(f"  Entities found: {len(state.entities)}")
    print(f"  Relationships: {len(state.relationships)}")
    print(f"  API endpoints: {len(state.api_endpoints)}")
    print(f"  Data models: {len(state.data_models)}")
    print(f"  Auth patterns: {len(state.auth_patterns)}")
    print(f"  Time: {elapsed_ms:.0f}ms")
    
    return result


async def run_graph_analysis(codebase_path: Path, use_lsp: bool = True) -> dict:
    """Run the new graph-enhanced analysis."""
    print("\n" + "=" * 60)
    print(f"GRAPH-ENHANCED ANALYSIS (LSP={'enabled' if use_lsp else 'disabled'})")
    print("=" * 60)
    
    start_time = time.time()
    
    # Create graph analyzer
    analyzer = GraphEnhancedAnalyzer(
        use_lsp=use_lsp,
        include_call_hierarchy=use_lsp,
        include_references=use_lsp,
    )
    
    # Run analysis
    analysis_result = await analyzer.analyze(codebase_path)
    
    elapsed_ms = (time.time() - start_time) * 1000
    
    graph = analysis_result.graph
    state = analysis_result.state
    metrics = analysis_result.metrics
    findings = analysis_result.findings
    
    result = {
        "method": f"graph_enhanced_lsp_{use_lsp}",
        "timestamp": datetime.now().isoformat(),
        "elapsed_ms": elapsed_ms,
        "lsp_used": analysis_result.lsp_used,
        "files_analyzed": analysis_result.files_analyzed,
        "lines_of_code": state.lines_of_code if state else 0,
        
        # Graph metrics
        "graph_nodes": graph.node_count if graph else 0,
        "graph_edges": graph.edge_count if graph else 0,
        "nodes_by_kind": metrics.get("nodes_by_kind", {}),
        "nodes_by_language": metrics.get("nodes_by_language", {}),
        
        # Traditional metrics for comparison
        "entities": len(state.entities) if state else 0,
        "relationships": len(state.relationships) if state else 0,
        "api_endpoints": len(state.api_endpoints) if state else 0,
        "data_models": len(state.data_models) if state else 0,
        "auth_patterns": len(state.auth_patterns) if state else 0,
        
        # Enhanced metrics
        "coupling_metrics": metrics.get("coupling_metrics", {}),
        "unused_exports_count": metrics.get("unused_exports_count", 0),
        "findings_count": len(findings),
        
        "details": {
            "endpoints": [
                {"path": e.get("path"), "method": e.get("method"), "file": e.get("file")}
                for e in (state.api_endpoints if state else [])[:10]
            ],
            "findings_by_type": {},
            "unused_exports": metrics.get("unused_exports", [])[:5],
        },
    }
    
    # Count findings by type
    for finding in findings:
        ftype = finding.get("type", "unknown")
        result["details"]["findings_by_type"][ftype] = \
            result["details"]["findings_by_type"].get(ftype, 0) + 1
    
    print(f"\nResults:")
    print(f"  LSP used: {analysis_result.lsp_used}")
    print(f"  Files analyzed: {analysis_result.files_analyzed}")
    print(f"  Graph nodes: {graph.node_count if graph else 0}")
    print(f"  Graph edges: {graph.edge_count if graph else 0}")
    print(f"  Nodes by kind: {metrics.get('nodes_by_kind', {})}")
    print(f"  Entities found: {len(state.entities) if state else 0}")
    print(f"  Relationships: {len(state.relationships) if state else 0}")
    print(f"  API endpoints: {len(state.api_endpoints) if state else 0}")
    print(f"  Cross-functional findings: {len(findings)}")
    print(f"  Unused exports detected: {metrics.get('unused_exports_count', 0)}")
    print(f"  Time: {elapsed_ms:.0f}ms")
    
    if findings:
        print(f"\n  Findings by type:")
        for ftype, count in result["details"]["findings_by_type"].items():
            print(f"    - {ftype}: {count}")
    
    return result


def compare_results(traditional: dict, graph_enhanced: dict, baseline: Optional[dict] = None) -> dict:
    """Compare analysis results."""
    print("\n" + "=" * 60)
    print("COMPARISON")
    print("=" * 60)
    
    comparison = {
        "timestamp": datetime.now().isoformat(),
        "traditional": traditional,
        "graph_enhanced": graph_enhanced,
        "baseline": baseline,
        "improvements": [],
        "regressions": [],
    }
    
    # Compare key metrics
    metrics_to_compare = [
        ("files_analyzed", "Files analyzed"),
        ("api_endpoints", "API endpoints"),
        ("data_models", "Data models"),
        ("entities", "Entities"),
        ("relationships", "Relationships"),
    ]
    
    print("\n| Metric | Traditional | Graph-Enhanced | Baseline | Delta |")
    print("|--------|-------------|----------------|----------|-------|")
    
    for key, label in metrics_to_compare:
        trad_val = traditional.get(key, 0)
        graph_val = graph_enhanced.get(key, 0)
        baseline_val = baseline.get(key, "-") if baseline else "-"
        
        delta = graph_val - trad_val
        delta_str = f"+{delta}" if delta > 0 else str(delta)
        
        print(f"| {label} | {trad_val} | {graph_val} | {baseline_val} | {delta_str} |")
        
        if delta > 0:
            comparison["improvements"].append({
                "metric": key,
                "traditional": trad_val,
                "graph_enhanced": graph_val,
                "delta": delta,
            })
        elif delta < 0:
            comparison["regressions"].append({
                "metric": key,
                "traditional": trad_val,
                "graph_enhanced": graph_val,
                "delta": delta,
            })
    
    # Graph-specific metrics
    print(f"\n| Graph-Specific Metric | Value |")
    print("|----------------------|-------|")
    print(f"| Total graph nodes | {graph_enhanced.get('graph_nodes', 0)} |")
    print(f"| Total graph edges | {graph_enhanced.get('graph_edges', 0)} |")
    print(f"| LSP used | {graph_enhanced.get('lsp_used', False)} |")
    print(f"| Unused exports found | {graph_enhanced.get('unused_exports_count', 0)} |")
    print(f"| Cross-functional findings | {graph_enhanced.get('findings_count', 0)} |")
    
    # Performance comparison
    print(f"\n| Performance | Traditional | Graph-Enhanced |")
    print("|-------------|-------------|----------------|")
    print(f"| Time (ms) | {traditional.get('elapsed_ms', 0):.0f} | {graph_enhanced.get('elapsed_ms', 0):.0f} |")
    
    # Summary
    print("\n" + "-" * 60)
    print("SUMMARY")
    print("-" * 60)
    
    if comparison["improvements"]:
        print(f"\n✅ Improvements ({len(comparison['improvements'])}):")
        for imp in comparison["improvements"]:
            print(f"   - {imp['metric']}: +{imp['delta']} ({imp['traditional']} → {imp['graph_enhanced']})")
    
    if comparison["regressions"]:
        print(f"\n⚠️  Regressions ({len(comparison['regressions'])}):")
        for reg in comparison["regressions"]:
            print(f"   - {reg['metric']}: {reg['delta']} ({reg['traditional']} → {reg['graph_enhanced']})")
    
    # New capabilities
    new_capabilities = []
    if graph_enhanced.get("unused_exports_count", 0) > 0:
        new_capabilities.append(f"Dead code detection: {graph_enhanced['unused_exports_count']} unused exports")
    if graph_enhanced.get("findings_count", 0) > 0:
        new_capabilities.append(f"Cross-functional findings: {graph_enhanced['findings_count']} issues")
    if graph_enhanced.get("graph_edges", 0) > 0:
        new_capabilities.append(f"Relationship tracking: {graph_enhanced['graph_edges']} edges")
    
    if new_capabilities:
        print(f"\n🆕 New Capabilities from Graph Analysis:")
        for cap in new_capabilities:
            print(f"   - {cap}")
    
    return comparison


async def main():
    parser = argparse.ArgumentParser(description="Compare traditional vs graph-enhanced analysis")
    parser.add_argument("codebase_path", type=Path, help="Path to codebase to analyze")
    parser.add_argument("--baseline", type=Path, help="Path to baseline JSON file for comparison")
    parser.add_argument("--output", type=Path, help="Output path for comparison JSON")
    parser.add_argument("--no-lsp", action="store_true", help="Disable LSP for graph analysis")
    
    args = parser.parse_args()
    
    if not args.codebase_path.exists():
        print(f"Error: Codebase path does not exist: {args.codebase_path}")
        sys.exit(1)
    
    print(f"\nAnalyzing codebase: {args.codebase_path}")
    print("=" * 60)
    
    # Show current capabilities
    config = load_graph_config()
    print_capabilities_summary(config)
    
    # Load baseline if provided
    baseline = None
    if args.baseline and args.baseline.exists():
        with open(args.baseline) as f:
            baseline = json.load(f)
        print(f"Loaded baseline from: {args.baseline}")
    
    # Run traditional analysis
    traditional_result = run_traditional_analysis(args.codebase_path)
    
    # Run graph-enhanced analysis
    graph_result = await run_graph_analysis(args.codebase_path, use_lsp=not args.no_lsp)
    
    # Compare results
    comparison = compare_results(traditional_result, graph_result, baseline)
    
    # Save output if requested
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(comparison, f, indent=2, default=str)
        print(f"\nComparison saved to: {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
