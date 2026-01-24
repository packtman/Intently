# Iterative Analysis Framework

The iterative analysis framework enables multi-round LLM analysis to ensure comprehensive coverage of all security, privacy, compliance, engineering, and architecture categories.

## Overview

Traditional single-pass LLM analysis often misses findings due to:
- Output token limits causing truncation
- LLM focusing on obvious findings first
- Incomplete category coverage

The iterative framework solves this by:
1. Running multiple analysis rounds
2. Tracking which categories have been covered
3. Building "continuation context" to prompt for uncovered areas
4. Deduplicating findings across rounds
5. Using completion signals to determine when to stop

## Architecture

```
┌─────────────────────┐
│   Initial Context   │
│  (PRD + Codebase)   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐     ┌─────────────────────┐
│  IterativeAnalyzer  │────▶│   LLM Provider      │
│                     │◀────│   (OpenAI/Claude)   │
└──────────┬──────────┘     └─────────────────────┘
           │
           ▼
┌─────────────────────┐
│  Category Tracker   │
│  - Covered          │
│  - Uncovered        │
└──────────┬──────────┘
           │
           ▼
    [More rounds?]───────┐
           │             │
           ▼             │
┌─────────────────────┐  │
│ Continuation Context│──┘
│ - Existing findings │
│ - Target categories │
└─────────────────────┘
```

## Categories

Each analysis type has predefined categories that the framework tracks for coverage:

### Security Analysis (10 categories)
- Authentication/Identity
- Authorization/Access Control
- Input Validation/Injection
- Data Protection/Cryptography
- Session Management
- Error Handling/Information Leakage
- Logging/Audit
- API Security
- Business Logic
- Third-Party/Supply Chain

### Privacy Analysis (LINDDUN - 10 categories)
- Linking
- Identifying
- Non-Repudiation
- Detecting
- Data Disclosure
- Unawareness
- Non-Compliance
- Data Minimization
- Retention/Deletion
- Cross-Border Transfer

### Compliance Analysis (9 categories)
- Access Control (SOC2/HIPAA/PCI)
- Data Protection
- Audit Logging
- Incident Response
- Availability/Continuity
- Vulnerability Management
- Network Security
- PHI Handling (HIPAA)
- Cardholder Data (PCI)

### Engineering Analysis (8 categories)
- Code Complexity
- Technical Debt
- Test Coverage
- Documentation
- Maintainability
- Performance Concerns
- Scalability
- Implementation Feasibility

### Architecture Analysis (8 categories)
- API Design
- Service Boundaries
- Data Architecture
- Dependencies
- Resilience Patterns
- Scalability Design
- Breaking Changes
- Architectural Patterns

## Configuration

### Feature Flags

Enable iterative analysis per review type via environment variables:

```bash
# Global max rounds (default: 5)
export ITERATIVE_ANALYSIS_MAX_ROUNDS=5

# Enable per analysis type
export ENABLE_ITERATIVE_SECURITY_ANALYSIS=true
export ENABLE_ITERATIVE_PRIVACY_ANALYSIS=true
export ENABLE_ITERATIVE_COMPLIANCE_ANALYSIS=true
export ENABLE_ITERATIVE_ENGINEERING_ANALYSIS=true
export ENABLE_ITERATIVE_ARCHITECTURE_ANALYSIS=true
```

### Programmatic Configuration

```python
from context_graph.llm.analysis_categories import (
    IterativeAnalysisConfig,
    AnalysisTypeCategories,
    get_analysis_config,
)

# Get default config for security
config = get_analysis_config(AnalysisTypeCategories.SECURITY)

# Or create custom config
custom_config = IterativeAnalysisConfig(
    analysis_type=AnalysisTypeCategories.SECURITY,
    categories=SECURITY_CATEGORIES,
    max_rounds=3,                         # Maximum iteration rounds
    min_findings_per_round=2,             # Minimum new findings expected per round
    max_uncovered_categories_to_stop=2,   # Stop if <=N categories uncovered
    stop_on_no_new_findings=True,         # Stop if round produces no new findings
)
```

## Usage

### Using ParallelLLMAnalyzer

The `ParallelLLMAnalyzer` provides iterative versions of all review methods:

