# Intently — Comprehensive Evals List

This document catalogs every evaluation needed for the Intently platform, organized by functional area. Each eval includes what to measure, suggested metrics, and example test cases.

---

## Table of Contents

1. [PRD Parsing & Intent Extraction](#1-prd-parsing--intent-extraction)
2. [Codebase Analysis & State Extraction](#2-codebase-analysis--state-extraction)
3. [Delta Analysis (Intent vs State)](#3-delta-analysis-intent-vs-state)
4. [Security Review Findings](#4-security-review-findings)
5. [Privacy Review Findings](#5-privacy-review-findings)
6. [Compliance Review Findings](#6-compliance-review-findings)
7. [Engineering Review Findings](#7-engineering-review-findings)
8. [Architecture Review Findings](#8-architecture-review-findings)
9. [Cross-Functional Detection](#9-cross-functional-detection)
10. [False Positive Filtering](#10-false-positive-filtering)
11. [Iterative Analysis](#11-iterative-analysis)
12. [Parallel / Multi-Provider Analysis](#12-parallel--multi-provider-analysis)
13. [PRD Quality Scoring](#13-prd-quality-scoring)
14. [Effort Estimation](#14-effort-estimation)
15. [PRD Change Suggestions](#15-prd-change-suggestions)
16. [PRD Generator](#16-prd-generator)
17. [Product Chat](#17-product-chat)
18. [Codebase Chat & Semantic Search](#18-codebase-chat--semantic-search)
19. [Threat Canvas](#19-threat-canvas)
20. [Approval Gates](#20-approval-gates)
21. [End-to-End Pipeline](#21-end-to-end-pipeline)
22. [Regression & Baseline Drift](#22-regression--baseline-drift)
23. [Latency & Cost](#23-latency--cost)

---

## 1. PRD Parsing & Intent Extraction

**Module**: `parsers/prd_parser.py`, `parsers/markdown_parser.py`, `parsers/notion_parser.py`
**LLM Analysis Type**: `INTENT_EXTRACTION`

### What to Evaluate

| Eval ID | Eval Name | Description | Metric |
|---------|-----------|-------------|--------|
| PARSE-01 | Feature extraction completeness | All features listed in a PRD are extracted into `Intent.features` | Recall (features found / features in ground truth) |
| PARSE-02 | User story extraction | User stories are correctly parsed with actor, action, and outcome | F1 score against labeled user stories |
| PARSE-03 | Data entity detection | PII and data entities mentioned in PRD are captured in `Intent.data_entities` | Precision & recall vs labeled entities |
| PARSE-04 | API change detection | New/modified API endpoints described in PRD are captured in `Intent.api_changes` | Recall of API changes |
| PARSE-05 | Auth requirement extraction | Authentication and authorization requirements are captured in `Intent.auth_requirements` | Recall & accuracy |
| PARSE-06 | Integration extraction | Third-party integrations and external dependencies are identified | Recall |
| PARSE-07 | Markdown format robustness | Parser handles various markdown styles (tables, nested lists, code blocks, frontmatter) | Pass rate across format variants |
| PARSE-08 | Notion format robustness | Notion-exported markdown is correctly parsed | Pass rate |
| PARSE-09 | Ambiguous PRD handling | Parser flags ambiguous or underspecified sections rather than hallucinating intent | Precision (no false positives from ambiguity) |
| PARSE-10 | Large PRD handling | PRDs >10k words parse without truncation or missing sections | Completeness score |

### Example Test Cases

- **Golden PRDs**: 10-20 real or synthetic PRDs with hand-labeled features, data entities, API changes, and auth requirements
- **Edge cases**: PRD with no explicit features section, PRD in bullet-only format, PRD with embedded diagrams/images
- **Adversarial**: PRD with contradictory requirements, extremely long PRD, PRD with non-English sections

---

## 2. Codebase Analysis & State Extraction

**Modules**: `analyzers/codebase_analyzer.py`, `analyzers/python_analyzer.py`, `analyzers/typescript_analyzer.py`, `analyzers/kotlin_analyzer.py`, `analyzers/yaml_analyzer.py`, `analyzers/json_analyzer.py`, `analyzers/infrastructure_analyzer.py`

### What to Evaluate

| Eval ID | Eval Name | Description | Metric |
|---------|-----------|-------------|--------|
| CODE-01 | API endpoint detection | All REST/GraphQL endpoints are found across languages | Recall & precision vs ground truth |
| CODE-02 | Data model extraction | ORM models, schemas, and data classes are identified | F1 score |
| CODE-03 | Auth pattern detection | Auth middleware, decorators, guards are found in `State.auth_patterns` | Recall |
| CODE-04 | Entity extraction accuracy | Entities (User, Data, PII, API, Service, etc.) are correctly typed | Type accuracy |
| CODE-05 | Relationship extraction | Data flows, reads/writes, auth relationships are captured | Precision & recall |
| CODE-06 | Existing controls detection | Security controls already in the codebase (CSRF, rate limiting, encryption) are found | Recall |
| CODE-07 | Multi-language support | Analysis quality doesn't degrade across Python, TypeScript, Kotlin, YAML, JSON | Per-language F1 |
| CODE-08 | Large codebase scalability | Codebases with 1000+ files complete analysis within timeout | Completion rate, time |
| CODE-09 | Monorepo handling | Correctly scopes analysis to relevant directories in monorepos | Precision (no noise from irrelevant dirs) |
| CODE-10 | Infrastructure config detection | Docker, K8s, Terraform configs analyzed for security settings | Recall of infra controls |

### Example Test Cases

- **Golden codebases**: 5-10 sample codebases with labeled endpoints, models, auth patterns, and controls
- **Language coverage**: FastAPI app, Express/NestJS app, Spring Boot app, mixed-language repo
- **Scale test**: Large OSS repos (e.g., 500+ files) with known API surface

---

## 3. Delta Analysis (Intent vs State)

**Module**: `security/delta_analyzer.py`

### What to Evaluate

| Eval ID | Eval Name | Description | Metric |
|---------|-----------|-------------|--------|
| DELTA-01 | New endpoint detection | Endpoints in intent but not in state are flagged as new attack surface | Recall |
| DELTA-02 | Modified endpoint detection | Endpoints changing behavior (new params, auth changes) are detected | Recall |
| DELTA-03 | New data model detection | Data models introduced by the PRD are identified | Recall |
| DELTA-04 | New data flow detection | New data flows (especially PII flows) are captured | Recall |
| DELTA-05 | PII introduction flag | `introduces_pii` flag is correctly set when PRD adds PII handling | Accuracy (binary) |
| DELTA-06 | External integration flag | `introduces_external_integration` correctly set | Accuracy (binary) |
| DELTA-07 | Auth flow modification flag | `modifies_auth_flow` correctly set when PRD changes auth | Accuracy (binary) |
| DELTA-08 | Trust boundary impact | Trust boundary crossings are detected when PRD introduces cross-service calls | Recall |
| DELTA-09 | False negative rate | Real gaps between intent and state are not missed | 1 - false negative rate |
| DELTA-10 | Noise rate | Delta items that aren't actually new (already in codebase) are rare | Precision |

### Example Test Cases

- **Greenfield PRD**: PRD for a completely new feature against existing codebase — all items should be "new"
- **Incremental PRD**: PRD modifying existing auth — delta should capture auth changes but not re-flag existing endpoints
- **No-op PRD**: PRD describing what already exists — delta should be nearly empty

---

## 4. Security Review Findings

**Modules**: `security/review_engine.py`, `security/threat_patterns.py`, LLM analysis type `SECURITY_REVIEW`

### What to Evaluate

| Eval ID | Eval Name | Description | Metric |
|---------|-----------|-------------|--------|
| SEC-01 | Finding relevance | Security findings are relevant to the PRD + codebase (not generic) | Precision (% relevant) |
| SEC-02 | Finding completeness | Known security issues in ground truth are found | Recall |
| SEC-03 | Severity accuracy | Severity ratings (critical/high/medium/low) match expert judgment | Severity agreement rate, MAE |
| SEC-04 | STRIDE coverage | Findings span Spoofing, Tampering, Repudiation, Info Disclosure, DoS, Elevation | Category coverage |
| SEC-05 | OWASP Top 10 coverage | Findings address relevant OWASP categories for the codebase | Coverage of applicable categories |
| SEC-06 | Remediation quality | Recommended mitigations are actionable and technically correct | Expert rating (1-5 scale) |
| SEC-07 | Evidence grounding | Each finding references specific PRD sections, endpoints, or code patterns | % findings with concrete evidence |
| SEC-08 | Deduplication | No duplicate findings covering the same issue | Duplicate rate |
| SEC-09 | Confidence calibration | Confidence scores correlate with actual correctness | Brier score / calibration curve |
| SEC-10 | Pattern-matched vs LLM findings | Pattern-based findings are complementary to (not duplicative of) LLM findings | Overlap rate, unique contribution % |

### Example Test Cases

- **OWASP Juice Shop**: Run against intentionally vulnerable app; expect all known vulns found
- **Secure baseline**: Run against well-secured app; expect minimal findings, no false criticals
- **Auth-heavy PRD**: PRD adding OAuth2 + RBAC; expect findings around token handling, scope escalation

---

## 5. Privacy Review Findings

**Module**: `security/privacy_analyzer.py`, LLM analysis type `PRIVACY_REVIEW`

### What to Evaluate

| Eval ID | Eval Name | Description | Metric |
|---------|-----------|-------------|--------|
| PRIV-01 | PII flow detection | All PII data flows (collection, storage, sharing, deletion) are identified | Recall |
| PRIV-02 | LINDDUN coverage | Findings span Linkability, Identifiability, Non-repudiation, Detectability, Disclosure, Unawareness, Non-compliance | Category coverage |
| PRIV-03 | GDPR requirement mapping | GDPR-relevant findings (consent, right to erasure, data portability) are flagged | Recall of applicable articles |
| PRIV-04 | CCPA requirement mapping | CCPA-relevant findings (opt-out, data sale disclosure) are flagged | Recall |
| PRIV-05 | Data minimization check | Findings flag unnecessary PII collection or over-retention | Precision & recall |
| PRIV-06 | Third-party data sharing | Sharing PII with external services is detected | Recall |
| PRIV-07 | Severity appropriateness | PII-related findings are not under-rated (e.g., PII leak not marked "low") | % correctly rated |
| PRIV-08 | Consent flow coverage | Missing or incomplete consent flows are flagged | Recall |

### Example Test Cases

- **User registration PRD**: Expect findings on PII storage, consent, password handling
- **Analytics PRD**: Expect findings on tracking, data minimization, cookie consent
- **Healthcare PRD**: Expect elevated privacy findings for PHI handling

---

## 6. Compliance Review Findings

**Module**: `security/compliance_analyzer.py`, LLM analysis type `COMPLIANCE_REVIEW`

### What to Evaluate

| Eval ID | Eval Name | Description | Metric |
|---------|-----------|-------------|--------|
| COMP-01 | SOC 2 mapping accuracy | Findings correctly reference SOC 2 Trust Services Criteria | Mapping accuracy |
| COMP-02 | HIPAA mapping accuracy | Findings correctly reference HIPAA safeguards (Administrative, Physical, Technical) | Mapping accuracy |
| COMP-03 | PCI-DSS mapping accuracy | Findings correctly reference PCI-DSS requirements | Mapping accuracy |
| COMP-04 | ISO 27001 mapping accuracy | Findings correctly reference ISO 27001 controls | Mapping accuracy |
| COMP-05 | Framework relevance | Only applicable frameworks are flagged (e.g., HIPAA not flagged for non-healthcare) | Precision |
| COMP-06 | Control gap identification | Missing compliance controls are identified vs existing ones | Recall |
| COMP-07 | Remediation specificity | Compliance remediations reference specific control requirements, not generic advice | Expert rating |
| COMP-08 | Cross-framework deduplication | Same underlying issue mapped to multiple frameworks is shown once with all mappings | Dedup quality |

### Example Test Cases

- **Healthcare SaaS PRD**: Expect HIPAA + SOC 2 findings; PCI-DSS should not appear unless payment processing present
- **E-commerce PRD**: Expect PCI-DSS + GDPR/CCPA findings for payment and user data
- **Internal tool PRD**: Expect minimal compliance findings; only SOC 2 if applicable

---

## 7. Engineering Review Findings

**Modules**: `analyzers/engineering_analyzer.py`, `security/engineering_patterns.py`

### What to Evaluate

| Eval ID | Eval Name | Description | Metric |
|---------|-----------|-------------|--------|
| ENG-01 | Anti-pattern detection | Common anti-patterns (N+1 queries, missing error handling, hardcoded secrets) are found | Recall |
| ENG-02 | Pattern match precision | Flagged engineering issues are real problems, not false positives | Precision |
| ENG-03 | Complexity assessment | Complexity estimates correlate with actual implementation difficulty | Correlation coefficient |
| ENG-04 | Dependency risk detection | Outdated, vulnerable, or unmaintained dependencies are flagged | Recall |
| ENG-05 | Testing gap identification | Missing test coverage for critical paths is flagged | Recall |
| ENG-06 | Error handling completeness | Missing error handling for external calls, DB operations, etc. is detected | Recall |
| ENG-07 | Performance concern detection | Obvious performance issues (unbounded queries, missing pagination, N+1) are flagged | Recall |
| ENG-08 | Severity calibration | Engineering finding severities are appropriate (not everything is "critical") | Distribution quality (no severity inflation) |

### Example Test Cases

- **Well-engineered codebase**: Expect few findings, mostly informational
- **Legacy codebase**: Expect findings on error handling, missing types, outdated patterns
- **New feature PRD**: Expect engineering guidance on implementation approach

---

## 8. Architecture Review Findings

**Modules**: `analyzers/architecture_analyzer.py`, `security/architecture_patterns.py`

### What to Evaluate

| Eval ID | Eval Name | Description | Metric |
|---------|-----------|-------------|--------|
| ARCH-01 | Architectural pattern recognition | Existing patterns (MVC, microservices, event-driven) are correctly identified | Accuracy |
| ARCH-02 | Consistency violation detection | PRD-proposed architecture that conflicts with existing patterns is flagged | Recall |
| ARCH-03 | Coupling analysis | Tight coupling and dependency cycles are detected | Recall |
| ARCH-04 | Scalability concern detection | Designs that won't scale (single-point-of-failure, stateful services) are flagged | Recall |
| ARCH-05 | API design quality | Poor API design (inconsistent naming, missing versioning, breaking changes) is flagged | Precision & recall |
| ARCH-06 | Data model fitness | Mismatches between PRD data requirements and existing schema are detected | Recall |
| ARCH-07 | Service boundary analysis | Incorrect service boundaries (shared databases, circular deps) are flagged | Recall |
| ARCH-08 | Migration risk assessment | Findings flag risks of proposed architecture changes on existing system | Coverage |

### Example Test Cases

- **Microservice split PRD**: Expect findings on data consistency, network calls, service discovery
- **Monolith PRD**: Expect findings on modularity, separation of concerns
- **Database migration PRD**: Expect findings on backward compatibility, migration strategy

---

## 9. Cross-Functional Detection

**Module**: `security/cross_functional_detector.py`

### What to Evaluate

| Eval ID | Eval Name | Description | Metric |
|---------|-----------|-------------|--------|
| CROSS-01 | Multi-dimension finding detection | Issues that span dimensions (e.g., security + compliance) are tagged to all relevant dimensions | Dimension coverage per finding |
| CROSS-02 | Deduplication quality | Same underlying issue appearing in multiple dimensions is linked, not duplicated | Dedup rate |
| CROSS-03 | Priority escalation | A finding that is "medium" in one dimension but "high" cross-functionally is correctly escalated | Escalation accuracy |
| CROSS-04 | Cross-impact accuracy | The cross-functional impact description is accurate and not hallucinated | Expert rating |

---

## 10. False Positive Filtering

**Module**: `llm/false_positive_filter.py`

### What to Evaluate

| Eval ID | Eval Name | Description | Metric |
|---------|-----------|-------------|--------|
| FP-01 | True positive preservation | Real findings are not incorrectly removed | Recall (true positives retained) |
| FP-02 | False positive removal rate | Generic / mitigated / speculative findings are removed | Precision improvement |
| FP-03 | Context validation accuracy | Findings already mitigated by existing controls are correctly identified | Accuracy per strategy |
| FP-04 | Specificity check accuracy | Generic boilerplate findings are correctly identified | Accuracy per strategy |
| FP-05 | Evidence grounding accuracy | Speculative findings without concrete evidence are correctly identified | Accuracy per strategy |
| FP-06 | Parallel vs sequential agreement | Both modes produce similar quality outcomes | Agreement rate |
| FP-07 | Majority vote correctness | 2-of-3 majority vote makes the right call | Vote accuracy |
| FP-08 | Multi-iteration stability | Running multiple iterations converges (doesn't oscillate) | Convergence rate |
| FP-09 | Critical finding preservation | Critical-severity findings are never incorrectly filtered | 100% retention of true critical |
| FP-10 | Filter throughput | Filtering doesn't remove >50% of findings (quality gate) | Removal rate distribution |

### Example Test Cases

- **Known FP set**: 20+ findings manually labeled as TP or FP; measure filter accuracy
- **Hardened codebase**: Findings against a well-secured codebase should have high FP removal
- **Vulnerable codebase**: Findings against an intentionally vulnerable codebase should have high TP retention

---

## 11. Iterative Analysis

**Module**: `llm/iterative_analyzer.py`

### What to Evaluate

| Eval ID | Eval Name | Description | Metric |
|---------|-----------|-------------|--------|
| ITER-01 | Category coverage improvement | Later rounds find findings in categories missed by round 1 | New categories per round |
| ITER-02 | Diminishing returns detection | Analysis correctly stops when no new findings are emerging | Rounds to convergence |
| ITER-03 | Deduplication across rounds | Findings from later rounds don't duplicate earlier ones | Cross-round duplicate rate |
| ITER-04 | Continuation context quality | The context passed to subsequent rounds is accurate and helpful | Finding quality in round N vs round 1 |
| ITER-05 | Max rounds safety | Analysis respects `max_rounds` config and terminates | Termination rate |
| ITER-06 | Finding quality by round | Findings from later rounds are comparable quality to round 1 (not degrading) | Quality score by round |

---

## 12. Parallel / Multi-Provider Analysis

**Module**: `llm/parallel_analyzer.py`

### What to Evaluate

| Eval ID | Eval Name | Description | Metric |
|---------|-----------|-------------|--------|
| PAR-01 | Provider complementarity | Different providers find different findings (not just duplicates) | Unique finding rate per provider |
| PAR-02 | Consensus finding quality | Findings agreed upon by multiple providers are higher quality | Consensus vs single-provider precision |
| PAR-03 | Divergent finding triage | Divergent findings (found by only one provider) are correctly handled | Expert review of divergent set |
| PAR-04 | Merge quality | Merged findings are coherent (no contradictory info from different providers) | Coherence score |
| PAR-05 | Single-provider fallback | Analysis quality is acceptable when only one provider is available | Quality delta (single vs dual) |
| PAR-06 | Token efficiency | Parallel analysis doesn't use >2x tokens compared to single-provider | Token ratio |

---

## 13. PRD Quality Scoring

**Module**: `pm/quality_scorer.py`

### What to Evaluate

| Eval ID | Eval Name | Description | Metric |
|---------|-----------|-------------|--------|
| QUAL-01 | Score calibration | Scores correlate with expert-rated PRD quality | Spearman correlation |
| QUAL-02 | Grade thresholds | Grade boundaries (A/B/C/D/F) align with intuitive quality | Expert agreement rate |
| QUAL-03 | Gap identification | Identified gaps are real missing sections (not noise) | Precision |
| QUAL-04 | Gap completeness | All significant quality gaps are identified | Recall |
| QUAL-05 | Score sensitivity | Score meaningfully differentiates between good and poor PRDs | Score spread (std dev) across PRD corpus |
| QUAL-06 | Score stability | Same PRD scored twice produces same result (deterministic) | Score variance on repeated runs |
| QUAL-07 | Blocker detection accuracy | Items flagged as "blockers" are genuinely blocking issues | Expert agreement rate |

### Example Test Cases

- **High-quality PRD**: Well-structured, complete PRD; expect score >85, grade A
- **Minimal PRD**: One-paragraph PRD with no details; expect score <40, grade D/F
- **Partial PRD**: Good feature spec but missing auth/privacy sections; expect medium score with specific gaps

---

## 14. Effort Estimation

**Module**: `pm/effort_estimator.py`

### What to Evaluate

| Eval ID | Eval Name | Description | Metric |
|---------|-----------|-------------|--------|
| EFF-01 | Range accuracy | Actual implementation time falls within estimated min-max range | % within range |
| EFF-02 | Central estimate accuracy | "Likely" estimate is close to actual | MAPE (Mean Absolute Percentage Error) |
| EFF-03 | Codebase support accuracy | `codebase_support` percentage reflects actual pattern reuse | Correlation with actual reuse |
| EFF-04 | Sprint calculation reasonableness | Sprint estimates are reasonable for typical team sizes | Expert rating |
| EFF-05 | Per-requirement breakdown | Individual requirement estimates sum sensibly to total | Consistency check |
| EFF-06 | Complexity sensitivity | More complex findings get higher effort estimates | Monotonicity with complexity |

### Example Test Cases

- **Simple CRUD PRD**: Expect low effort (1-3 days); high codebase support if similar CRUDs exist
- **Auth system PRD**: Expect higher effort (1-2 weeks); medium codebase support
- **Greenfield PRD**: Expect low codebase support; wider min-max range

---

## 15. PRD Change Suggestions

**Module**: `pm/diff_generator.py` (PRD change generator)

### What to Evaluate

| Eval ID | Eval Name | Description | Metric |
|---------|-----------|-------------|--------|
| CHG-01 | Change relevance | Suggested PRD changes address real gaps identified by review | Precision |
| CHG-02 | Change completeness | All significant gaps have corresponding change suggestions | Recall |
| CHG-03 | Change quality | Suggested text is well-written and integrates naturally with PRD | Expert rating (1-5) |
| CHG-04 | Change correctness | Suggested changes are technically accurate | Accuracy |
| CHG-05 | Accept rate | Percentage of suggested changes accepted by PMs in practice | Accept rate |
| CHG-06 | Undo rate | Percentage of accepted changes later undone | Undo rate (lower is better) |
| CHG-07 | Side-by-side diff clarity | Diff presentation clearly shows what changed and why | User satisfaction |

---

## 16. PRD Generator

**Module**: `pm/prd_generator.py`

### What to Evaluate

| Eval ID | Eval Name | Description | Metric |
|---------|-----------|-------------|--------|
| GEN-01 | Feature coverage | Generated PRD covers all significant features in the codebase | Recall of features |
| GEN-02 | API documentation accuracy | Generated API docs match actual endpoints (method, path, params) | Accuracy |
| GEN-03 | Data model documentation | Generated data model docs match actual schema | Accuracy |
| GEN-04 | Section structure | Generated PRD has appropriate sections (overview, features, API, data model, auth, etc.) | Completeness |
| GEN-05 | Technical accuracy | Generated descriptions are technically correct (no hallucinated features) | Precision |
| GEN-06 | Readability | Generated PRD is well-organized and readable | Expert rating |
| GEN-07 | Section confidence | Confidence scores correlate with actual section accuracy | Calibration |
| GEN-08 | Output format quality | Generated Markdown/JSON/HTML is well-formed and renders correctly | Format validity rate |

### Example Test Cases

- **Sample codebase**: Generate PRD for `examples/sample-codebase/`; compare against known feature set
- **Intently itself**: Generate PRD for this project; verify it captures major features
- **Minimal codebase**: Single-file API; expect concise, accurate PRD

---

## 17. Product Chat

**Module**: `chat/product_chat.py`

### What to Evaluate

| Eval ID | Eval Name | Description | Metric |
|---------|-----------|-------------|--------|
| CHAT-01 | Answer correctness | Answers are factually correct given the context graph and review data | Accuracy |
| CHAT-02 | Citation accuracy | Citations reference real reviews, findings, entities, or patterns | Citation precision |
| CHAT-03 | Citation completeness | All relevant sources are cited (not just one) | Citation recall |
| CHAT-04 | Grounding quality | Answers are grounded in actual data (not hallucinated) | Grounding score |
| CHAT-05 | Context utilization | Chat uses review history, collaboration data, and patterns effectively | Context usage rate |
| CHAT-06 | Conversational coherence | Multi-turn conversations maintain context and coherence | Coherence rating |
| CHAT-07 | Refusal quality | Chat appropriately refuses questions it cannot answer from available data | Refusal accuracy |
| CHAT-08 | Streaming consistency | Streamed responses match non-streamed responses | Consistency rate |

### Example Test Cases

- **"What are the top security risks?"**: Expect answer citing actual security findings from latest review
- **"Has this issue been addressed?"**: Expect answer checking validation status and lifecycle
- **"What patterns have we learned?"**: Expect answer citing learned patterns from collaboration data
- **Out-of-scope question**: Expect graceful refusal with explanation

---

## 18. Codebase Chat & Semantic Search

**Module**: `chat/vector_index.py`, `chat/product_chat.py` (codebase-aware mode)

### What to Evaluate

| Eval ID | Eval Name | Description | Metric |
|---------|-----------|-------------|--------|
| SEARCH-01 | Retrieval relevance | Top-k results are relevant to the query | nDCG@k, MRR |
| SEARCH-02 | Code snippet accuracy | Retrieved code snippets are the correct files/functions for the question | Precision@k |
| SEARCH-03 | Embedding quality | Similar code concepts cluster together in embedding space | Clustering quality (silhouette score) |
| SEARCH-04 | Chunking quality | Code chunks preserve meaningful context (not split mid-function) | Chunk coherence score |
| SEARCH-05 | TF-IDF fallback quality | When ChromaDB unavailable, TF-IDF fallback provides acceptable results | Quality delta vs embedding |
| SEARCH-06 | Index build time | Indexing 1000+ files completes within reasonable time | Time to index |
| SEARCH-07 | Large codebase handling | Search quality maintained at scale (2000 files) | Quality at scale vs small corpus |

---

## 19. Threat Canvas

**Module**: `security/canvas_threat_analyzer.py`, API routes in `threat_canvas_routes.py`

### What to Evaluate

| Eval ID | Eval Name | Description | Metric |
|---------|-----------|-------------|--------|
| CANVAS-01 | AI threat suggestion relevance | Suggested threats are relevant to the canvas context | Precision |
| CANVAS-02 | Threat suggestion completeness | Important threats are not missed | Recall |
| CANVAS-03 | Populate from review accuracy | Populating canvas from review results produces accurate threat mappings | Accuracy |
| CANVAS-04 | Threat categorization | Threats are correctly categorized (STRIDE, OWASP) | Category accuracy |
| CANVAS-05 | Mitigation suggestion quality | Suggested mitigations are actionable and appropriate | Expert rating |
| CANVAS-06 | Export quality | Exported canvas is well-structured and useful | Format quality |

---

## 20. Approval Gates

**Module**: `governance/gate_evaluator.py`

### What to Evaluate

| Eval ID | Eval Name | Description | Metric |
|---------|-----------|-------------|--------|
| GATE-01 | Gate condition evaluation accuracy | Conditions like `no_unresolved_critical` and `quality_score_above:70` evaluate correctly | Accuracy |
| GATE-02 | Blocking vs warning distinction | Blocking gates block, warning gates warn — no misclassification | Accuracy |
| GATE-03 | Team approval detection | `team_approved:security` correctly checks collaboration data | Accuracy |
| GATE-04 | Edge case handling | Gates handle missing data (no reviews, no validations) gracefully | Error rate |

---

## 21. End-to-End Pipeline

**What to Evaluate**: Full review cycle from PRD input to final report.

| Eval ID | Eval Name | Description | Metric |
|---------|-----------|-------------|--------|
| E2E-01 | Review completion rate | Reviews complete without errors for valid inputs | Completion rate |
| E2E-02 | Report quality | Final report (Markdown/dashboard) is comprehensive and actionable | Expert rating |
| E2E-03 | Executive summary accuracy | Executive summary correctly reflects the findings | Faithfulness score |
| E2E-04 | Finding count reasonableness | Finding count is in expected range (not 0 and not 500) | Distribution check |
| E2E-05 | Dimension coverage | All requested dimensions have findings in the report | Coverage rate |
| E2E-06 | Graph visualization quality | D3 graph (nodes/edges) is meaningful and navigable | Usability rating |
| E2E-07 | Trace completeness | SSE trace stream captures all pipeline stages | Stage coverage |
| E2E-08 | Idempotency | Same PRD + codebase produces consistent results across runs | Result stability score |
| E2E-09 | Error recovery | Pipeline recovers gracefully from partial LLM failures | Recovery rate |
| E2E-10 | Bulk analysis quality | Bulk PRD analysis produces per-PRD results of equal quality to single | Quality parity |

### Example Test Cases

- **Happy path**: Sample PRD + sample codebase → complete review with findings across all dimensions
- **LLM failure**: Simulate provider timeout → expect graceful degradation to available provider
- **Empty codebase**: PRD with no codebase → expect intent analysis only, appropriate messaging
- **Bulk batch of 5 PRDs**: Expect all 5 complete with consistent quality

---

## 22. Regression & Baseline Drift

**Existing infrastructure**: `baseline/` directory, `scripts/compare_analysis.py`

| Eval ID | Eval Name | Description | Metric |
|---------|-----------|-------------|--------|
| REG-01 | Baseline comparison | New analysis results compared against stored baselines | Delta in findings count, severity distribution |
| REG-02 | Finding stability | Core findings persist across code changes (not lost on refactor) | Core finding retention rate |
| REG-03 | Score drift | Quality scores, effort estimates don't drift significantly without code changes | Score delta on unchanged inputs |
| REG-04 | Model upgrade impact | Switching LLM model version doesn't catastrophically change results | Quality delta on model switch |
| REG-05 | Prompt regression | Changes to system prompts don't degrade finding quality | Before/after quality comparison |

---

## 23. Latency & Cost

| Eval ID | Eval Name | Description | Metric |
|---------|-----------|-------------|--------|
| PERF-01 | Single review latency | Time from review creation to completion | P50, P95, P99 latency |
| PERF-02 | Parsing latency | PRD parse time | P95 time |
| PERF-03 | Codebase analysis latency | Codebase analysis time by repo size | Time vs file count |
| PERF-04 | LLM call latency | Per-call LLM latency by provider | P95 per provider |
| PERF-05 | Token usage per review | Total tokens consumed per review by dimension | Mean tokens per dimension |
| PERF-06 | Cost per review | Dollar cost per review (tokens × price) | Mean cost |
| PERF-07 | FP filter overhead | Additional time/cost from false positive filtering | % overhead |
| PERF-08 | Iterative analysis overhead | Additional time/cost from multi-round analysis | % overhead vs single-round |
| PERF-09 | Chat response latency | Time to first token and full response | TTFT, P95 total |
| PERF-10 | Vector index build time | Time to build/refresh codebase index | Time by codebase size |

---

## Eval Infrastructure Recommendations

### Priority Order for Implementation

1. **P0 — Ship-blocking evals** (build first):
   - SEC-01 to SEC-03 (security finding quality — the core product)
   - FP-01, FP-02 (false positive filter — directly impacts user trust)
   - E2E-01 (completion rate — must not crash)
   - PARSE-01 to PARSE-03 (intent extraction — garbage in, garbage out)
   - CODE-01 to CODE-03 (state extraction — same)

2. **P1 — Quality bar evals** (build next):
   - PRIV-01, PRIV-02 (privacy findings)
   - COMP-01 to COMP-03 (compliance accuracy)
   - QUAL-01, QUAL-02 (quality scoring calibration)
   - CHAT-01, CHAT-02 (chat correctness)
   - REG-01 (baseline regression)
   - PERF-01, PERF-06 (latency and cost monitoring)

3. **P2 — Comprehensive evals** (build over time):
   - All remaining dimension-specific evals
   - ITER-*, PAR-* (iterative and parallel analysis)
   - GEN-* (PRD generator)
   - CANVAS-* (threat canvas)
   - EFF-* (effort estimation)
   - SEARCH-* (semantic search)

### Suggested Eval Dataset

| Dataset | Contents | Size |
|---------|----------|------|
| Golden PRDs | Hand-annotated PRDs with labeled features, entities, auth requirements | 15-20 PRDs |
| Golden Codebases | Codebases with labeled endpoints, models, auth patterns, controls | 5-10 repos |
| Labeled Findings | Findings manually labeled as TP/FP with correct severity | 200+ findings |
| Expert Reviews | Complete reviews rated by security experts (ground truth) | 10-15 reviews |
| Chat Q&A Pairs | Questions with expected answers grounded in review data | 50+ pairs |
| PRD Quality Ratings | PRDs rated by PMs for quality (calibration) | 20+ rated PRDs |

### Eval Harness Requirements

- **Deterministic LLM mode**: Temperature=0, seed-based for reproducibility
- **Baseline snapshots**: Store results in `baseline/` for regression detection
- **CI integration**: Run P0 evals on every PR; P1 weekly; P2 monthly
- **Cost tracking**: Log token usage per eval run to monitor costs
- **Human-in-the-loop**: Expert review queue for calibrating automated metrics
