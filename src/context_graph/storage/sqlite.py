"""
SQLite storage implementations for persistent review and collaboration data.

Uses aiosqlite for async SQLite operations, providing a lightweight
persistent storage option suitable for development, testing, and
single-instance deployments.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import aiosqlite

from context_graph.storage.base import ReviewStorage, CollaborationStorage
from context_graph.security.review_engine import ReviewResult
from context_graph.core.models import (
    Intent,
    State,
    Entity,
    Relationship,
    ReviewDimension,
    Severity,
    ThreatCategory,
    PrivacyCategory,
    ComplianceCategory,
    EngineeringCategory,
    ArchitectureCategory,
    ComplianceFramework,
    SecurityFinding,
    PrivacyFinding,
    ComplianceFinding,
    EngineeringFinding,
    ArchitectureFinding,
    PredictedQuestion,
    PRDQualityScore,
    EffortEstimation,
    CodeEvidence,
    PRDChange,
    DiffHunk,
)

logger = logging.getLogger(__name__)


# ==================== JSON Serialization Helpers ====================

def _uuid_to_str(obj: Any) -> Any:
    """Convert UUIDs to strings for JSON serialization."""
    if isinstance(obj, UUID):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, (Severity, ThreatCategory, PrivacyCategory, ComplianceCategory,
                          EngineeringCategory, ArchitectureCategory, ComplianceFramework,
                          ReviewDimension)):
        return obj.value
    elif hasattr(obj, '__dataclass_fields__'):
        return {k: _uuid_to_str(v) for k, v in obj.__dict__.items()}
    elif isinstance(obj, list):
        return [_uuid_to_str(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: _uuid_to_str(v) for k, v in obj.items()}
    return obj


def _safe_uuid_parse(uuid_str: str | None) -> UUID:
    """
    Safely parse a UUID string, returning a new UUID if the string is invalid or empty.
    
    Args:
        uuid_str: UUID string to parse, or None/empty string
        
    Returns:
        UUID object, either parsed from string or newly generated
    """
    if not uuid_str or not isinstance(uuid_str, str) or not uuid_str.strip():
        return uuid4()
    
    try:
        return UUID(uuid_str)
    except (ValueError, TypeError, AttributeError):
        # If UUID parsing fails, generate a new one
        return uuid4()


def _serialize_intent(intent: Intent) -> str:
    """Serialize Intent to JSON."""
    data = {
        "id": str(intent.id),
        "title": intent.title,
        "summary": intent.summary,
        "features": intent.features,
        "user_stories": intent.user_stories,
        "data_entities": [_uuid_to_str(e.__dict__) for e in intent.data_entities],
        "api_changes": intent.api_changes,
        "auth_requirements": intent.auth_requirements,
        "data_sensitivity": intent.data_sensitivity,
        "external_integrations": intent.external_integrations,
        "source_document": intent.source_document,
        "parsed_at": intent.parsed_at.isoformat(),
        "raw_content": intent.raw_content,
    }
    return json.dumps(data)


def _deserialize_intent(json_str: str) -> Intent:
    """Deserialize Intent from JSON."""
    data = json.loads(json_str)
    entities = []
    for e_data in data.get("data_entities", []):
        entity = Entity(
            id=_safe_uuid_parse(e_data.get("id")),
            name=e_data.get("name", ""),
            entity_type=e_data.get("entity_type", "data"),
            description=e_data.get("description", ""),
            properties=e_data.get("properties", {}),
            source=e_data.get("source", ""),
            is_sensitive=e_data.get("is_sensitive", False),
            requires_auth=e_data.get("requires_auth", False),
            trust_level=e_data.get("trust_level", 0),
        )
        entities.append(entity)
    
    return Intent(
        id=_safe_uuid_parse(data.get("id")),
        title=data.get("title", ""),
        summary=data.get("summary", ""),
        features=data.get("features", []),
        user_stories=data.get("user_stories", []),
        data_entities=entities,
        api_changes=data.get("api_changes", []),
        auth_requirements=data.get("auth_requirements", []),
        data_sensitivity=data.get("data_sensitivity", []),
        external_integrations=data.get("external_integrations", []),
        source_document=data.get("source_document", ""),
        parsed_at=datetime.fromisoformat(data["parsed_at"]) if data.get("parsed_at") else datetime.now(),
        raw_content=data.get("raw_content", ""),
    )


def _serialize_state(state: State) -> str:
    """Serialize State to JSON."""
    data = {
        "id": str(state.id),
        "codebase_path": state.codebase_path,
        "analyzed_at": state.analyzed_at.isoformat(),
        "entities": [_uuid_to_str(e.__dict__) for e in state.entities],
        "relationships": [_uuid_to_str(r.__dict__) for r in state.relationships],
        "api_endpoints": state.api_endpoints,
        "data_models": state.data_models,
        "auth_patterns": state.auth_patterns,
        "existing_controls": state.existing_controls,
        "trust_boundaries": state.trust_boundaries,
        "files_analyzed": state.files_analyzed,
        "lines_of_code": state.lines_of_code,
    }
    return json.dumps(data)


def _deserialize_state(json_str: str) -> State:
    """Deserialize State from JSON."""
    data = json.loads(json_str)
    
    entities = []
    for e_data in data.get("entities", []):
        from context_graph.core.models import EntityType
        entity = Entity(
            id=_safe_uuid_parse(e_data.get("id")),
            name=e_data.get("name", ""),
            entity_type=EntityType(e_data["entity_type"]) if e_data.get("entity_type") else EntityType.DATA,
            description=e_data.get("description", ""),
            properties=e_data.get("properties", {}),
            source=e_data.get("source", ""),
            is_sensitive=e_data.get("is_sensitive", False),
            requires_auth=e_data.get("requires_auth", False),
            trust_level=e_data.get("trust_level", 0),
        )
        entities.append(entity)
    
    relationships = []
    for r_data in data.get("relationships", []):
        from context_graph.core.models import RelationshipType
        rel = Relationship(
            id=_safe_uuid_parse(r_data.get("id")),
            source_id=_safe_uuid_parse(r_data.get("source_id")),
            target_id=_safe_uuid_parse(r_data.get("target_id")),
            relationship_type=RelationshipType(r_data["relationship_type"]) if r_data.get("relationship_type") else RelationshipType.FLOWS_TO,
            properties=r_data.get("properties", {}),
            crosses_trust_boundary=r_data.get("crosses_trust_boundary", False),
            requires_encryption=r_data.get("requires_encryption", False),
        )
        relationships.append(rel)
    
    return State(
        id=_safe_uuid_parse(data.get("id")),
        codebase_path=data.get("codebase_path", ""),
        analyzed_at=datetime.fromisoformat(data["analyzed_at"]) if data.get("analyzed_at") else datetime.now(),
        entities=entities,
        relationships=relationships,
        api_endpoints=data.get("api_endpoints", []),
        data_models=data.get("data_models", []),
        auth_patterns=data.get("auth_patterns", []),
        existing_controls=data.get("existing_controls", []),
        trust_boundaries=data.get("trust_boundaries", []),
        files_analyzed=data.get("files_analyzed", 0),
        lines_of_code=data.get("lines_of_code", 0),
    )


def _serialize_findings(findings: list[Any], finding_type: str) -> str:
    """Serialize findings to JSON."""
    return json.dumps([_uuid_to_str(f.__dict__) for f in findings])


def _deserialize_security_findings(json_str: str) -> list[SecurityFinding]:
    """Deserialize security findings from JSON."""
    data = json.loads(json_str)
    findings = []
    for f_data in data:
        finding = SecurityFinding(
            id=_safe_uuid_parse(f_data.get("id")),
            title=f_data.get("title", ""),
            description=f_data.get("description", ""),
            severity=Severity(f_data["severity"]) if f_data.get("severity") else Severity.MEDIUM,
            category=ThreatCategory(f_data["category"]) if f_data.get("category") else ThreatCategory.INFO_DISCLOSURE,
            dimension=ReviewDimension(f_data["dimension"]) if f_data.get("dimension") else ReviewDimension.SECURITY,
            affected_entities=[_safe_uuid_parse(e) for e in f_data.get("affected_entities", [])],
            affected_relationships=[_safe_uuid_parse(r) for r in f_data.get("affected_relationships", [])],
            source_type=f_data.get("source_type", ""),
            source_reference=f_data.get("source_reference", ""),
            recommendation=f_data.get("recommendation", ""),
            mitigations=f_data.get("mitigations", []),
            confidence=f_data.get("confidence", 0.0),
            found_at=datetime.fromisoformat(f_data["found_at"]) if f_data.get("found_at") else datetime.now(),
            validation_status=f_data.get("validation_status", "pending"),
            validated_by=f_data.get("validated_by"),
            validated_at=datetime.fromisoformat(f_data["validated_at"]) if f_data.get("validated_at") else None,
            validation_notes=f_data.get("validation_notes"),
            assigned_team=f_data.get("assigned_team"),
            assigned_user=f_data.get("assigned_user"),
            comment_count=f_data.get("comment_count", 0),
        )
        findings.append(finding)
    return findings


def _deserialize_privacy_findings(json_str: str) -> list[PrivacyFinding]:
    """Deserialize privacy findings from JSON."""
    data = json.loads(json_str)
    findings = []
    for f_data in data:
        finding = PrivacyFinding(
            id=_safe_uuid_parse(f_data.get("id")),
            title=f_data.get("title", ""),
            description=f_data.get("description", ""),
            severity=Severity(f_data["severity"]) if f_data.get("severity") else Severity.MEDIUM,
            category=PrivacyCategory(f_data["category"]) if f_data.get("category") else PrivacyCategory.DATA_DISCLOSURE,
            dimension=ReviewDimension.PRIVACY,
            data_subjects=f_data.get("data_subjects", []),
            personal_data_types=f_data.get("personal_data_types", []),
            processing_activities=f_data.get("processing_activities", []),
            affected_entities=[_safe_uuid_parse(e) for e in f_data.get("affected_entities", [])],
            affected_relationships=[_safe_uuid_parse(r) for r in f_data.get("affected_relationships", [])],
            source_type=f_data.get("source_type", ""),
            source_reference=f_data.get("source_reference", ""),
            applicable_regulations=f_data.get("applicable_regulations", []),
            legal_basis_required=f_data.get("legal_basis_required", False),
            consent_required=f_data.get("consent_required", False),
            recommendation=f_data.get("recommendation", ""),
            mitigations=f_data.get("mitigations", []),
            confidence=f_data.get("confidence", 0.0),
            found_at=datetime.fromisoformat(f_data["found_at"]) if f_data.get("found_at") else datetime.now(),
        )
        findings.append(finding)
    return findings


def _deserialize_compliance_findings(json_str: str) -> list[ComplianceFinding]:
    """Deserialize compliance findings from JSON."""
    data = json.loads(json_str)
    findings = []
    for f_data in data:
        finding = ComplianceFinding(
            id=_safe_uuid_parse(f_data.get("id")),
            title=f_data.get("title", ""),
            description=f_data.get("description", ""),
            severity=Severity(f_data["severity"]) if f_data.get("severity") else Severity.MEDIUM,
            category=ComplianceCategory(f_data["category"]) if f_data.get("category") else ComplianceCategory.REGULATORY_VIOLATION,
            dimension=ReviewDimension.COMPLIANCE,
            framework=ComplianceFramework(f_data["framework"]) if f_data.get("framework") else ComplianceFramework.SOC2,
            control_id=f_data.get("control_id", ""),
            control_description=f_data.get("control_description", ""),
            requirement_text=f_data.get("requirement_text", ""),
            affected_entities=[_safe_uuid_parse(e) for e in f_data.get("affected_entities", [])],
            affected_relationships=[_safe_uuid_parse(r) for r in f_data.get("affected_relationships", [])],
            source_type=f_data.get("source_type", ""),
            source_reference=f_data.get("source_reference", ""),
            current_state=f_data.get("current_state", ""),
            required_state=f_data.get("required_state", ""),
            gap_description=f_data.get("gap_description", ""),
            recommendation=f_data.get("recommendation", ""),
            mitigations=f_data.get("mitigations", []),
            remediation_effort=f_data.get("remediation_effort", ""),
            confidence=f_data.get("confidence", 0.0),
            found_at=datetime.fromisoformat(f_data["found_at"]) if f_data.get("found_at") else datetime.now(),
        )
        findings.append(finding)
    return findings


def _deserialize_engineering_findings(json_str: str) -> list[EngineeringFinding]:
    """Deserialize engineering findings from JSON."""
    data = json.loads(json_str)
    findings = []
    for f_data in data:
        finding = EngineeringFinding(
            id=_safe_uuid_parse(f_data.get("id")),
            title=f_data.get("title", ""),
            description=f_data.get("description", ""),
            severity=Severity(f_data["severity"]) if f_data.get("severity") else Severity.MEDIUM,
            category=EngineeringCategory(f_data["category"]) if f_data.get("category") else EngineeringCategory.HIGH_COMPLEXITY,
            dimension=ReviewDimension.ENGINEERING,
            complexity_score=f_data.get("complexity_score", 0),
            estimated_effort=f_data.get("estimated_effort", ""),
            estimated_days=f_data.get("estimated_days", ""),
            affected_files=f_data.get("affected_files", []),
            affected_functions=f_data.get("affected_functions", []),
            lines_of_code_affected=f_data.get("lines_of_code_affected", 0),
            tech_debt_items=f_data.get("tech_debt_items", 0),
            test_coverage_gap=f_data.get("test_coverage_gap", 0.0),
            affected_entities=[_safe_uuid_parse(e) for e in f_data.get("affected_entities", [])],
            affected_relationships=[_safe_uuid_parse(r) for r in f_data.get("affected_relationships", [])],
            source_type=f_data.get("source_type", ""),
            source_reference=f_data.get("source_reference", ""),
            recommendation=f_data.get("recommendation", ""),
            mitigations=f_data.get("mitigations", []),
            refactoring_suggestions=f_data.get("refactoring_suggestions", []),
            confidence=f_data.get("confidence", 0.0),
            found_at=datetime.fromisoformat(f_data["found_at"]) if f_data.get("found_at") else datetime.now(),
        )
        findings.append(finding)
    return findings


def _deserialize_architecture_findings(json_str: str) -> list[ArchitectureFinding]:
    """Deserialize architecture findings from JSON."""
    data = json.loads(json_str)
    findings = []
    for f_data in data:
        finding = ArchitectureFinding(
            id=_safe_uuid_parse(f_data.get("id")),
            title=f_data.get("title", ""),
            description=f_data.get("description", ""),
            severity=Severity(f_data["severity"]) if f_data.get("severity") else Severity.MEDIUM,
            category=ArchitectureCategory(f_data["category"]) if f_data.get("category") else ArchitectureCategory.MISSING_API_CONTRACT,
            dimension=ReviewDimension.ARCHITECTURE,
            architectural_pattern=f_data.get("architectural_pattern", ""),
            affected_services=f_data.get("affected_services", []),
            affected_apis=f_data.get("affected_apis", []),
            dependency_chain=f_data.get("dependency_chain", []),
            is_circular_dependency=f_data.get("is_circular_dependency", False),
            coupling_score=f_data.get("coupling_score", 0.0),
            breaking_change=f_data.get("breaking_change", False),
            downstream_impact=f_data.get("downstream_impact", []),
            upstream_dependencies=f_data.get("upstream_dependencies", []),
            affected_entities=[_safe_uuid_parse(e) for e in f_data.get("affected_entities", [])],
            affected_relationships=[_safe_uuid_parse(r) for r in f_data.get("affected_relationships", [])],
            source_type=f_data.get("source_type", ""),
            source_reference=f_data.get("source_reference", ""),
            recommendation=f_data.get("recommendation", ""),
            mitigations=f_data.get("mitigations", []),
            design_alternatives=f_data.get("design_alternatives", []),
            confidence=f_data.get("confidence", 0.0),
            found_at=datetime.fromisoformat(f_data["found_at"]) if f_data.get("found_at") else datetime.now(),
        )
        findings.append(finding)
    return findings


def _serialize_predicted_questions(questions: list[PredictedQuestion]) -> str:
    """Serialize predicted questions to JSON."""
    return json.dumps([_uuid_to_str(q.__dict__) for q in questions])


def _deserialize_predicted_questions(json_str: str) -> list[PredictedQuestion]:
    """Deserialize predicted questions from JSON."""
    if not json_str:
        return []
    data = json.loads(json_str)
    questions = []
    for q_data in data:
        # Deserialize code evidence
        code_evidence = []
        for ce_data in q_data.get("code_evidence", []):
            ce = CodeEvidence(
                file_path=ce_data.get("file_path", ""),
                line_number=ce_data.get("line_number"),
                code_snippet=ce_data.get("code_snippet", ""),
                context=ce_data.get("context", ""),
            )
            code_evidence.append(ce)
        
        # Deserialize suggested change
        suggested_change = None
        if q_data.get("suggested_change"):
            sc_data = q_data["suggested_change"]
            diff_hunks = []
            for dh_data in sc_data.get("diff_hunks", []):
                dh = DiffHunk(
                    operation=dh_data.get("operation", "add"),
                    content=dh_data.get("content", ""),
                    line_number=dh_data.get("line_number"),
                )
                diff_hunks.append(dh)
            
            suggested_change = PRDChange(
                id=_safe_uuid_parse(sc_data.get("id")),
                prediction_id=_safe_uuid_parse(sc_data.get("prediction_id")),
                section=sc_data.get("section", ""),
                start_line=sc_data.get("start_line", 0),
                end_line=sc_data.get("end_line", 0),
                change_type=sc_data.get("change_type", "addition"),
                current_text=sc_data.get("current_text", ""),
                suggested_text=sc_data.get("suggested_text", ""),
                diff_hunks=diff_hunks,
                reasoning=sc_data.get("reasoning", ""),
                applied_at=datetime.fromisoformat(sc_data["applied_at"]) if sc_data.get("applied_at") else None,
                status=sc_data.get("status", "open"),
                original_suggested_text=sc_data.get("original_suggested_text"),
                edited_by_pm=sc_data.get("edited_by_pm", False),
                edit_history=sc_data.get("edit_history", []),
            )
        
        question = PredictedQuestion(
            id=_safe_uuid_parse(q_data.get("id")),
            question=q_data.get("question", ""),
            team=q_data.get("team", ""),
            severity=q_data.get("severity", "likely"),
            reasoning=q_data.get("reasoning", ""),
            code_evidence=code_evidence,
            suggested_change=suggested_change,
            status=q_data.get("status", "open"),
            expert_ask_id=_safe_uuid_parse(q_data.get("expert_ask_id")) if q_data.get("expert_ask_id") else None,
        )
        questions.append(question)
    return questions


def _serialize_prd_quality_score(score: PRDQualityScore | None) -> str | None:
    """Serialize PRD quality score to JSON."""
    if score is None:
        return None
    return json.dumps(_uuid_to_str(score.__dict__))


def _deserialize_prd_quality_score(json_str: str | None) -> PRDQualityScore | None:
    """Deserialize PRD quality score from JSON."""
    if not json_str:
        return None
    data = json.loads(json_str)
    return PRDQualityScore(
        score=data.get("score", 0.0),
        grade=data.get("grade", "F"),
        gaps=data.get("gaps", []),
        predicted_pushback=data.get("predicted_pushback", 0),
        blockers=data.get("blockers", 0),
        likely_questions=data.get("likely_questions", 0),
        possible_questions=data.get("possible_questions", 0),
    )


def _serialize_effort_estimation(estimation: EffortEstimation | None) -> str | None:
    """Serialize effort estimation to JSON."""
    if estimation is None:
        return None
    return json.dumps(_uuid_to_str(estimation.__dict__))


def _deserialize_effort_estimation(json_str: str | None) -> EffortEstimation | None:
    """Deserialize effort estimation from JSON."""
    if not json_str:
        return None
    data = json.loads(json_str)
    return EffortEstimation(
        total_days=data.get("total_days", {"min": 0, "likely": 0, "max": 0}),
        by_requirement=data.get("by_requirement", []),
        codebase_support=data.get("codebase_support", 0.0),
        tldr=data.get("tldr", ""),
    )


# ==================== Database Schema ====================

SCHEMA_VERSION = 1

REVIEWS_SCHEMA = """
CREATE TABLE IF NOT EXISTS reviews (
    id TEXT PRIMARY KEY,
    intent_json TEXT NOT NULL,
    state_json TEXT NOT NULL,
    delta_result_json TEXT,
    
    -- Legacy findings (for backward compatibility)
    pattern_findings_json TEXT,
    llm_findings_json TEXT,
    graph_findings_json TEXT,
    merged_findings_json TEXT,
    
    -- Multi-dimension findings
    security_findings_json TEXT,
    privacy_findings_json TEXT,
    compliance_findings_json TEXT,
    engineering_findings_json TEXT,
    architecture_findings_json TEXT,
    
    dimensions_analyzed TEXT,
    
    -- Summary
    executive_summary TEXT,
    risk_rating TEXT,
    reviewed_at TEXT NOT NULL,
    
    -- PM features
    predicted_questions_json TEXT,
    prd_quality_score_json TEXT,
    effort_estimation_json TEXT,
    original_prd_content TEXT,
    
    -- Metadata
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reviews_reviewed_at ON reviews(reviewed_at);
CREATE INDEX IF NOT EXISTS idx_reviews_risk_rating ON reviews(risk_rating);
"""

REVIEW_STATUS_SCHEMA = """
CREATE TABLE IF NOT EXISTS review_status (
    review_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    progress REAL NOT NULL,
    message TEXT,
    dimensions TEXT,
    updated_at TEXT NOT NULL
);
"""

VALIDATIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS validations (
    id TEXT PRIMARY KEY,
    review_id TEXT NOT NULL,
    finding_id TEXT NOT NULL,
    status TEXT NOT NULL,
    validator_id TEXT NOT NULL,
    validator_team TEXT NOT NULL,
    notes TEXT,
    validated_at TEXT NOT NULL,
    
    UNIQUE(review_id, finding_id)
);

CREATE INDEX IF NOT EXISTS idx_validations_review_id ON validations(review_id);
"""

COMMENTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS comments (
    id TEXT PRIMARY KEY,
    review_id TEXT NOT NULL,
    finding_id TEXT NOT NULL,
    author_id TEXT NOT NULL,
    author_name TEXT NOT NULL,
    author_team TEXT NOT NULL,
    content TEXT NOT NULL,
    parent_comment_id TEXT,
    created_at TEXT NOT NULL,
    is_deleted INTEGER DEFAULT 0,
    deleted_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_comments_review_finding ON comments(review_id, finding_id);
"""

ASSIGNMENTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS assignments (
    id TEXT PRIMARY KEY,
    review_id TEXT NOT NULL,
    finding_id TEXT NOT NULL,
    team TEXT NOT NULL,
    user_id TEXT,
    assigned_by TEXT,
    assigned_at TEXT NOT NULL,
    
    UNIQUE(review_id, finding_id)
);

CREATE INDEX IF NOT EXISTS idx_assignments_team ON assignments(team);
"""

FEEDBACK_SCHEMA = """
CREATE TABLE IF NOT EXISTS feedback (
    id TEXT PRIMARY KEY,
    review_id TEXT NOT NULL,
    finding_id TEXT NOT NULL,
    feedback_type TEXT NOT NULL,
    original_value TEXT NOT NULL,
    expert_value TEXT NOT NULL,
    expert_id TEXT NOT NULL,
    expert_team TEXT NOT NULL,
    reasoning TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_feedback_review_finding ON feedback(review_id, finding_id);
"""

LIFECYCLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS lifecycle (
    review_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    updated_by TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    notes TEXT
);
"""

LIFECYCLE_HISTORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS lifecycle_history (
    id TEXT PRIMARY KEY,
    review_id TEXT NOT NULL,
    state TEXT NOT NULL,
    updated_by TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_lifecycle_history_review ON lifecycle_history(review_id);
"""

REVIEW_REQUESTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS review_requests (
    id TEXT PRIMARY KEY,
    review_id TEXT NOT NULL,
    finding_id TEXT NOT NULL,
    requesting_team TEXT NOT NULL,
    target_team TEXT NOT NULL,
    question TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    deadline TEXT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    response TEXT,
    responded_by TEXT,
    responded_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_review_requests_review ON review_requests(review_id);
CREATE INDEX IF NOT EXISTS idx_review_requests_target_team ON review_requests(target_team);
"""

CONSENSUS_VOTES_SCHEMA = """
CREATE TABLE IF NOT EXISTS consensus_votes (
    id TEXT PRIMARY KEY,
    review_id TEXT NOT NULL,
    finding_id TEXT NOT NULL,
    team TEXT NOT NULL,
    vote TEXT NOT NULL,
    voter_id TEXT NOT NULL,
    notes TEXT,
    voted_at TEXT NOT NULL,
    
    UNIQUE(review_id, finding_id, team)
);

CREATE INDEX IF NOT EXISTS idx_consensus_votes_review_finding ON consensus_votes(review_id, finding_id);
"""

PATTERNS_SCHEMA = """
CREATE TABLE IF NOT EXISTS patterns (
    id TEXT PRIMARY KEY,
    pattern_type TEXT NOT NULL,
    pattern_signature TEXT NOT NULL,
    decision TEXT NOT NULL,
    conditions TEXT NOT NULL,
    reasoning TEXT NOT NULL,
    source_feedback_ids TEXT NOT NULL,
    times_applied INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_patterns_type ON patterns(pattern_type);
"""

CODEBASE_PROFILES_SCHEMA = """
CREATE TABLE IF NOT EXISTS codebase_profiles (
    id TEXT PRIMARY KEY,
    codebase_path TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    attack_surface_json TEXT NOT NULL,
    entity_inventory_json TEXT NOT NULL,
    cumulative_findings_json TEXT NOT NULL,
    coverage_json TEXT NOT NULL,
    historical_trend_json TEXT NOT NULL,
    review_count INTEGER DEFAULT 0,
    last_review_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_codebase_profiles_path ON codebase_profiles(codebase_path);
"""

THREAT_CANVAS_SCHEMA = """
CREATE TABLE IF NOT EXISTS threat_canvases (
    id TEXT PRIMARY KEY,
    review_id TEXT,
    title TEXT NOT NULL,
    canvas_state_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_threat_canvases_review ON threat_canvases(review_id);
"""

SCHEMA_VERSION_TABLE = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);
"""


# ==================== SQLite Review Storage ====================

class SQLiteReviewStorage(ReviewStorage):
    """
    SQLite-based persistent review storage.
    
    Stores reviews in a local SQLite database file.
    Thread-safe and suitable for single-instance deployments.
    """
    
    def __init__(self, db_path: str | Path = "context_graph_reviews.db") -> None:
        """
        Initialize SQLite review storage.
        
        Args:
            db_path: Path to the SQLite database file.
                     Defaults to 'context_graph_reviews.db' in current directory.
        """
        self.db_path = Path(db_path)
        self._initialized = False
    
    async def _ensure_initialized(self) -> None:
        """Ensure database tables are created."""
        if self._initialized:
            return
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(SCHEMA_VERSION_TABLE)
            await db.executescript(REVIEWS_SCHEMA)
            await db.executescript(REVIEW_STATUS_SCHEMA)
            await db.commit()
        
        self._initialized = True
        logger.info(f"SQLite review storage initialized at {self.db_path}")
    
    async def save_review(self, review_id: str, result: ReviewResult) -> None:
        """Save a review result."""
        await self._ensure_initialized()
        
        now = datetime.now().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO reviews (
                    id, intent_json, state_json, delta_result_json,
                    pattern_findings_json, llm_findings_json, graph_findings_json, merged_findings_json,
                    security_findings_json, privacy_findings_json, compliance_findings_json,
                    engineering_findings_json, architecture_findings_json,
                    dimensions_analyzed, executive_summary, risk_rating, reviewed_at,
                    predicted_questions_json, prd_quality_score_json, effort_estimation_json,
                    original_prd_content, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    review_id,
                    _serialize_intent(result.intent),
                    _serialize_state(result.state),
                    json.dumps(_uuid_to_str(result.delta_result.__dict__)) if result.delta_result else None,
                    _serialize_findings(result.pattern_findings, "security"),
                    _serialize_findings(result.llm_findings, "security"),
                    _serialize_findings(result.graph_findings, "security"),
                    _serialize_findings(result.merged_findings, "security"),
                    _serialize_findings(result.security_findings, "security"),
                    _serialize_findings(result.privacy_findings, "privacy"),
                    _serialize_findings(result.compliance_findings, "compliance"),
                    _serialize_findings(result.engineering_findings, "engineering"),
                    _serialize_findings(result.architecture_findings, "architecture"),
                    json.dumps([d.value for d in result.dimensions_analyzed]),
                    result.executive_summary,
                    result.risk_rating,
                    result.reviewed_at.isoformat(),
                    _serialize_predicted_questions(result.predicted_questions),
                    _serialize_prd_quality_score(result.prd_quality_score),
                    _serialize_effort_estimation(result.effort_estimation),
                    result.original_prd_content,
                    now,
                    now,
                )
            )
            await db.commit()
        
        logger.debug(f"Saved review {review_id}")
    
    async def get_review(self, review_id: str) -> ReviewResult | None:
        """Get a review by ID."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM reviews WHERE id = ?", (review_id,)
            ) as cursor:
                row = await cursor.fetchone()
        
        if not row:
            return None
        
        # Reconstruct ReviewResult
        result = ReviewResult(
            review_id=_safe_uuid_parse(row["id"]),
            intent=_deserialize_intent(row["intent_json"]),
            state=_deserialize_state(row["state_json"]),
            pattern_findings=_deserialize_security_findings(row["pattern_findings_json"] or "[]"),
            llm_findings=_deserialize_security_findings(row["llm_findings_json"] or "[]"),
            graph_findings=_deserialize_security_findings(row["graph_findings_json"] or "[]"),
            merged_findings=_deserialize_security_findings(row["merged_findings_json"] or "[]"),
            security_findings=_deserialize_security_findings(row["security_findings_json"] or "[]"),
            privacy_findings=_deserialize_privacy_findings(row["privacy_findings_json"] or "[]"),
            compliance_findings=_deserialize_compliance_findings(row["compliance_findings_json"] or "[]"),
            engineering_findings=_deserialize_engineering_findings(row["engineering_findings_json"] or "[]"),
            architecture_findings=_deserialize_architecture_findings(row["architecture_findings_json"] or "[]"),
            dimensions_analyzed=[ReviewDimension(d) for d in json.loads(row["dimensions_analyzed"] or "[]")],
            executive_summary=row["executive_summary"] or "",
            risk_rating=row["risk_rating"] or "",
            reviewed_at=datetime.fromisoformat(row["reviewed_at"]),
            predicted_questions=_deserialize_predicted_questions(row["predicted_questions_json"]),
            prd_quality_score=_deserialize_prd_quality_score(row["prd_quality_score_json"]),
            effort_estimation=_deserialize_effort_estimation(row["effort_estimation_json"]),
            original_prd_content=row["original_prd_content"] or "",
        )
        
        return result
    
    async def delete_review(self, review_id: str) -> bool:
        """Delete a review."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM reviews WHERE id = ?", (review_id,)
            )
            await db.execute(
                "DELETE FROM review_status WHERE review_id = ?", (review_id,)
            )
            await db.commit()
            return cursor.rowcount > 0
    
    async def list_reviews(self) -> list[dict[str, Any]]:
        """List all reviews with summary info."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT r.id, r.intent_json, r.risk_rating, r.reviewed_at,
                       r.security_findings_json, r.privacy_findings_json,
                       r.compliance_findings_json, r.engineering_findings_json,
                       r.architecture_findings_json, r.dimensions_analyzed,
                       s.status
                FROM reviews r
                LEFT JOIN review_status s ON r.id = s.review_id
                ORDER BY r.reviewed_at DESC
                """
            ) as cursor:
                rows = await cursor.fetchall()
        
        reviews = []
        for row in rows:
            intent = _deserialize_intent(row["intent_json"])
            
            # Count findings
            security = json.loads(row["security_findings_json"] or "[]")
            privacy = json.loads(row["privacy_findings_json"] or "[]")
            compliance = json.loads(row["compliance_findings_json"] or "[]")
            engineering = json.loads(row["engineering_findings_json"] or "[]")
            architecture = json.loads(row["architecture_findings_json"] or "[]")
            
            all_findings = security + privacy + compliance + engineering + architecture
            
            reviews.append({
                "review_id": row["id"],
                "title": intent.title,
                "status": row["status"] or "completed",
                "risk_rating": row["risk_rating"],
                "findings_count": len(all_findings),
                "dimensions": json.loads(row["dimensions_analyzed"] or "[]"),
                "security_findings": len(security),
                "privacy_findings": len(privacy),
                "compliance_findings": len(compliance),
                "engineering_findings": len(engineering),
                "architecture_findings": len(architecture),
                "reviewed_at": row["reviewed_at"],
            })
        
        return reviews
    
    async def update_review_status(
        self,
        review_id: str,
        status: str,
        progress: float,
        message: str,
        dimensions: list[str] | None = None,
    ) -> None:
        """Update the status of a running review."""
        await self._ensure_initialized()
        
        now = datetime.now().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO review_status (review_id, status, progress, message, dimensions, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (review_id, status, progress, message, json.dumps(dimensions or []), now)
            )
            await db.commit()
    
    async def get_review_status(self, review_id: str) -> dict[str, Any] | None:
        """Get the current status of a review."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM review_status WHERE review_id = ?", (review_id,)
            ) as cursor:
                row = await cursor.fetchone()
        
        if not row:
            return None
        
        return {
            "status": row["status"],
            "progress": row["progress"],
            "message": row["message"],
            "dimensions": json.loads(row["dimensions"] or "[]"),
        }


# ==================== SQLite Collaboration Storage ====================

class SQLiteCollaborationStorage(CollaborationStorage):
    """
    SQLite-based persistent collaboration data storage.
    
    Stores validations, comments, assignments, feedback, and more.
    """
    
    def __init__(self, db_path: str | Path = "context_graph_reviews.db") -> None:
        """
        Initialize SQLite collaboration storage.
        
        Args:
            db_path: Path to the SQLite database file.
                     Should be the same as ReviewStorage for shared data.
        """
        self.db_path = Path(db_path)
        self._initialized = False
    
    async def _ensure_initialized(self) -> None:
        """Ensure database tables are created."""
        if self._initialized:
            return
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(SCHEMA_VERSION_TABLE)
            await db.executescript(VALIDATIONS_SCHEMA)
            await db.executescript(COMMENTS_SCHEMA)
            await db.executescript(ASSIGNMENTS_SCHEMA)
            await db.executescript(FEEDBACK_SCHEMA)
            await db.executescript(LIFECYCLE_SCHEMA)
            await db.executescript(LIFECYCLE_HISTORY_SCHEMA)
            await db.executescript(REVIEW_REQUESTS_SCHEMA)
            await db.executescript(CONSENSUS_VOTES_SCHEMA)
            await db.executescript(PATTERNS_SCHEMA)
            await db.executescript(CODEBASE_PROFILES_SCHEMA)
            await db.executescript(THREAT_CANVAS_SCHEMA)
            await db.commit()
        
        self._initialized = True
        logger.info(f"SQLite collaboration storage initialized at {self.db_path}")
    
    # ==================== Finding Validation ====================
    
    async def save_finding_validation(
        self,
        review_id: str,
        finding_id: str,
        status: str,
        validator_id: str,
        validator_team: str,
        notes: str,
    ) -> dict[str, Any]:
        """Save a validation decision for a finding."""
        await self._ensure_initialized()
        
        validation_id = str(uuid4())
        now = datetime.now().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO validations 
                (id, review_id, finding_id, status, validator_id, validator_team, notes, validated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (validation_id, review_id, finding_id, status, validator_id, validator_team, notes, now)
            )
            await db.commit()
        
        return {
            "id": validation_id,
            "review_id": review_id,
            "finding_id": finding_id,
            "status": status,
            "validator_id": validator_id,
            "validator_team": validator_team,
            "notes": notes,
            "validated_at": now,
        }
    
    async def get_finding_validation(
        self,
        review_id: str,
        finding_id: str,
    ) -> dict[str, Any] | None:
        """Get the current validation status for a finding."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM validations WHERE review_id = ? AND finding_id = ?",
                (review_id, finding_id)
            ) as cursor:
                row = await cursor.fetchone()
        
        if not row:
            return None
        
        return dict(row)
    
    async def get_validations_for_review(
        self,
        review_id: str,
    ) -> dict[str, dict[str, Any]]:
        """Get all validations for a review, keyed by finding_id."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM validations WHERE review_id = ?", (review_id,)
            ) as cursor:
                rows = await cursor.fetchall()
        
        return {row["finding_id"]: dict(row) for row in rows}
    
    # ==================== Comments ====================
    
    async def add_comment(
        self,
        review_id: str,
        finding_id: str,
        author_id: str,
        author_name: str,
        author_team: str,
        content: str,
        parent_comment_id: str | None = None,
    ) -> dict[str, Any]:
        """Add a comment to a finding."""
        await self._ensure_initialized()
        
        comment_id = str(uuid4())
        now = datetime.now().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO comments 
                (id, review_id, finding_id, author_id, author_name, author_team, content, parent_comment_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (comment_id, review_id, finding_id, author_id, author_name, author_team, content, parent_comment_id, now)
            )
            await db.commit()
        
        return {
            "id": comment_id,
            "review_id": review_id,
            "finding_id": finding_id,
            "author_id": author_id,
            "author_name": author_name,
            "author_team": author_team,
            "content": content,
            "parent_comment_id": parent_comment_id,
            "created_at": now,
            "is_deleted": False,
        }
    
    async def get_comments(
        self,
        review_id: str,
        finding_id: str,
    ) -> list[dict[str, Any]]:
        """Get all comments for a finding."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT * FROM comments 
                WHERE review_id = ? AND finding_id = ? AND is_deleted = 0
                ORDER BY created_at ASC
                """,
                (review_id, finding_id)
            ) as cursor:
                rows = await cursor.fetchall()
        
        return [dict(row) for row in rows]
    
    async def get_comment_counts(
        self,
        review_id: str,
    ) -> dict[str, int]:
        """Get comment counts for all findings in a review."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """
                SELECT finding_id, COUNT(*) as count
                FROM comments
                WHERE review_id = ? AND is_deleted = 0
                GROUP BY finding_id
                """,
                (review_id,)
            ) as cursor:
                rows = await cursor.fetchall()
        
        return {row[0]: row[1] for row in rows}
    
    async def delete_comment(
        self,
        comment_id: str,
    ) -> bool:
        """Soft-delete a comment."""
        await self._ensure_initialized()
        
        now = datetime.now().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "UPDATE comments SET is_deleted = 1, deleted_at = ? WHERE id = ?",
                (now, comment_id)
            )
            await db.commit()
            return cursor.rowcount > 0
    
    # ==================== Team Assignment ====================
    
    async def assign_finding(
        self,
        review_id: str,
        finding_id: str,
        team: str,
        user_id: str | None = None,
        assigned_by: str | None = None,
    ) -> dict[str, Any]:
        """Assign a finding to a team/user."""
        await self._ensure_initialized()
        
        assignment_id = str(uuid4())
        now = datetime.now().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO assignments 
                (id, review_id, finding_id, team, user_id, assigned_by, assigned_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (assignment_id, review_id, finding_id, team, user_id, assigned_by, now)
            )
            await db.commit()
        
        return {
            "id": assignment_id,
            "review_id": review_id,
            "finding_id": finding_id,
            "team": team,
            "user_id": user_id,
            "assigned_by": assigned_by,
            "assigned_at": now,
        }
    
    async def get_assignments_for_review(
        self,
        review_id: str,
    ) -> dict[str, dict[str, Any]]:
        """Get all assignments for a review."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM assignments WHERE review_id = ?", (review_id,)
            ) as cursor:
                rows = await cursor.fetchall()
        
        return {row["finding_id"]: dict(row) for row in rows}
    
    async def get_team_queue(
        self,
        team: str,
    ) -> list[dict[str, Any]]:
        """Get all findings assigned to a team."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM assignments WHERE team = ?", (team,)
            ) as cursor:
                rows = await cursor.fetchall()
        
        return [dict(row) for row in rows]
    
    # ==================== Expert Feedback ====================
    
    async def save_expert_feedback(
        self,
        review_id: str,
        finding_id: str,
        feedback_type: str,
        original_value: str,
        expert_value: str,
        expert_id: str,
        expert_team: str,
        reasoning: str,
    ) -> dict[str, Any]:
        """Save expert feedback on a finding."""
        await self._ensure_initialized()
        
        feedback_id = str(uuid4())
        now = datetime.now().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO feedback 
                (id, review_id, finding_id, feedback_type, original_value, expert_value, expert_id, expert_team, reasoning, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (feedback_id, review_id, finding_id, feedback_type, original_value, expert_value, expert_id, expert_team, reasoning, now)
            )
            await db.commit()
        
        return {
            "id": feedback_id,
            "review_id": review_id,
            "finding_id": finding_id,
            "feedback_type": feedback_type,
            "original_value": original_value,
            "expert_value": expert_value,
            "expert_id": expert_id,
            "expert_team": expert_team,
            "reasoning": reasoning,
            "created_at": now,
        }
    
    async def get_feedback_for_finding(
        self,
        review_id: str,
        finding_id: str,
    ) -> list[dict[str, Any]]:
        """Get all expert feedback for a finding."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM feedback WHERE review_id = ? AND finding_id = ?",
                (review_id, finding_id)
            ) as cursor:
                rows = await cursor.fetchall()
        
        return [dict(row) for row in rows]
    
    async def get_feedback_stats(self) -> dict[str, Any]:
        """Get aggregated feedback statistics."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            # Total feedback
            async with db.execute("SELECT COUNT(*) FROM feedback") as cursor:
                total = (await cursor.fetchone())[0]
            
            # By type
            async with db.execute(
                "SELECT feedback_type, COUNT(*) FROM feedback GROUP BY feedback_type"
            ) as cursor:
                by_type = {row[0]: row[1] for row in await cursor.fetchall()}
            
            # By team
            async with db.execute(
                "SELECT expert_team, COUNT(*) FROM feedback GROUP BY expert_team"
            ) as cursor:
                by_team = {row[0]: row[1] for row in await cursor.fetchall()}
            
            # Rejection patterns
            async with db.execute(
                """
                SELECT SUBSTR(reasoning, 1, 50), COUNT(*) as cnt
                FROM feedback 
                WHERE feedback_type = 'accuracy' AND expert_value = 'rejected'
                GROUP BY SUBSTR(reasoning, 1, 50)
                ORDER BY cnt DESC
                LIMIT 10
                """
            ) as cursor:
                rejection_reasons = {row[0]: row[1] for row in await cursor.fetchall()}
        
        return {
            "total_feedback": total,
            "by_type": by_type,
            "by_team": by_team,
            "common_rejection_reasons": rejection_reasons,
        }
    
    # ==================== Review Lifecycle ====================
    
    async def update_review_lifecycle(
        self,
        review_id: str,
        state: str,
        updated_by: str,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Update the lifecycle state of a review."""
        await self._ensure_initialized()
        
        now = datetime.now().isoformat()
        history_id = str(uuid4())
        
        async with aiosqlite.connect(self.db_path) as db:
            # Update current state
            await db.execute(
                """
                INSERT OR REPLACE INTO lifecycle (review_id, state, updated_by, updated_at, notes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (review_id, state, updated_by, now, notes)
            )
            
            # Add to history
            await db.execute(
                """
                INSERT INTO lifecycle_history (id, review_id, state, updated_by, updated_at, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (history_id, review_id, state, updated_by, now, notes)
            )
            
            await db.commit()
        
        return {
            "review_id": review_id,
            "state": state,
            "updated_by": updated_by,
            "updated_at": now,
            "notes": notes,
        }
    
    async def get_review_lifecycle(
        self,
        review_id: str,
    ) -> dict[str, Any] | None:
        """Get the current lifecycle state of a review."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM lifecycle WHERE review_id = ?", (review_id,)
            ) as cursor:
                row = await cursor.fetchone()
        
        if not row:
            return None
        
        return dict(row)
    
    async def get_lifecycle_history(
        self,
        review_id: str,
    ) -> list[dict[str, Any]]:
        """Get lifecycle state history for a review."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM lifecycle_history WHERE review_id = ? ORDER BY updated_at ASC",
                (review_id,)
            ) as cursor:
                rows = await cursor.fetchall()
        
        return [dict(row) for row in rows]
    
    # ==================== Cross-Team Requests ====================
    
    async def create_review_request(
        self,
        review_id: str,
        finding_id: str,
        requesting_team: str,
        target_team: str,
        question: str,
        requested_by: str,
        deadline: str | None = None,
    ) -> dict[str, Any]:
        """Create a cross-team review request."""
        await self._ensure_initialized()
        
        request_id = str(uuid4())
        now = datetime.now().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO review_requests 
                (id, review_id, finding_id, requesting_team, target_team, question, requested_by, deadline, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (request_id, review_id, finding_id, requesting_team, target_team, question, requested_by, deadline, "pending", now)
            )
            await db.commit()
        
        return {
            "id": request_id,
            "review_id": review_id,
            "finding_id": finding_id,
            "requesting_team": requesting_team,
            "target_team": target_team,
            "question": question,
            "requested_by": requested_by,
            "deadline": deadline,
            "status": "pending",
            "created_at": now,
            "response": None,
            "responded_by": None,
            "responded_at": None,
        }
    
    async def get_review_requests(
        self,
        review_id: str | None = None,
        target_team: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get review requests filtered by review or target team."""
        await self._ensure_initialized()
        
        query = "SELECT * FROM review_requests WHERE 1=1"
        params: list[str] = []
        
        if review_id:
            query += " AND review_id = ?"
            params.append(review_id)
        
        if target_team:
            query += " AND target_team = ?"
            params.append(target_team)
        
        query += " ORDER BY created_at DESC"
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
        
        return [dict(row) for row in rows]
    
    async def respond_to_request(
        self,
        request_id: str,
        response: str,
        responded_by: str,
    ) -> dict[str, Any]:
        """Respond to a cross-team review request."""
        await self._ensure_initialized()
        
        now = datetime.now().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE review_requests 
                SET status = 'responded', response = ?, responded_by = ?, responded_at = ?
                WHERE id = ?
                """,
                (response, responded_by, now, request_id)
            )
            await db.commit()
            
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM review_requests WHERE id = ?", (request_id,)
            ) as cursor:
                row = await cursor.fetchone()
        
        if not row:
            raise ValueError(f"Request {request_id} not found")
        
        return dict(row)
    
    # ==================== Consensus Mode ====================
    
    async def add_consensus_vote(
        self,
        review_id: str,
        finding_id: str,
        team: str,
        vote: str,
        voter_id: str,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Add a consensus vote for a finding."""
        await self._ensure_initialized()
        
        vote_id = str(uuid4())
        now = datetime.now().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO consensus_votes 
                (id, review_id, finding_id, team, vote, voter_id, notes, voted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (vote_id, review_id, finding_id, team, vote, voter_id, notes, now)
            )
            await db.commit()
        
        return {
            "id": vote_id,
            "review_id": review_id,
            "finding_id": finding_id,
            "team": team,
            "vote": vote,
            "voter_id": voter_id,
            "notes": notes,
            "voted_at": now,
        }
    
    async def get_consensus_status(
        self,
        review_id: str,
        finding_id: str,
    ) -> dict[str, Any]:
        """Get consensus voting status for a finding."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM consensus_votes WHERE review_id = ? AND finding_id = ?",
                (review_id, finding_id)
            ) as cursor:
                rows = await cursor.fetchall()
        
        votes = {row["team"]: dict(row) for row in rows}
        
        # Count votes
        vote_counts = {"approve": 0, "reject": 0, "abstain": 0}
        for vote_data in votes.values():
            vote_type = vote_data.get("vote", "abstain")
            if vote_type in vote_counts:
                vote_counts[vote_type] += 1
        
        total_votes = len(votes)
        
        return {
            "review_id": review_id,
            "finding_id": finding_id,
            "votes": votes,
            "vote_counts": vote_counts,
            "total_votes": total_votes,
            "has_consensus": (
                vote_counts["approve"] > vote_counts["reject"] and total_votes >= 2
            ),
        }
    
    # ==================== Pattern Learning ====================
    
    async def save_learned_pattern(
        self,
        pattern_type: str,
        pattern_signature: str,
        decision: str,
        conditions: list[str],
        reasoning: str,
        source_feedback_ids: list[str],
    ) -> dict[str, Any]:
        """Save a learned pattern from feedback aggregation."""
        await self._ensure_initialized()
        
        pattern_id = str(uuid4())
        now = datetime.now().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO patterns 
                (id, pattern_type, pattern_signature, decision, conditions, reasoning, source_feedback_ids, times_applied, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (pattern_id, pattern_type, pattern_signature, decision, json.dumps(conditions), reasoning, json.dumps(source_feedback_ids), 0, now)
            )
            await db.commit()
        
        return {
            "id": pattern_id,
            "pattern_type": pattern_type,
            "pattern_signature": pattern_signature,
            "decision": decision,
            "conditions": conditions,
            "reasoning": reasoning,
            "source_feedback_ids": source_feedback_ids,
            "times_applied": 0,
            "created_at": now,
        }
    
    async def get_similar_patterns(
        self,
        pattern_type: str,
        pattern_signature: str,
    ) -> list[dict[str, Any]]:
        """Find similar patterns for a given finding."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM patterns WHERE pattern_type = ?", (pattern_type,)
            ) as cursor:
                rows = await cursor.fetchall()
        
        # Simple substring matching
        signature_lower = pattern_signature.lower()
        similar = []
        
        for row in rows:
            pattern_sig_lower = row["pattern_signature"].lower()
            sig_words = set(signature_lower.split())
            pattern_words = set(pattern_sig_lower.split())
            overlap = len(sig_words & pattern_words)
            
            if overlap >= 2 or signature_lower in pattern_sig_lower or pattern_sig_lower in signature_lower:
                pattern_dict = dict(row)
                pattern_dict["conditions"] = json.loads(pattern_dict["conditions"])
                pattern_dict["source_feedback_ids"] = json.loads(pattern_dict["source_feedback_ids"])
                pattern_dict["similarity_score"] = overlap / max(len(sig_words), 1)
                similar.append(pattern_dict)
        
        return sorted(similar, key=lambda p: p.get("similarity_score", 0), reverse=True)[:5]
    
    async def get_pattern_insights(self) -> dict[str, Any]:
        """Get aggregated pattern learning insights."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Total patterns
            async with db.execute("SELECT COUNT(*) FROM patterns") as cursor:
                total = (await cursor.fetchone())[0]
            
            # By type
            async with db.execute(
                "SELECT pattern_type, COUNT(*) FROM patterns GROUP BY pattern_type"
            ) as cursor:
                by_type = {row[0]: row[1] for row in await cursor.fetchall()}
            
            # By decision
            async with db.execute(
                "SELECT decision, COUNT(*) FROM patterns GROUP BY decision"
            ) as cursor:
                by_decision = {row[0]: row[1] for row in await cursor.fetchall()}
            
            # Most applied
            async with db.execute(
                """
                SELECT pattern_signature, decision, times_applied 
                FROM patterns 
                ORDER BY times_applied DESC 
                LIMIT 10
                """
            ) as cursor:
                most_applied = [
                    {
                        "pattern_signature": row[0],
                        "decision": row[1],
                        "times_applied": row[2],
                    }
                    for row in await cursor.fetchall()
                ]
        
        return {
            "total_patterns": total,
            "by_type": by_type,
            "by_decision": by_decision,
            "most_applied_patterns": most_applied,
        }
    
    # ==================== Codebase Security Profile ====================
    
    async def save_codebase_profile(
        self,
        profile_id: str,
        codebase_path: str,
        display_name: str,
        attack_surface: dict[str, Any],
        entity_inventory: dict[str, Any],
        cumulative_findings: dict[str, Any],
        coverage: dict[str, Any],
        historical_trend: dict[str, Any],
        review_count: int,
        last_review_id: str | None = None,
    ) -> dict[str, Any]:
        """Save or update a codebase security profile."""
        await self._ensure_initialized()
        
        now = datetime.now().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            # Check if profile exists for created_at
            async with db.execute(
                "SELECT created_at FROM codebase_profiles WHERE id = ?", (profile_id,)
            ) as cursor:
                existing = await cursor.fetchone()
            
            created_at = existing[0] if existing else now
            
            await db.execute(
                """
                INSERT OR REPLACE INTO codebase_profiles 
                (id, codebase_path, display_name, attack_surface_json, entity_inventory_json,
                 cumulative_findings_json, coverage_json, historical_trend_json,
                 review_count, last_review_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile_id,
                    codebase_path,
                    display_name,
                    json.dumps(attack_surface),
                    json.dumps(entity_inventory),
                    json.dumps(cumulative_findings),
                    json.dumps(coverage),
                    json.dumps(historical_trend),
                    review_count,
                    last_review_id,
                    created_at,
                    now,
                )
            )
            await db.commit()
        
        return {
            "id": profile_id,
            "codebase_path": codebase_path,
            "display_name": display_name,
            "attack_surface": attack_surface,
            "entity_inventory": entity_inventory,
            "cumulative_findings": cumulative_findings,
            "coverage": coverage,
            "historical_trend": historical_trend,
            "review_count": review_count,
            "last_review_id": last_review_id,
            "created_at": created_at,
            "updated_at": now,
        }
    
    async def get_codebase_profile(self, profile_id: str) -> dict[str, Any] | None:
        """Get a codebase profile by ID."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM codebase_profiles WHERE id = ?", (profile_id,)
            ) as cursor:
                row = await cursor.fetchone()
        
        if not row:
            return None
        
        return self._row_to_profile(row)
    
    async def get_codebase_profile_by_path(self, codebase_path: str) -> dict[str, Any] | None:
        """Get a codebase profile by codebase path."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM codebase_profiles WHERE codebase_path = ?", (codebase_path,)
            ) as cursor:
                row = await cursor.fetchone()
        
        if not row:
            return None
        
        return self._row_to_profile(row)
    
    async def list_codebase_profiles(self) -> list[dict[str, Any]]:
        """List all codebase profiles (summary view)."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM codebase_profiles ORDER BY updated_at DESC"
            ) as cursor:
                rows = await cursor.fetchall()
        
        return [self._row_to_profile(row) for row in rows]
    
    async def delete_codebase_profile(self, profile_id: str) -> bool:
        """Delete a codebase profile."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM codebase_profiles WHERE id = ?", (profile_id,)
            )
            await db.commit()
            return cursor.rowcount > 0
    
    @staticmethod
    def _row_to_profile(row: Any) -> dict[str, Any]:
        """Convert a database row to a profile dict."""
        return {
            "id": row["id"],
            "codebase_path": row["codebase_path"],
            "display_name": row["display_name"],
            "attack_surface": json.loads(row["attack_surface_json"]),
            "entity_inventory": json.loads(row["entity_inventory_json"]),
            "cumulative_findings": json.loads(row["cumulative_findings_json"]),
            "coverage": json.loads(row["coverage_json"]),
            "historical_trend": json.loads(row["historical_trend_json"]),
            "review_count": row["review_count"],
            "last_review_id": row["last_review_id"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    # ==================== Threat Canvas ====================

    async def save_threat_canvas(
        self,
        canvas_id: str,
        title: str,
        canvas_state: dict[str, Any],
        review_id: str | None = None,
    ) -> dict[str, Any]:
        """Create or update a threat canvas."""
        await self._ensure_initialized()

        now = datetime.now().isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            existing = await db.execute(
                "SELECT created_at FROM threat_canvases WHERE id = ?", (canvas_id,)
            )
            row = await existing.fetchone()
            created_at = row[0] if row else now

            await db.execute(
                """
                INSERT OR REPLACE INTO threat_canvases
                    (id, review_id, title, canvas_state_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (canvas_id, review_id, title, json.dumps(canvas_state), created_at, now),
            )
            await db.commit()

        return {
            "canvas_id": canvas_id,
            "review_id": review_id,
            "title": title,
            "created_at": created_at,
            "updated_at": now,
            **canvas_state,
        }

    async def get_threat_canvas(self, canvas_id: str) -> dict[str, Any] | None:
        """Get a threat canvas by ID."""
        await self._ensure_initialized()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM threat_canvases WHERE id = ?", (canvas_id,)
            ) as cursor:
                row = await cursor.fetchone()

        if not row:
            return None

        return self._row_to_canvas(row)

    async def list_threat_canvases(self) -> list[dict[str, Any]]:
        """List all threat canvases (summary view)."""
        await self._ensure_initialized()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id, review_id, title, created_at, updated_at FROM threat_canvases ORDER BY updated_at DESC"
            ) as cursor:
                rows = await cursor.fetchall()

        return [
            {
                "canvas_id": row["id"],
                "review_id": row["review_id"],
                "title": row["title"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

    async def delete_threat_canvas(self, canvas_id: str) -> bool:
        """Delete a threat canvas."""
        await self._ensure_initialized()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM threat_canvases WHERE id = ?", (canvas_id,)
            )
            await db.commit()
            return cursor.rowcount > 0

    @staticmethod
    def _row_to_canvas(row: Any) -> dict[str, Any]:
        """Convert a database row to a canvas dict."""
        state = json.loads(row["canvas_state_json"])
        return {
            "canvas_id": row["id"],
            "review_id": row["review_id"],
            "title": row["title"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            **state,
        }


# ==================== Factory Functions ====================

def create_sqlite_storage(
    db_path: str | Path = "context_graph_reviews.db"
) -> tuple[SQLiteReviewStorage, SQLiteCollaborationStorage]:
    """
    Create SQLite storage instances for both reviews and collaboration.
    
    Args:
        db_path: Path to the SQLite database file.
        
    Returns:
        Tuple of (review_storage, collaboration_storage) instances.
    """
    review_storage = SQLiteReviewStorage(db_path)
    collaboration_storage = SQLiteCollaborationStorage(db_path)
    return review_storage, collaboration_storage
