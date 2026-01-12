# Phase 2: Make Context Graph a PM's Daily Driver

**Status:** Planning  
**Target Duration:** 4 weeks (Weeks 5-8)  
**Author:** Product Team  
**Last Updated:** January 2026

---

## Table of Contents

1. [Overview](#overview)
2. [Feature 2.1: Effort Estimation with Codebase Grounding](#feature-21-effort-estimation-with-codebase-grounding)
3. [Feature 2.2: Predicted Cross-Functional Feedback](#feature-22-predicted-cross-functional-feedback)
4. [Feature 2.3: PRD Quality Scoring](#feature-23-prd-quality-scoring)
5. [Data Models](#data-models)
6. [API Specifications](#api-specifications)
7. [UI/UX Specifications](#uiux-specifications)
8. [Implementation Plan](#implementation-plan)
9. [Testing Strategy](#testing-strategy)
10. [Success Metrics](#success-metrics)

---

## Overview

### Vision: Cursor for PMs

**What Cursor does for Engineers:**
- Shows errors inline as you code
- Predicts what you need to fix
- Grounds suggestions in actual code context
- Makes YOU a better engineer

**What Context Graph should do for PMs:**
- Shows stakeholder concerns inline as you write PRDs
- Predicts what cross-functional teams will push back on
- Grounds feedback in actual codebase state
- Makes YOU a better PM (not just a coordination tool)

### The Key Difference

| Aspect | Linear/Jira Approach | Cursor-for-PMs Approach |
|--------|---------------------|-------------------------|
| **Purpose** | Share findings with teams | Predict pushback, help PM strengthen PRD |
| **Timing** | After review, for collaboration | During PRD writing, for self-improvement |
| **Output** | "Here's a summary for Eng" | "Eng will ask X because `file.py:line` shows Y" |
| **Action** | PM sends to stakeholder | PM updates PRD to preemptively address |
| **Value** | Coordination | PM competence + faster reviews |

### Success Criteria

After Phase 2, a PM should be able to:

1. **Upload a PRD** and immediately see what's missing/unclear
2. **Get predicted questions** from Eng/Security/Privacy/Legal - grounded in actual code
3. **Fix their PRD** before stakeholder meetings
4. **Generate sprint-ready estimates** with confidence calibrated to codebase

---

## Feature 2.1: Effort Estimation with Codebase Grounding

### Problem Statement

Generic effort estimates like "High Complexity" don't help PMs plan. What PMs need:
- "This will take 3-5 days because `auth_service.py` already has 60% of the pattern"
- "This will take 8-12 days because no rate limiting exists - see gap in `api/` directory"

### Solution

Generate **Code-Grounded Effort Estimates** where every estimate references:
- What exists in the codebase (reduces effort)
- What's missing (increases effort + identifies risk)
- Similar implementations for calibration

---

### 2.1.1 Data Models

```python
# src/context_graph/core/models.py

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4


class EffortSize(Enum):
    """T-shirt sizing for effort estimation."""
    XS = "xs"      # < 1 day
    S = "small"    # 1-2 days
    M = "medium"   # 3-5 days
    L = "large"    # 1-2 weeks
    XL = "xl"      # 2-4 weeks
    XXL = "xxl"    # > 1 month


class TeamRole(Enum):
    """Roles that may be needed for implementation."""
    BACKEND = "backend"
    FRONTEND = "frontend"
    FULLSTACK = "fullstack"
    DEVOPS = "devops"
    SECURITY = "security"
    QA = "qa"
    DESIGN = "design"
    DATA = "data"
    MOBILE = "mobile"


class DependencyType(Enum):
    """Types of dependencies identified."""
    INFRASTRUCTURE = "infrastructure"
    EXTERNAL_SERVICE = "external_service"
    TEAM_DECISION = "team_decision"
    APPROVAL = "approval"
    DESIGN = "design"
    OTHER_FEATURE = "other_feature"


@dataclass
class CodeEvidence:
    """Evidence from codebase that affects estimation."""
    file_path: str = ""
    line_start: int = 0
    line_end: int = 0
    code_snippet: str = ""
    relevance: str = ""  # Why this code matters
    impact: str = ""     # "reduces_effort", "increases_effort", "reference"


@dataclass
class EffortEstimate:
    """Effort estimate for a single requirement."""
    id: UUID = field(default_factory=uuid4)
    requirement_id: str = ""
    requirement_text: str = ""
    
    # Effort sizing
    effort_size: EffortSize = EffortSize.M
    effort_days_min: float = 0.0
    effort_days_max: float = 0.0
    effort_days_likely: float = 0.0
    
    # Confidence with reasoning
    confidence: float = 0.5
    confidence_reasoning: str = ""
    
    # Code evidence (THE KEY DIFFERENTIATOR)
    supporting_code: list[CodeEvidence] = field(default_factory=list)
    missing_code: list[CodeEvidence] = field(default_factory=list)  # Patterns that DON'T exist
    similar_implementations: list[CodeEvidence] = field(default_factory=list)
    
    # Summary
    why_this_estimate: str = ""  # Plain English: "3-5 days because..."
    risks: list[str] = field(default_factory=list)


@dataclass
class TeamRequirement:
    """Team/role requirement for implementation."""
    role: TeamRole = TeamRole.BACKEND
    allocation_days: float = 0.0
    allocation_percentage: float = 100.0
    is_primary: bool = False
    skills_needed: list[str] = field(default_factory=list)
    code_evidence: list[CodeEvidence] = field(default_factory=list)
    notes: str = ""


@dataclass
class Dependency:
    """A dependency that must be resolved."""
    id: UUID = field(default_factory=uuid4)
    dependency_type: DependencyType = DependencyType.INFRASTRUCTURE
    title: str = ""
    description: str = ""
    code_evidence: list[CodeEvidence] = field(default_factory=list)
    owner_team: str = ""
    blocking: bool = True
    estimated_resolution_days: float = 0.0
    status: str = "pending"


@dataclass
class SprintRecommendation:
    """Recommended sprint breakdown."""
    sprint_number: int = 1
    sprint_name: str = ""
    deliverables: list[str] = field(default_factory=list)
    requirement_ids: list[str] = field(default_factory=list)
    effort_points: int = 0
    risk_level: str = "low"
    risk_explanation: str = ""
    dependencies_to_resolve: list[UUID] = field(default_factory=list)


@dataclass
class SprintPlanSummary:
    """Complete sprint planning summary."""
    id: UUID = field(default_factory=uuid4)
    review_id: UUID = field(default_factory=uuid4)
    
    # High-level summary
    total_effort_days_min: float = 0.0
    total_effort_days_max: float = 0.0
    total_effort_days_likely: float = 0.0
    recommended_sprint_count: int = 1
    overall_confidence: float = 0.5
    
    # Detailed breakdowns
    effort_estimates: list[EffortEstimate] = field(default_factory=list)
    team_requirements: list[TeamRequirement] = field(default_factory=list)
    dependencies: list[Dependency] = field(default_factory=list)
    sprint_recommendations: list[SprintRecommendation] = field(default_factory=list)
    
    # Codebase context
    codebase_readiness_score: float = 0.0
    existing_patterns_leveraged: list[CodeEvidence] = field(default_factory=list)
    new_patterns_required: list[str] = field(default_factory=list)
    
    # Executive summary
    tldr: str = ""  # "14-20 days, 3 sprints, 72% of patterns exist"
    
    generated_at: str = ""
```

---

### 2.1.2 Estimation Engine

```python
# src/context_graph/estimators/effort_estimator.py

"""
Code-Grounded Effort Estimation Engine

Every estimate is tied to actual codebase evidence.
"""

from dataclasses import dataclass
from typing import Optional
from context_graph.core.models import (
    Intent, State, EffortEstimate, SprintPlanSummary,
    TeamRequirement, Dependency, SprintRecommendation,
    EffortSize, TeamRole, DependencyType, CodeEvidence
)


class EffortEstimationEngine:
    """
    Generates sprint planning estimates grounded in codebase analysis.
    """
    
    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
    ):
        self.openai_api_key = openai_api_key
        self.anthropic_api_key = anthropic_api_key
    
    async def estimate(
        self,
        intent: Intent,
        state: State,
        codebase_index: dict,  # Full codebase index for evidence
        sprint_length_days: int = 10,
    ) -> SprintPlanSummary:
        """
        Generate code-grounded sprint planning summary.
        """
        summary = SprintPlanSummary()
        
        # Step 1: Extract requirements
        requirements = self._extract_requirements(intent)
        
        # Step 2: For each requirement, find code evidence
        for req in requirements:
            estimate = await self._estimate_with_evidence(
                req, state, codebase_index
            )
            summary.effort_estimates.append(estimate)
        
        # Step 3: Generate team requirements with evidence
        summary.team_requirements = self._identify_team_requirements(
            summary.effort_estimates, codebase_index
        )
        
        # Step 4: Identify dependencies with code evidence
        summary.dependencies = self._identify_dependencies(
            intent, state, codebase_index
        )
        
        # Step 5: Generate sprint breakdown
        summary.sprint_recommendations = self._generate_sprint_breakdown(
            summary.effort_estimates,
            summary.dependencies,
            sprint_length_days
        )
        
        # Step 6: Calculate totals and generate TLDR
        self._calculate_summary_totals(summary)
        summary.tldr = self._generate_tldr(summary)
        
        return summary
    
    async def _estimate_with_evidence(
        self,
        requirement: dict,
        state: State,
        codebase_index: dict,
    ) -> EffortEstimate:
        """
        Estimate a single requirement with code evidence.
        
        This is where the magic happens - every estimate has a "because".
        """
        estimate = EffortEstimate(
            requirement_id=requirement["id"],
            requirement_text=requirement["text"],
        )
        
        # Find supporting code (reduces effort)
        supporting = self._find_supporting_code(
            requirement["text"], codebase_index
        )
        estimate.supporting_code = supporting
        
        # Find similar implementations (calibrates estimate)
        similar = self._find_similar_implementations(
            requirement["text"], codebase_index
        )
        estimate.similar_implementations = similar
        
        # Find missing patterns (increases effort)
        missing = self._find_missing_patterns(
            requirement["text"], state, codebase_index
        )
        estimate.missing_code = missing
        
        # Calculate effort based on evidence
        base_days = self._get_base_days(requirement["type"])
        
        # Adjust based on evidence
        if len(supporting) >= 2:
            # Strong support - can extend existing patterns
            multiplier = 0.5
            confidence = 0.8
            estimate.why_this_estimate = (
                f"{base_days * multiplier:.0f}-{base_days * multiplier * 1.5:.0f} days because "
                f"existing code in {supporting[0].file_path} already implements "
                f"the core pattern. Just needs extension."
            )
        elif len(supporting) >= 1:
            # Partial support
            multiplier = 0.75
            confidence = 0.65
            estimate.why_this_estimate = (
                f"{base_days * multiplier:.0f}-{base_days * multiplier * 1.5:.0f} days because "
                f"related pattern exists in {supporting[0].file_path}, "
                f"but needs adaptation."
            )
        else:
            # No support - build from scratch
            multiplier = 1.0
            confidence = 0.5
            if missing:
                estimate.why_this_estimate = (
                    f"{base_days:.0f}-{base_days * 1.5:.0f} days because "
                    f"no existing pattern found. {missing[0].relevance}"
                )
            else:
                estimate.why_this_estimate = (
                    f"{base_days:.0f}-{base_days * 1.5:.0f} days - "
                    f"new implementation required."
                )
        
        # Use similar implementations to calibrate
        if similar:
            avg_lines = sum(
                e.line_end - e.line_start for e in similar
            ) / len(similar)
            estimate.confidence_reasoning = (
                f"Based on {len(similar)} similar implementations "
                f"averaging {avg_lines:.0f} lines each."
            )
        
        likely = base_days * multiplier
        estimate.effort_size = self._days_to_size(likely)
        estimate.effort_days_min = likely * 0.7
        estimate.effort_days_max = likely * 1.5
        estimate.effort_days_likely = likely
        estimate.confidence = confidence
        
        return estimate
    
    def _find_supporting_code(
        self,
        requirement_text: str,
        codebase_index: dict,
    ) -> list[CodeEvidence]:
        """
        Find code that supports implementing this requirement.
        """
        evidence = []
        req_lower = requirement_text.lower()
        
        # Search for matching patterns
        keywords = self._extract_keywords(req_lower)
        
        for file_path, file_data in codebase_index.items():
            for func in file_data.get("functions", []):
                func_name_lower = func["name"].lower()
                
                # Check if function relates to requirement
                for keyword in keywords:
                    if keyword in func_name_lower:
                        evidence.append(CodeEvidence(
                            file_path=file_path,
                            line_start=func["line_start"],
                            line_end=func["line_end"],
                            code_snippet=func.get("signature", ""),
                            relevance=f"Existing {func['name']} handles similar functionality",
                            impact="reduces_effort"
                        ))
                        break
        
        return evidence[:5]  # Top 5 most relevant
    
    def _find_similar_implementations(
        self,
        requirement_text: str,
        codebase_index: dict,
    ) -> list[CodeEvidence]:
        """
        Find similar implementations for calibration.
        """
        # This would use semantic search in production
        # Simplified version here
        evidence = []
        
        req_type = self._infer_requirement_type(requirement_text)
        
        for file_path, file_data in codebase_index.items():
            # Look for similar patterns based on requirement type
            if req_type == "api" and "route" in file_path.lower():
                for func in file_data.get("functions", []):
                    if any(method in func["name"].lower() 
                           for method in ["get", "post", "put", "delete"]):
                        evidence.append(CodeEvidence(
                            file_path=file_path,
                            line_start=func["line_start"],
                            line_end=func["line_end"],
                            code_snippet=func.get("signature", ""),
                            relevance=f"Similar API endpoint for reference",
                            impact="reference"
                        ))
        
        return evidence[:3]
    
    def _find_missing_patterns(
        self,
        requirement_text: str,
        state: State,
        codebase_index: dict,
    ) -> list[CodeEvidence]:
        """
        Identify patterns that DON'T exist but are needed.
        
        This is crucial for accurate estimation.
        """
        missing = []
        req_lower = requirement_text.lower()
        
        # Check for common patterns that might be missing
        patterns_to_check = [
            ("rate limit", "rate_limit", "No rate limiting infrastructure found"),
            ("mfa", "totp", "No MFA/TOTP implementation exists"),
            ("oauth", "oauth", "No OAuth integration exists"),
            ("cache", "cache", "No caching layer exists"),
            ("queue", "queue", "No message queue integration exists"),
            ("websocket", "socket", "No WebSocket infrastructure exists"),
        ]
        
        for req_pattern, code_pattern, message in patterns_to_check:
            if req_pattern in req_lower:
                # Check if pattern exists in codebase
                found = False
                for file_path, file_data in codebase_index.items():
                    if code_pattern in file_path.lower():
                        found = True
                        break
                    for func in file_data.get("functions", []):
                        if code_pattern in func["name"].lower():
                            found = True
                            break
                
                if not found:
                    missing.append(CodeEvidence(
                        file_path="",
                        line_start=0,
                        line_end=0,
                        code_snippet="",
                        relevance=message,
                        impact="increases_effort"
                    ))
        
        return missing
    
    def _extract_keywords(self, text: str) -> list[str]:
        """Extract relevant keywords from requirement text."""
        # Remove common words
        stopwords = {"a", "an", "the", "and", "or", "to", "for", "with", "in"}
        words = text.split()
        keywords = [w for w in words if w not in stopwords and len(w) > 3]
        return keywords[:10]
    
    def _infer_requirement_type(self, text: str) -> str:
        """Infer the type of requirement."""
        text_lower = text.lower()
        if any(w in text_lower for w in ["api", "endpoint", "route", "request"]):
            return "api"
        if any(w in text_lower for w in ["auth", "login", "password", "token"]):
            return "auth"
        if any(w in text_lower for w in ["database", "model", "schema", "table"]):
            return "data"
        return "feature"
    
    def _get_base_days(self, req_type: str) -> float:
        """Get base effort in days by requirement type."""
        base_days = {
            "functional": 3.0,
            "api": 2.0,
            "security": 4.0,
            "infrastructure": 5.0,
            "auth": 4.0,
            "data": 2.0,
        }
        return base_days.get(req_type, 3.0)
    
    def _days_to_size(self, days: float) -> EffortSize:
        """Convert days to T-shirt size."""
        if days < 1:
            return EffortSize.XS
        elif days < 3:
            return EffortSize.S
        elif days < 5:
            return EffortSize.M
        elif days < 10:
            return EffortSize.L
        elif days < 20:
            return EffortSize.XL
        else:
            return EffortSize.XXL
    
    def _generate_tldr(self, summary: SprintPlanSummary) -> str:
        """Generate executive TLDR."""
        blockers = len([d for d in summary.dependencies if d.blocking])
        support_pct = summary.codebase_readiness_score
        
        return (
            f"{summary.total_effort_days_likely:.0f} days "
            f"({summary.total_effort_days_min:.0f}-{summary.total_effort_days_max:.0f} range), "
            f"{summary.recommended_sprint_count} sprints, "
            f"{support_pct:.0f}% codebase support, "
            f"{blockers} blockers to resolve first"
        )
    
    # ... other helper methods same as before
```

---

## Feature 2.2: Predicted Cross-Functional Feedback

### Problem Statement (Reframed)

**Old thinking:** "Generate summaries to share with stakeholders"  
**New thinking:** "Predict what stakeholders will ask, grounded in code, so PM can fix PRD first"

The goal is NOT coordination. The goal is making PMs more competent by:
1. Anticipating cross-functional questions before meetings
2. Grounding those questions in actual codebase state
3. Providing suggested PRD additions to address concerns proactively

### Solution

Generate **Predicted Cross-Functional Feedback** that shows:
- What Engineering will ask (and why, based on code)
- What Security will flag (and what code supports the concern)
- What Privacy/Legal will question (grounded in data handling)
- Suggested PRD additions to preemptively address each concern

---

### 2.2.1 Data Models

```python
# src/context_graph/core/models.py (additions)

from enum import Enum
from dataclasses import dataclass, field
from uuid import UUID, uuid4


class CrossFunctionalTeam(Enum):
    """Teams that will review the PRD."""
    ENGINEERING = "engineering"
    SECURITY = "security"
    PRIVACY = "privacy"
    LEGAL = "legal"
    INFRA = "infrastructure"
    QA = "qa"
    DESIGN = "design"


class ConcernSeverity(Enum):
    """How likely this concern will block approval."""
    BLOCKER = "blocker"      # Will definitely come up, must address
    LIKELY = "likely"        # Very likely to come up
    POSSIBLE = "possible"    # Might come up depending on reviewer


@dataclass
class PredictedQuestion:
    """A question a team is likely to ask."""
    id: UUID = field(default_factory=uuid4)
    
    # The predicted question
    question: str = ""
    
    # Why they'll ask this (code-grounded)
    reasoning: str = ""
    code_evidence: list[CodeEvidence] = field(default_factory=list)
    
    # How to address it
    suggested_prd_addition: str = ""
    example_text: str = ""
    
    # Metadata
    severity: ConcernSeverity = ConcernSeverity.LIKELY
    prd_section_affected: str = ""  # Where to add the fix


@dataclass
class TeamFeedback:
    """Predicted feedback from a specific team."""
    team: CrossFunctionalTeam = CrossFunctionalTeam.ENGINEERING
    
    # Summary for this team
    tldr: str = ""  # "3 blockers, 2 likely questions"
    
    # Predicted questions
    predicted_questions: list[PredictedQuestion] = field(default_factory=list)
    
    # What they'll approve without question
    auto_approved: list[str] = field(default_factory=list)
    
    # Overall readiness for this team's review
    readiness_score: float = 0.0  # 0-100
    readiness_explanation: str = ""


@dataclass
class CrossFunctionalFeedback:
    """Complete predicted feedback from all teams."""
    id: UUID = field(default_factory=uuid4)
    review_id: UUID = field(default_factory=uuid4)
    
    # Per-team feedback
    team_feedback: dict[CrossFunctionalTeam, TeamFeedback] = field(default_factory=dict)
    
    # Aggregated view
    total_blockers: int = 0
    total_likely_questions: int = 0
    overall_readiness: float = 0.0
    
    # Priority order for fixing
    fix_priority: list[UUID] = field(default_factory=list)  # Question IDs in priority order
    
    # PRD improvement checklist
    prd_checklist: list[dict] = field(default_factory=list)
    
    generated_at: str = ""
```

---

### 2.2.2 Feedback Predictor

```python
# src/context_graph/feedback/cross_functional_predictor.py

"""
Cross-Functional Feedback Predictor

Predicts what each team will ask about a PRD, grounded in codebase analysis.
"""

from context_graph.core.models import (
    Intent, State, CrossFunctionalFeedback, TeamFeedback,
    PredictedQuestion, CrossFunctionalTeam, ConcernSeverity,
    CodeEvidence
)


class CrossFunctionalPredictor:
    """
    Predicts stakeholder feedback to help PMs improve their PRDs.
    
    This is NOT for sharing with stakeholders.
    This is for making PMs better at writing PRDs.
    """
    
    async def predict(
        self,
        intent: Intent,
        state: State,
        codebase_index: dict,
        raw_prd_text: str,
    ) -> CrossFunctionalFeedback:
        """
        Predict cross-functional feedback for a PRD.
        """
        feedback = CrossFunctionalFeedback()
        
        # Predict feedback from each team
        feedback.team_feedback[CrossFunctionalTeam.ENGINEERING] = \
            await self._predict_engineering_feedback(intent, state, codebase_index, raw_prd_text)
        
        feedback.team_feedback[CrossFunctionalTeam.SECURITY] = \
            await self._predict_security_feedback(intent, state, codebase_index, raw_prd_text)
        
        feedback.team_feedback[CrossFunctionalTeam.PRIVACY] = \
            await self._predict_privacy_feedback(intent, state, codebase_index, raw_prd_text)
        
        feedback.team_feedback[CrossFunctionalTeam.INFRA] = \
            await self._predict_infra_feedback(intent, state, codebase_index, raw_prd_text)
        
        # Aggregate
        feedback.total_blockers = sum(
            len([q for q in tf.predicted_questions if q.severity == ConcernSeverity.BLOCKER])
            for tf in feedback.team_feedback.values()
        )
        
        feedback.total_likely_questions = sum(
            len([q for q in tf.predicted_questions if q.severity == ConcernSeverity.LIKELY])
            for tf in feedback.team_feedback.values()
        )
        
        # Generate fix priority (blockers first)
        all_questions = []
        for tf in feedback.team_feedback.values():
            all_questions.extend(tf.predicted_questions)
        
        all_questions.sort(key=lambda q: (
            0 if q.severity == ConcernSeverity.BLOCKER else
            1 if q.severity == ConcernSeverity.LIKELY else 2
        ))
        
        feedback.fix_priority = [q.id for q in all_questions]
        
        # Generate PRD checklist
        feedback.prd_checklist = self._generate_checklist(all_questions)
        
        return feedback
    
    async def _predict_engineering_feedback(
        self,
        intent: Intent,
        state: State,
        codebase_index: dict,
        raw_prd_text: str,
    ) -> TeamFeedback:
        """
        Predict what Engineering will ask.
        
        Engineers care about:
        - How does this fit with existing architecture?
        - What's the migration story?
        - What about existing data/sessions/state?
        - Performance implications?
        - Testing approach?
        """
        feedback = TeamFeedback(team=CrossFunctionalTeam.ENGINEERING)
        questions = []
        
        # Check 1: Migration story
        if self._has_data_model_changes(intent):
            existing_models = self._find_existing_models(codebase_index)
            if existing_models:
                questions.append(PredictedQuestion(
                    question="What happens to existing data during migration?",
                    reasoning=f"PRD proposes changes that affect existing data models.",
                    code_evidence=existing_models[:2],
                    suggested_prd_addition="Add a 'Migration Strategy' section",
                    example_text="""### Migration Strategy
1. Existing users: [Will be migrated automatically / Will need to re-authenticate / etc.]
2. Data transformation: [Describe any data migration needed]
3. Rollback plan: [Feature flag / Blue-green / etc.]""",
                    severity=ConcernSeverity.BLOCKER,
                    prd_section_affected="Technical Considerations"
                ))
        
        # Check 2: Session handling
        session_code = self._find_session_handling(codebase_index)
        if session_code and "auth" in str(intent.features).lower():
            questions.append(PredictedQuestion(
                question="What happens to existing sessions when we deploy this?",
                reasoning=f"Current session handling in {session_code[0].file_path} stores sessions with specific schema.",
                code_evidence=session_code,
                suggested_prd_addition="Add session migration behavior to requirements",
                example_text="""### Session Handling
- Existing sessions: [Invalidate all / Grandfather existing / etc.]
- Session format changes: [None / Add new fields / etc.]""",
                severity=ConcernSeverity.LIKELY,
                prd_section_affected="Authentication Requirements"
            ))
        
        # Check 3: Missing infrastructure
        missing_infra = self._check_missing_infrastructure(intent, codebase_index)
        for infra_name, infra_evidence in missing_infra.items():
            questions.append(PredictedQuestion(
                question=f"Have you considered that {infra_name} doesn't exist yet?",
                reasoning=f"PRD assumes {infra_name} but no implementation found in codebase.",
                code_evidence=[],
                suggested_prd_addition=f"Add dependency on {infra_name} or remove assumption",
                example_text=f"""### Infrastructure Dependencies
- **{infra_name}**: [New infrastructure needed / Alternative approach / etc.]
- Timeline impact: [X days for setup]""",
                severity=ConcernSeverity.BLOCKER,
                prd_section_affected="Dependencies"
            ))
        
        # Check 4: Performance implications
        if self._has_performance_concerns(intent, codebase_index):
            perf_code = self._find_performance_critical_code(codebase_index)
            questions.append(PredictedQuestion(
                question="What are the performance targets for this feature?",
                reasoning="PRD doesn't specify latency/throughput requirements.",
                code_evidence=perf_code,
                suggested_prd_addition="Add non-functional requirements section",
                example_text="""### Performance Requirements
- Response time: p50 < Xms, p99 < Yms
- Throughput: X requests/second
- Concurrent users: X""",
                severity=ConcernSeverity.LIKELY,
                prd_section_affected="Non-Functional Requirements"
            ))
        
        # Check 5: Testing approach
        existing_tests = self._find_test_patterns(codebase_index)
        if existing_tests:
            questions.append(PredictedQuestion(
                question="What's the testing approach for this feature?",
                reasoning=f"Existing test patterns in {existing_tests[0].file_path} suggest unit + integration.",
                code_evidence=existing_tests,
                suggested_prd_addition="Add testing requirements or acceptance criteria format",
                example_text="""### Acceptance Criteria
Given [context], when [action], then [expected result]

### Testing Requirements
- Unit test coverage target: X%
- Integration tests required for: [list endpoints]""",
                severity=ConcernSeverity.POSSIBLE,
                prd_section_affected="Acceptance Criteria"
            ))
        
        feedback.predicted_questions = questions
        feedback.readiness_score = max(0, 100 - len(questions) * 20)
        feedback.tldr = f"{len([q for q in questions if q.severity == ConcernSeverity.BLOCKER])} blockers, {len(questions)} total questions"
        
        return feedback
    
    async def _predict_security_feedback(
        self,
        intent: Intent,
        state: State,
        codebase_index: dict,
        raw_prd_text: str,
    ) -> TeamFeedback:
        """
        Predict what Security will ask.
        
        Security cares about:
        - Authentication changes
        - Data exposure
        - Input validation
        - Audit logging
        - Rate limiting
        """
        feedback = TeamFeedback(team=CrossFunctionalTeam.SECURITY)
        questions = []
        
        # Check 1: Auth changes without threat model
        if intent.auth_requirements:
            existing_auth = self._find_auth_code(codebase_index)
            if "threat model" not in raw_prd_text.lower():
                questions.append(PredictedQuestion(
                    question="Where's the threat model for the auth changes?",
                    reasoning=f"PRD proposes auth changes but doesn't enumerate threats.",
                    code_evidence=existing_auth,
                    suggested_prd_addition="Add threat modeling section",
                    example_text="""### Threat Model
| Threat | Likelihood | Impact | Mitigation |
|--------|------------|--------|------------|
| Brute force attack | High | High | Rate limiting + account lockout |
| Session hijacking | Medium | High | Secure cookies + HTTPS only |
| Token theft | Medium | High | Short expiry + refresh rotation |""",
                    severity=ConcernSeverity.BLOCKER,
                    prd_section_affected="Security Considerations"
                ))
        
        # Check 2: Rate limiting
        rate_limit_code = self._find_rate_limiting(codebase_index)
        if not rate_limit_code and "auth" in str(intent.features).lower():
            questions.append(PredictedQuestion(
                question="How are you handling rate limiting for auth endpoints?",
                reasoning="No rate limiting found in codebase, and auth endpoints need protection.",
                code_evidence=[],
                suggested_prd_addition="Add rate limiting requirements",
                example_text="""### Rate Limiting
- Login endpoint: Max 5 attempts per 15 minutes per IP
- Password reset: Max 3 requests per hour per email
- Token refresh: Max 10 per minute per user""",
                severity=ConcernSeverity.BLOCKER,
                prd_section_affected="Security Considerations"
            ))
        
        # Check 3: Input validation
        if intent.api_changes:
            validation_code = self._find_input_validation(codebase_index)
            if not "validation" in raw_prd_text.lower() and not "sanitiz" in raw_prd_text.lower():
                questions.append(PredictedQuestion(
                    question="What input validation is required for the new endpoints?",
                    reasoning="PRD defines new API endpoints but doesn't specify validation rules.",
                    code_evidence=validation_code,
                    suggested_prd_addition="Add validation rules to API spec",
                    example_text="""### Input Validation
- email: Valid email format, max 254 chars
- password: Min 12 chars, complexity requirements
- username: Alphanumeric, 3-30 chars, no special chars""",
                    severity=ConcernSeverity.LIKELY,
                    prd_section_affected="API Specification"
                ))
        
        # Check 4: Audit logging
        audit_code = self._find_audit_logging(codebase_index)
        if intent.auth_requirements and "audit" not in raw_prd_text.lower():
            questions.append(PredictedQuestion(
                question="What events need to be audit logged?",
                reasoning="Auth changes require audit trail for compliance.",
                code_evidence=audit_code,
                suggested_prd_addition="Add audit logging requirements",
                example_text="""### Audit Logging
Events to log:
- Login success/failure (user_id, IP, timestamp, result)
- Password change (user_id, timestamp)
- MFA enable/disable (user_id, timestamp, method)
- Session invalidation (user_id, reason, timestamp)""",
                severity=ConcernSeverity.LIKELY,
                prd_section_affected="Security Considerations"
            ))
        
        feedback.predicted_questions = questions
        feedback.readiness_score = max(0, 100 - len(questions) * 25)
        feedback.tldr = f"{len([q for q in questions if q.severity == ConcernSeverity.BLOCKER])} blockers, {len(questions)} total questions"
        
        return feedback
    
    async def _predict_privacy_feedback(
        self,
        intent: Intent,
        state: State,
        codebase_index: dict,
        raw_prd_text: str,
    ) -> TeamFeedback:
        """
        Predict what Privacy/Legal will ask.
        
        Privacy cares about:
        - PII collection and storage
        - Data retention
        - Third-party data sharing
        - User consent
        - Right to deletion
        """
        feedback = TeamFeedback(team=CrossFunctionalTeam.PRIVACY)
        questions = []
        
        # Check 1: PII handling
        if intent.data_sensitivity:
            pii_code = self._find_pii_handling(codebase_index)
            questions.append(PredictedQuestion(
                question="What PII is being collected and where is it stored?",
                reasoning=f"PRD involves sensitive data: {', '.join(intent.data_sensitivity[:3])}",
                code_evidence=pii_code,
                suggested_prd_addition="Add data inventory table",
                example_text="""### Data Inventory
| Field | Type | Storage | Encryption | Retention |
|-------|------|---------|------------|-----------|
| email | PII | PostgreSQL | At rest | Until deletion |
| password | Sensitive | PostgreSQL | bcrypt hash | Until deletion |
| IP address | PII | Logs | No | 30 days |""",
                severity=ConcernSeverity.BLOCKER,
                prd_section_affected="Privacy Considerations"
            ))
        
        # Check 2: Third-party sharing
        if intent.external_integrations:
            questions.append(PredictedQuestion(
                question="What data is shared with third parties?",
                reasoning=f"PRD integrates with: {', '.join(intent.external_integrations)}",
                code_evidence=[],
                suggested_prd_addition="Add third-party data sharing matrix",
                example_text=f"""### Third-Party Data Sharing
| Service | Data Shared | Purpose | DPA Status |
|---------|-------------|---------|------------|
{chr(10).join(f'| {i} | [specify] | [purpose] | [status] |' for i in intent.external_integrations)}""",
                severity=ConcernSeverity.BLOCKER,
                prd_section_affected="Privacy Considerations"
            ))
        
        # Check 3: Data retention
        if "retention" not in raw_prd_text.lower() and intent.data_sensitivity:
            questions.append(PredictedQuestion(
                question="What's the data retention policy for this feature?",
                reasoning="PRD collects user data but doesn't specify retention.",
                code_evidence=[],
                suggested_prd_addition="Add retention policy",
                example_text="""### Data Retention
- Active user data: Retained while account is active
- Deleted account data: Purged within 30 days
- Logs: 90 days, then anonymized
- Audit trail: 7 years (compliance requirement)""",
                severity=ConcernSeverity.LIKELY,
                prd_section_affected="Privacy Considerations"
            ))
        
        # Check 4: Right to deletion
        if intent.data_sensitivity and "delet" not in raw_prd_text.lower():
            questions.append(PredictedQuestion(
                question="How does this feature support user data deletion requests?",
                reasoning="GDPR/CCPA require right to deletion for PII.",
                code_evidence=[],
                suggested_prd_addition="Add deletion behavior",
                example_text="""### User Data Deletion
When user requests account deletion:
1. [Field X]: Hard delete within Y days
2. [Field Y]: Anonymize, retain for analytics
3. [Audit logs]: Retain reference ID, purge PII""",
                severity=ConcernSeverity.LIKELY,
                prd_section_affected="Privacy Considerations"
            ))
        
        feedback.predicted_questions = questions
        feedback.readiness_score = max(0, 100 - len(questions) * 25)
        feedback.tldr = f"{len([q for q in questions if q.severity == ConcernSeverity.BLOCKER])} blockers, {len(questions)} total questions"
        
        return feedback
    
    async def _predict_infra_feedback(
        self,
        intent: Intent,
        state: State,
        codebase_index: dict,
        raw_prd_text: str,
    ) -> TeamFeedback:
        """
        Predict what Infrastructure/DevOps will ask.
        """
        feedback = TeamFeedback(team=CrossFunctionalTeam.INFRA)
        questions = []
        
        # Check for new infrastructure needs
        infra_needs = self._identify_infrastructure_needs(intent, codebase_index)
        
        for need in infra_needs:
            questions.append(PredictedQuestion(
                question=f"Who's provisioning {need['name']}?",
                reasoning=need["reasoning"],
                code_evidence=[],
                suggested_prd_addition=f"Add {need['name']} to infrastructure dependencies",
                example_text=f"""### Infrastructure Requirements
- **{need['name']}**: {need['description']}
  - Owner: [Infra team / Self-provisioned]
  - Timeline: [X days before feature work]
  - Cost: [Estimate if known]""",
                severity=ConcernSeverity.BLOCKER,
                prd_section_affected="Infrastructure Requirements"
            ))
        
        feedback.predicted_questions = questions
        feedback.readiness_score = max(0, 100 - len(questions) * 30)
        feedback.tldr = f"{len(questions)} infrastructure decisions needed"
        
        return feedback
    
    def _generate_checklist(
        self,
        questions: list[PredictedQuestion]
    ) -> list[dict]:
        """Generate actionable PRD improvement checklist."""
        checklist = []
        
        for q in questions:
            checklist.append({
                "action": q.suggested_prd_addition,
                "section": q.prd_section_affected,
                "severity": q.severity.value,
                "team_asking": str(q),
                "example": q.example_text,
            })
        
        return checklist
    
    # Helper methods for finding code evidence
    def _has_data_model_changes(self, intent: Intent) -> bool:
        return bool(intent.data_entities)
    
    def _find_existing_models(self, codebase_index: dict) -> list[CodeEvidence]:
        evidence = []
        for file_path, file_data in codebase_index.items():
            if "model" in file_path.lower() or "schema" in file_path.lower():
                for cls in file_data.get("classes", []):
                    evidence.append(CodeEvidence(
                        file_path=file_path,
                        line_start=cls.get("line_start", 0),
                        line_end=cls.get("line_end", 0),
                        code_snippet=cls.get("name", ""),
                        relevance=f"Existing data model: {cls.get('name', '')}",
                        impact="reference"
                    ))
        return evidence[:3]
    
    def _find_session_handling(self, codebase_index: dict) -> list[CodeEvidence]:
        evidence = []
        for file_path, file_data in codebase_index.items():
            if "session" in file_path.lower():
                evidence.append(CodeEvidence(
                    file_path=file_path,
                    line_start=1,
                    line_end=50,
                    code_snippet="Session handling module",
                    relevance="Current session implementation",
                    impact="reference"
                ))
        return evidence
    
    def _check_missing_infrastructure(
        self,
        intent: Intent,
        codebase_index: dict
    ) -> dict[str, list[CodeEvidence]]:
        missing = {}
        
        infra_checks = [
            ("rate limiting", ["rate_limit", "throttle", "ratelimit"]),
            ("caching", ["redis", "cache", "memcache"]),
            ("queue", ["celery", "rabbitmq", "sqs", "queue"]),
            ("search", ["elasticsearch", "opensearch", "algolia"]),
        ]
        
        prd_text = str(intent.features).lower()
        
        for infra_name, patterns in infra_checks:
            if any(p in prd_text for p in patterns):
                found = False
                for file_path in codebase_index.keys():
                    if any(p in file_path.lower() for p in patterns):
                        found = True
                        break
                if not found:
                    missing[infra_name] = []
        
        return missing
    
    def _has_performance_concerns(
        self,
        intent: Intent,
        codebase_index: dict
    ) -> bool:
        # Check if PRD implies high-traffic features
        high_traffic_keywords = ["login", "search", "list", "feed", "stream"]
        return any(k in str(intent.features).lower() for k in high_traffic_keywords)
    
    def _find_performance_critical_code(self, codebase_index: dict) -> list[CodeEvidence]:
        # Find performance-sensitive patterns
        return []
    
    def _find_test_patterns(self, codebase_index: dict) -> list[CodeEvidence]:
        evidence = []
        for file_path in codebase_index.keys():
            if "test" in file_path.lower():
                evidence.append(CodeEvidence(
                    file_path=file_path,
                    line_start=1,
                    line_end=20,
                    code_snippet="Test file",
                    relevance="Existing test patterns",
                    impact="reference"
                ))
                break
        return evidence
    
    def _find_auth_code(self, codebase_index: dict) -> list[CodeEvidence]:
        evidence = []
        for file_path, file_data in codebase_index.items():
            if any(p in file_path.lower() for p in ["auth", "login", "session"]):
                evidence.append(CodeEvidence(
                    file_path=file_path,
                    line_start=1,
                    line_end=50,
                    code_snippet="Auth module",
                    relevance="Current auth implementation",
                    impact="reference"
                ))
        return evidence[:2]
    
    def _find_rate_limiting(self, codebase_index: dict) -> list[CodeEvidence]:
        for file_path in codebase_index.keys():
            if "rate" in file_path.lower() or "throttle" in file_path.lower():
                return [CodeEvidence(
                    file_path=file_path,
                    line_start=1,
                    line_end=20,
                    code_snippet="Rate limiting",
                    relevance="Existing rate limiter",
                    impact="reference"
                )]
        return []
    
    def _find_input_validation(self, codebase_index: dict) -> list[CodeEvidence]:
        return []
    
    def _find_audit_logging(self, codebase_index: dict) -> list[CodeEvidence]:
        return []
    
    def _find_pii_handling(self, codebase_index: dict) -> list[CodeEvidence]:
        return []
    
    def _identify_infrastructure_needs(
        self,
        intent: Intent,
        codebase_index: dict
    ) -> list[dict]:
        needs = []
        prd_text = str(intent.features).lower()
        
        if "redis" in prd_text or "cache" in prd_text:
            if not any("redis" in f.lower() for f in codebase_index.keys()):
                needs.append({
                    "name": "Redis",
                    "description": "For session storage / caching",
                    "reasoning": "PRD mentions caching but no Redis config found"
                })
        
        if "queue" in prd_text or "async" in prd_text or "background" in prd_text:
            if not any("celery" in f.lower() or "queue" in f.lower() for f in codebase_index.keys()):
                needs.append({
                    "name": "Message Queue",
                    "description": "For background job processing",
                    "reasoning": "PRD implies async processing but no queue found"
                })
        
        return needs
```

---

### 2.2.3 API Endpoints

```python
# src/context_graph/api/feedback_routes.py

from fastapi import APIRouter, HTTPException
from uuid import UUID
from context_graph.core.models import CrossFunctionalTeam

router = APIRouter(prefix="/api/feedback", tags=["cross_functional_feedback"])


@router.get("/reviews/{review_id}/predicted")
async def get_predicted_feedback(review_id: UUID):
    """
    Get predicted cross-functional feedback for a PRD.
    
    Returns predicted questions from Eng, Security, Privacy, Infra
    with code-grounded reasoning and suggested PRD improvements.
    """
    pass


@router.get("/reviews/{review_id}/predicted/{team}")
async def get_team_feedback(review_id: UUID, team: str):
    """
    Get predicted feedback for a specific team.
    
    Teams: engineering, security, privacy, legal, infrastructure, qa
    """
    try:
        team_enum = CrossFunctionalTeam(team)
    except ValueError:
        raise HTTPException(400, f"Invalid team: {team}")
    pass


@router.get("/reviews/{review_id}/checklist")
async def get_prd_improvement_checklist(review_id: UUID):
    """
    Get actionable checklist for improving the PRD.
    
    Returns prioritized list of suggested additions with examples.
    """
    pass


@router.post("/reviews/{review_id}/feedback/{question_id}/addressed")
async def mark_feedback_addressed(review_id: UUID, question_id: UUID):
    """
    Mark a predicted question as addressed in the PRD.
    
    Useful for tracking progress on PRD improvements.
    """
    pass
```

---

## Feature 2.3: PRD Quality Scoring

### Problem Statement

Same as before - but now framed as "catching issues before cross-functional teams do."

### Solution

PRD Quality Scoring that:
1. Evaluates completeness across dimensions
2. Maps low scores to predicted stakeholder pushback
3. Provides concrete examples from high-quality PRDs

---

### 2.3.1 Data Models

```python
# Same as before - PRDQualityDimension, PRDQualityScore
# But with added connection to predicted feedback

@dataclass
class PRDQualityScore:
    """Complete PRD quality assessment."""
    id: UUID = field(default_factory=uuid4)
    review_id: UUID = field(default_factory=uuid4)
    
    # Overall score
    overall_score: float = 0.0
    grade: str = ""
    
    # Dimension scores
    dimensions: list[PRDQualityDimension] = field(default_factory=list)
    
    # Strengths
    strengths: list[str] = field(default_factory=list)
    
    # Gaps with team impact
    gaps: list[dict] = field(default_factory=list)  # {gap, teams_affected, severity}
    
    # Suggestions with examples
    suggestions: list[dict] = field(default_factory=list)
    
    # Connection to predicted feedback
    predicted_blockers_from_gaps: int = 0
    gap_to_feedback_map: dict = field(default_factory=dict)  # gap -> predicted questions
```

---

## UI/UX Specifications

### 2.4.1 Predicted Feedback View (Main Feature)

**Route:** `/review/{id}/feedback`

This is the core Cursor-for-PMs feature.

```
+-------------------------------------------------------------------------+
|  Predicted Cross-Functional Feedback                                     |
|                                                                          |
|  4 Blockers | 7 Likely Questions | 56% Ready for Review                 |
+-------------------------------------------------------------------------+
|                                                                          |
|  [Engineering] [Security] [Privacy] [Infrastructure]                     |
|       3            2          2           1                              |
|                                                                          |
+-------------------------------------------------------------------------+
|                                                                          |
|  ENGINEERING WILL ASK:                                     56% Ready     |
|                                                                          |
|  +-------------------------------------------------------------------+  |
|  | [BLOCKER] "What happens to existing sessions when we deploy?"     |  |
|  |                                                                    |  |
|  | Because: session_manager.py:78-92 stores sessions with user_id    |  |
|  | as key. Your PRD doesn't specify migration behavior.              |  |
|  |                                                                    |  |
|  | > session_store = {                                               |  |
|  | >     "user_id": str,                                             |  |
|  | >     "created_at": datetime,                                     |  |
|  | >     ...                                                         |  |
|  | > }                                                               |  |
|  |                                                                    |  |
|  | SUGGESTED PRD ADDITION:                                           |  |
|  | +--------------------------------------------------------------+  |  |
|  | | ### Session Handling                                         |  |  |
|  | | - Existing sessions: Invalidate all on deploy                |  |  |
|  | | - Users will need to re-login after migration                |  |  |
|  | | - No data loss expected                                      |  |  |
|  | +--------------------------------------------------------------+  |  |
|  |                                                                    |  |
|  | [Copy to Clipboard]                      [Mark as Addressed]      |  |
|  +-------------------------------------------------------------------+  |
|                                                                          |
|  +-------------------------------------------------------------------+  |
|  | [BLOCKER] "Rate limiting doesn't exist - who's building it?"      |  |
|  |                                                                    |  |
|  | Because: Searched codebase for rate_limit*, throttle*, limiter*   |  |
|  | No matches found. Your auth endpoints need protection.            |  |
|  |                                                                    |  |
|  | SUGGESTED PRD ADDITION:                                           |  |
|  | +--------------------------------------------------------------+  |  |
|  | | ### Rate Limiting (New Infrastructure)                       |  |  |
|  | | - Login: 5 attempts per 15 minutes per IP                    |  |  |
|  | | - Owner: DevOps team                                         |  |  |
|  | | - Timeline: Must complete before Sprint 2                    |  |  |
|  | +--------------------------------------------------------------+  |  |
|  |                                                                    |  |
|  | [Copy to Clipboard]                      [Mark as Addressed]      |  |
|  +-------------------------------------------------------------------+  |
|                                                                          |
|  +-------------------------------------------------------------------+  |
|  | [LIKELY] "What are the performance targets?"                      |  |
|  |                                                                    |  |
|  | Because: auth_controller.py handles 10k+ requests/day based on    |  |
|  | current logging. New endpoints need similar capacity planning.    |  |
|  |                                                                    |  |
|  | SUGGESTED PRD ADDITION:                                           |  |
|  | +--------------------------------------------------------------+  |  |
|  | | ### Performance Requirements                                 |  |  |
|  | | - Login: p50 < 100ms, p99 < 500ms                            |  |  |
|  | | - Concurrent users: 1000                                     |  |  |
|  | +--------------------------------------------------------------+  |  |
|  |                                                                    |  |
|  | [Copy to Clipboard]                      [Mark as Addressed]      |  |
|  +-------------------------------------------------------------------+  |
|                                                                          |
+-------------------------------------------------------------------------+
|                                                                          |
|  SECURITY WILL ASK:                                        40% Ready     |
|                                                                          |
|  +-------------------------------------------------------------------+  |
|  | [BLOCKER] "Where's the threat model for auth changes?"            |  |
|  | ...                                                               |  |
|  +-------------------------------------------------------------------+  |
|                                                                          |
+-------------------------------------------------------------------------+
|                                                                          |
|  [Export PRD Improvement Checklist]    [Re-analyze Updated PRD]          |
|                                                                          |
+-------------------------------------------------------------------------+
```

---

### 2.4.2 PRD Quality Score (Before Analysis)

Same as before but now connected to predicted feedback.

```
+-------------------------------------------------------------------------+
|  PRD Quality Check                                                       |
+-------------------------------------------------------------------------+
|                                                                          |
|  Overall Score: 62/100 [C]                                              |
|                                                                          |
|  WARNING: This PRD will likely face pushback in stakeholder reviews     |
|                                                                          |
|  Predicted Impact:                                                       |
|  - 4 blocking questions from Engineering                                 |
|  - 2 blocking questions from Security                                   |
|  - 2 likely questions from Privacy                                      |
|                                                                          |
|  [Fix Issues Now]              [Proceed & See Detailed Feedback]        |
|                                                                          |
+-------------------------------------------------------------------------+
```

---

### 2.4.3 Sprint Planning View

Same as before but now shows code evidence.

```
+-------------------------------------------------------------------------+
|  Sprint Planning (Code-Grounded Estimates)                              |
+-------------------------------------------------------------------------+
|                                                                          |
|  Requirement: "Implement OAuth 2.0 integration"                         |
|                                                                          |
|  Estimate: 4-6 days (M)                                                 |
|  Confidence: 65%                                                        |
|                                                                          |
|  WHY THIS ESTIMATE:                                                     |
|  "4-6 days because no OAuth implementation exists in codebase.          |
|  Similar complexity to the GitHub webhook integration in                 |
|  integrations/github.py which took ~5 days (based on git history)."     |
|                                                                          |
|  Supporting Code:                                                        |
|  > integrations/github.py:45-120  (similar integration pattern)         |
|                                                                          |
|  Missing (increases effort):                                             |
|  - No OAuth library configured                                          |
|  - No token storage pattern exists                                      |
|                                                                          |
+-------------------------------------------------------------------------+
```

---

## Implementation Plan

### Week 5: Core Prediction Engine

| Day | Task | Owner |
|-----|------|-------|
| 1-2 | Implement CodeEvidence model and extraction | Backend |
| 2-3 | Build CrossFunctionalPredictor base | Backend |
| 3-4 | Implement Engineering feedback prediction | Backend |
| 4-5 | Implement Security feedback prediction | Backend |
| 5 | Unit tests for prediction engine | Backend |

**Deliverable:** Backend can predict Engineering + Security questions

---

### Week 6: Complete Prediction + UI

| Day | Task | Owner |
|-----|------|-------|
| 1-2 | Implement Privacy + Infra feedback prediction | Backend |
| 2-3 | API endpoints for predicted feedback | Backend |
| 3-4 | Frontend: Predicted Feedback view | Frontend |
| 4-5 | Frontend: Feedback cards with code evidence | Frontend |
| 5 | Integration testing | QA |

**Deliverable:** Full predicted feedback UI working

---

### Week 7: Effort Estimation + Quality

| Day | Task | Owner |
|-----|------|-------|
| 1-2 | Implement code-grounded effort estimator | Backend |
| 2-3 | PRD quality scoring with feedback connection | Backend |
| 3-4 | Frontend: Sprint planning with code evidence | Frontend |
| 4-5 | Frontend: Quality score with predicted impact | Frontend |
| 5 | Integration testing | QA |

**Deliverable:** Effort estimation and quality scoring live

---

### Week 8: Polish + Export

| Day | Task | Owner |
|-----|------|-------|
| 1-2 | Export functionality (Markdown checklist) | Backend |
| 2-3 | "Copy suggested addition" functionality | Frontend |
| 3-4 | End-to-end testing | QA |
| 4-5 | Bug fixes and polish | Team |

**Deliverable:** Complete Phase 2

---

## Success Metrics

### Quantitative

| Metric | Target | Measurement |
|--------|--------|-------------|
| Blocker questions predicted correctly | > 70% | Compare predictions to actual stakeholder questions |
| PRD revisions after using tool | > 50% of users update PRD | Track "Mark as Addressed" + PRD re-upload |
| Time from PRD to stakeholder approval | -30% | Compare before/after tool adoption |
| Stakeholder meeting iterations | -40% | Track rounds of feedback before approval |

### Qualitative

- PM feedback: "I knew what Security would ask before the meeting"
- PM feedback: "I fixed 3 issues before anyone else saw the PRD"
- Engineering feedback: "PRDs are coming in more complete"

---

## The Key Difference from Linear/Jira

| Aspect | This Tool (Cursor-for-PMs) | Linear/Jira |
|--------|---------------------------|-------------|
| **Core value** | Make PM smarter | Coordinate team |
| **When used** | Before stakeholder reviews | After decisions made |
| **Output** | "Fix this in your PRD" | "Assign this ticket" |
| **Feedback** | Predicted from codebase | Manual from humans |
| **Learning** | PM learns what to include | PM learns to use tool |

---

## Appendix: File Changes Summary

### New Files

| File | Purpose |
|------|---------|
| `src/context_graph/feedback/cross_functional_predictor.py` | Predicts stakeholder questions |
| `src/context_graph/estimators/effort_estimator.py` | Code-grounded effort estimation |
| `src/context_graph/analyzers/prd_quality_analyzer.py` | PRD quality scoring |
| `src/context_graph/api/feedback_routes.py` | Feedback API endpoints |
| `frontend/src/pages/PredictedFeedback.tsx` | Main feedback view |
| `frontend/src/components/FeedbackCard.tsx` | Predicted question card |
| `frontend/src/components/CodeEvidence.tsx` | Code snippet display |

---

## Questions for Review

1. Should we show confidence scores on predicted questions?
2. How do we handle cases where codebase is too small for good predictions?
3. Should "Mark as Addressed" require PRD re-upload to verify?
4. Do we need a "I disagree with this prediction" feedback mechanism?

---

*End of Phase 2 Implementation Plan - Cursor for PMs Edition*