```python
from context_graph.llm.parallel_analyzer import ParallelLLMAnalyzer

analyzer = ParallelLLMAnalyzer()

# Iterative security review
result = await analyzer.security_review_iterative(
    prd_intent=intent,
    codebase_state=state,
    security_delta=delta,
)

# Iterative privacy review
result = await analyzer.privacy_review_iterative(...)

# Iterative compliance review
result = await analyzer.compliance_review_iterative(...)

# Iterative engineering review
result = await analyzer.engineering_review_iterative(...)

# Iterative architecture review
result = await analyzer.architecture_review_iterative(...)
```

### Using IterativeAnalyzer Directly

For custom analysis types:

```python
from context_graph.llm.iterative_analyzer import IterativeAnalyzer, LLMCallResult
from context_graph.llm.analysis_categories import AnalysisTypeCategories

async def my_llm_call(context: str, metadata: dict) -> LLMCallResult:
    # Your LLM call implementation
    response = await call_llm(context)
    return LLMCallResult(
        structured_data=response,
        was_truncated=False,
        stop_reason="end_turn",
        latency_ms=100,
        tokens_used=1000,
    )

analyzer = IterativeAnalyzer(
    analysis_type=AnalysisTypeCategories.SECURITY,
    llm_call_fn=my_llm_call,
    finding_key="findings",       # Key in response containing findings
    finding_id_field="id",        # Field name for finding ID
    finding_category_field="category",  # Field name for category
    verbose=True,                 # Print progress to stderr
)

result = await analyzer.analyze(initial_context)

print(f"Total findings: {len(result.findings)}")
print(f"Rounds used: {result.total_rounds}")
print(f"Categories covered: {result.covered_categories}")
```

## Deduplication

The framework implements two-level deduplication:

### 1. ID-Based Deduplication (Within Rounds)
Findings with the same ID are deduplicated across iterative rounds:
```python
if finding_id and finding_id not in existing_finding_ids:
    all_findings.append(finding)
    existing_finding_ids.add(finding_id)
```

### 2. Signature-Based Deduplication (Across Providers)
When using parallel LLM providers, findings are deduplicated using a signature:
```python
def _finding_signature(finding: dict) -> str:
    title = finding.get("title", "").lower()[:30]
    category = finding.get("category", "").lower()
    severity = finding.get("severity", "").lower()
    return f"{severity}:{category}:{title}"
```

## Generation Metadata

LLM responses should include `generation_metadata` for iteration control:

```json
{
  "findings": [...],
  "generation_metadata": {
    "analysis_complete": false,
    "continuation_needed": true,
    "last_finding_id": "F5",
    "remaining_categories_to_analyze": ["Session Management", "API Security"],
    "total_findings_in_response": 5,
    "covered_categories": ["Authentication", "Authorization", "Input Validation"]
  }
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `analysis_complete` | bool | True if LLM has identified all findings |
| `continuation_needed` | bool | True if more findings could be found |
| `last_finding_id` | string | ID of the last finding in response |
| `remaining_categories_to_analyze` | list | Categories not yet covered |
| `total_findings_in_response` | int | Count of findings in this response |
| `covered_categories` | list | Categories covered so far |

## Stopping Conditions

The framework stops iteration when:

1. **Analysis Complete**: LLM signals `analysis_complete: true` AND no new findings
2. **Coverage Achieved**: Most categories covered AND LLM signals complete
3. **Max Rounds**: Reached maximum configured rounds
4. **No Progress**: No new findings AND response wasn't truncated

## Best Practices

1. **Set Appropriate Max Rounds**: 3-5 rounds is typically sufficient
2. **Monitor Token Usage**: Each round adds to total cost
3. **Check Category Coverage**: Review `uncovered_categories` in results
4. **Enable Verbose Mode**: Use for debugging/understanding iteration flow
5. **Custom Categories**: Extend categories for domain-specific analysis

## Troubleshooting

### No New Findings After Round 1
- Check if LLM is receiving continuation context
- Verify `generation_metadata` is being parsed correctly
- Increase `min_findings_per_round` threshold

### Too Many Rounds
- Lower `max_rounds` in config
- Set stricter `max_uncovered_categories_to_stop`
- Check if LLM is properly signaling `analysis_complete`

### Missing Categories
- Verify category keywords match your domain
- Check `_detect_category()` logic
- Consider adding custom categories
