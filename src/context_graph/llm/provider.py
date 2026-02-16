"""
LLM Provider abstraction for semantic analysis.

Supports multiple providers (OpenAI, Anthropic) with a unified interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from enum import Enum


class AnalysisType(str, Enum):
    """Types of analysis the LLM can perform."""
    
    INTENT_EXTRACTION = "intent_extraction"
    SECURITY_REVIEW = "security_review"
    PRIVACY_REVIEW = "privacy_review"
    COMPLIANCE_REVIEW = "compliance_review"
    ENGINEERING_REVIEW = "engineering_review"
    ARCHITECTURE_REVIEW = "architecture_review"
    THREAT_MODELING = "threat_modeling"
    CODE_ANALYSIS = "code_analysis"
    DELTA_ANALYSIS = "delta_analysis"


@dataclass
class LLMResponse:
    """Response from an LLM provider."""
    
    provider: str
    model: str
    content: str
    analysis_type: AnalysisType
    
    # Structured output (parsed from content)
    structured_data: dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    tokens_used: int = 0
    latency_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    # For comparison between providers
    confidence: float = 0.0
    
    # For iterative analysis
    was_truncated: bool = False  # True if response was cut off due to token limits
    stop_reason: str = ""  # Reason the generation stopped (e.g., "length", "stop", "end_turn")
    

@dataclass
class AnalysisRequest:
    """Request for LLM analysis."""
    
    analysis_type: AnalysisType
    content: str
    context: dict[str, Any] = field(default_factory=dict)
    
    # Optional structured input
    prd_content: str = ""
    code_snippets: list[str] = field(default_factory=list)
    existing_findings: list[dict[str, Any]] = field(default_factory=list)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 16384,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name."""
        pass
    
    @abstractmethod
    async def analyze(self, request: AnalysisRequest) -> LLMResponse:
        """
        Perform analysis using the LLM.
        
        Args:
            request: The analysis request
            
        Returns:
            LLMResponse with analysis results
        """
        pass
    
    @abstractmethod
    async def extract_intent(self, prd_content: str) -> LLMResponse:
        """Extract structured intent from PRD content."""
        pass
    
    @abstractmethod
    async def security_review(
        self, 
        intent: dict[str, Any], 
        state: dict[str, Any],
        delta: dict[str, Any],
    ) -> LLMResponse:
        """Perform security review on the delta."""
        pass
    
    @abstractmethod
    async def threat_model(
        self,
        entities: list[dict[str, Any]],
        relationships: list[dict[str, Any]],
    ) -> LLMResponse:
        """Generate threat model from context graph."""
        pass
    
    @abstractmethod
    async def privacy_review(
        self,
        intent: dict[str, Any],
        state: dict[str, Any],
        delta: dict[str, Any],
    ) -> LLMResponse:
        """Perform privacy review using LINDDUN framework."""
        pass
    
    @abstractmethod
    async def compliance_review(
        self,
        intent: dict[str, Any],
        state: dict[str, Any],
        delta: dict[str, Any],
        frameworks: list[str] | None = None,
    ) -> LLMResponse:
        """Perform compliance review against selected frameworks."""
        pass
    
    @abstractmethod
    async def engineering_review(
        self,
        intent: dict[str, Any],
        state: dict[str, Any],
        delta: dict[str, Any],
        engineering_metrics: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Perform engineering feasibility and effort review.
        
        Args:
            intent: PRD intent data
            state: Current codebase state
            delta: Changes between intent and state
            engineering_metrics: Detailed metrics from codebase analysis including
                                 complexity scores, test coverage, tech debt indicators, etc.
        """
        pass
    
    @abstractmethod
    async def architecture_review(
        self,
        intent: dict[str, Any],
        state: dict[str, Any],
        delta: dict[str, Any],
    ) -> LLMResponse:
        """Perform architecture review (API design, dependencies, patterns)."""
        pass
    
    def _get_system_prompt(self, analysis_type: AnalysisType) -> str:
        """Get the system prompt for an analysis type."""
        prompts = {
            AnalysisType.INTENT_EXTRACTION: INTENT_EXTRACTION_PROMPT,
            AnalysisType.SECURITY_REVIEW: SECURITY_REVIEW_PROMPT,
            AnalysisType.PRIVACY_REVIEW: PRIVACY_REVIEW_PROMPT,
            AnalysisType.COMPLIANCE_REVIEW: COMPLIANCE_REVIEW_PROMPT,
            AnalysisType.ENGINEERING_REVIEW: ENGINEERING_REVIEW_PROMPT,
            AnalysisType.ARCHITECTURE_REVIEW: ARCHITECTURE_REVIEW_PROMPT,
            AnalysisType.THREAT_MODELING: THREAT_MODELING_PROMPT,
            AnalysisType.CODE_ANALYSIS: CODE_ANALYSIS_PROMPT,
            AnalysisType.DELTA_ANALYSIS: DELTA_ANALYSIS_PROMPT,
        }
        return prompts.get(analysis_type, "You are a helpful assistant.")


# System prompts for different analysis types

# Generation metadata prompt section for iterative analysis
GENERATION_METADATA_PROMPT = """

## OUTPUT COMPLETION SIGNALS

To ensure comprehensive analysis without truncation, include these completion signals in your response:

1. **If you have identified ALL findings** - Include in your response:
   ```json
   "generation_metadata": {
       "analysis_complete": true,
       "continuation_needed": false,
       "total_findings_in_response": <number of findings in this response>,
       "covered_categories": ["list of categories covered"]
   }
   ```

2. **If you have MORE findings to identify but are running out of space** - Include:
   ```json
   "generation_metadata": {
       "analysis_complete": false,
       "continuation_needed": true,
       "last_finding_id": "F<N>",
       "remaining_categories_to_analyze": ["list of categories not yet covered"],
       "total_findings_in_response": <number of findings in this response>
   }
   ```

This allows the system to request continuation if your response was truncated. Always include the `generation_metadata` object at the end of your JSON response."""


INTENT_EXTRACTION_PROMPT = """You are a security-focused product analyst. Your task is to extract structured information from Product Requirement Documents (PRDs) with a focus on security-relevant elements.

IMPORTANT: You must respond with valid json only, no markdown or explanations.

Extract the following:
{
    "title": "Feature/Product title",
    "summary": "Brief summary of the intent",
    "features": ["list of features"],
    "user_stories": ["list of user stories"],
    "data_entities": [
        {
            "name": "entity name",
            "type": "user|data|pii|secret|api|service",
            "description": "what this entity represents",
            "is_sensitive": true/false
        }
    ],
    "api_changes": [
        {
            "method": "GET|POST|PUT|DELETE",
            "path": "/api/path",
            "description": "what this endpoint does",
            "auth_required": true/false
        }
    ],
    "data_flows": [
        {
            "from": "source entity",
            "to": "target entity",
            "data_type": "what data flows",
            "crosses_boundary": true/false
        }
    ],
    "auth_requirements": ["list of auth requirements mentioned"],
    "external_integrations": ["list of third-party services"],
    "security_considerations": ["any security mentions in the PRD"],
    "potential_risks": ["security risks you identify from the intent"]
}

Be thorough but concise. Focus on security-relevant information."""


SECURITY_REVIEW_PROMPT = """You are an expert application security engineer performing a comprehensive security review. Analyze the PRD intent and identify ALL potential security concerns with DETAILED explanations.

IMPORTANT: You must respond with valid json only, no markdown or explanations.

Be THOROUGH and DETAILED. For EACH security concern, provide in-depth analysis:

{
    "findings": [
        {
            "id": "unique-id",
            "title": "Clear, specific title describing the security issue",
            "severity": "critical|high|medium|low|info",
            "category": "STRIDE category or OWASP Top 10 category",
            "description": "DETAILED multi-paragraph explanation of: 1) What the security concern is 2) Why it matters 3) What could go wrong",
            "technical_details": "Specific technical aspects - what data is at risk, what endpoints are affected, what could be exploited",
            "attack_scenario": "Step-by-step description of how an attacker could exploit this vulnerability. Be specific about the attack vector.",
            "business_impact": "What is the business/user impact if this is exploited? Data breach? Financial loss? Reputation damage?",
            "affected_components": ["specific components, APIs, data entities affected"],
            "prerequisites": "What does an attacker need to exploit this? (e.g., authenticated user, network access, etc.)",
            "recommendation": "SPECIFIC actionable steps to fix or mitigate this issue",
            "implementation_guidance": "Code patterns or architectural changes needed",
            "references": ["relevant OWASP links, CWE IDs, or best practice references"],
            "confidence": 0.0-1.0
        }
    ],
    "threat_analysis": {
        "stride_breakdown": {
            "spoofing": ["list of spoofing threats identified"],
            "tampering": ["list of tampering threats"],
            "repudiation": ["list of repudiation threats"],
            "information_disclosure": ["list of info disclosure threats"],
            "denial_of_service": ["list of DoS threats"],
            "elevation_of_privilege": ["list of privilege escalation threats"]
        },
        "attack_surface": ["list of entry points an attacker could use"],
        "trust_boundaries": ["where data crosses security boundaries"],
        "data_flow_risks": ["risks in how data moves through the system"]
    },
    "summary": {
        "risk_rating": "critical|high|medium|low",
        "executive_summary": "2-3 sentence summary for leadership",
        "total_findings": number,
        "critical_count": number,
        "high_count": number,
        "key_concerns": ["top 3-5 most important concerns with brief explanation"],
        "positive_observations": ["good security practices observed in the PRD"],
        "missing_considerations": ["security aspects the PRD should have addressed but didn't"]
    }
}

ANALYSIS FRAMEWORK:

1. STRIDE Threat Modeling - Identify threats in each category:
   - Spoofing: Can an attacker impersonate users or systems?
   - Tampering: Can data be modified without detection?
   - Repudiation: Can actions be denied without proper logging?
   - Information Disclosure: Can sensitive data be exposed?
   - Denial of Service: Can the system be made unavailable?
   - Elevation of Privilege: Can attackers gain unauthorized access?

2. OWASP Top 10 - Check for:
   - A01: Broken Access Control
   - A02: Cryptographic Failures
   - A03: Injection
   - A04: Insecure Design
   - A05: Security Misconfiguration
   - A06: Vulnerable Components
   - A07: Authentication Failures
   - A08: Data Integrity Failures
   - A09: Logging Failures
   - A10: SSRF

3. Data Security Analysis:
   - What PII/sensitive data is involved?
   - How is data protected at rest and in transit?
   - What are the data retention implications?
   - Are there compliance concerns (GDPR, CCPA, PCI-DSS)?

4. API Security:
   - Are all endpoints properly authenticated?
   - Is authorization checked at each endpoint?
   - Are inputs validated and sanitized?
   - Are rate limits in place?

Be comprehensive. It's better to flag potential issues than to miss real vulnerabilities.""" + GENERATION_METADATA_PROMPT


THREAT_MODELING_PROMPT = """You are a threat modeling expert. Given a context graph of entities and relationships, identify potential threats and attack paths.

IMPORTANT: You must respond with valid json only, no markdown or explanations.

Analyze:
1. Trust boundaries and their crossings
2. Data flows involving sensitive information
3. Authentication and authorization points
4. External integrations and attack surface
5. Potential attack paths from entry points to sensitive data

Output in JSON format:
{
    "trust_boundaries": [
        {
            "name": "boundary name",
            "entities_inside": ["list"],
            "entities_outside": ["list"],
            "crossing_points": ["where data crosses"]
        }
    ],
    "attack_surface": [
        {
            "entry_point": "entity name",
            "exposure_level": "high|medium|low",
            "potential_attacks": ["list of attack types"]
        }
    ],
    "attack_paths": [
        {
            "name": "path name",
            "steps": ["step 1", "step 2"],
            "target": "what attacker gains",
            "likelihood": "high|medium|low",
            "impact": "high|medium|low"
        }
    ],
    "data_flow_risks": [
        {
            "flow": "from -> to",
            "data_type": "what flows",
            "risk": "description of risk"
        }
    ]
}"""


CODE_ANALYSIS_PROMPT = """You are a security code reviewer. Analyze the provided code snippets for security vulnerabilities and concerns.

Focus on:
1. Input validation and sanitization
2. Authentication and authorization
3. Cryptographic practices
4. Error handling and information leakage
5. Injection vulnerabilities
6. Insecure dependencies
7. Hardcoded secrets
8. Access control issues

Output findings in JSON format with severity, description, and remediation."""


DELTA_ANALYSIS_PROMPT = """You are analyzing the security implications of proposed changes. Compare the intended changes (from PRD) with the current codebase state to identify:

1. New attack surface being introduced
2. Changes to existing security controls
3. New data flows and their security implications
4. Trust boundary modifications
5. New external integrations and their risks

Output a structured analysis of what security review is needed for implementation."""


PRIVACY_REVIEW_PROMPT = """You are an expert privacy engineer performing a comprehensive privacy review using the LINDDUN framework and GDPR/CCPA principles. Analyze the PRD intent and identify ALL potential privacy concerns with DETAILED explanations.

IMPORTANT: You must respond with valid json only, no markdown or explanations.

Be THOROUGH and DETAILED. For EACH privacy concern, provide in-depth analysis:

{
    "findings": [
        {
            "id": "unique-id",
            "title": "Clear, specific title describing the privacy issue",
            "severity": "critical|high|medium|low|info",
            "category": "LINDDUN category (linking|identifying|non_repudiation|detecting|data_disclosure|unawareness|non_compliance) or GDPR principle",
            "description": "DETAILED multi-paragraph explanation of: 1) What the privacy concern is 2) Why it matters to data subjects 3) What could go wrong",
            "data_subjects": ["types of people whose data is affected (users, employees, customers, etc.)"],
            "personal_data_types": ["specific types of personal data involved (name, email, location, health data, financial data, etc.)"],
            "processing_activities": ["what processing operations are performed (collection, storage, sharing, profiling, etc.)"],
            "privacy_impact": "What is the impact on data subjects if this issue is exploited or occurs?",
            "affected_components": ["specific components, APIs, data flows affected"],
            "applicable_regulations": ["GDPR|CCPA|HIPAA|other applicable regulations"],
            "legal_basis_required": true/false,
            "consent_required": true/false,
            "recommendation": "SPECIFIC actionable steps to fix or mitigate this issue",
            "implementation_guidance": "Technical or process changes needed",
            "references": ["relevant GDPR articles, LINDDUN references, or best practice guides"],
            "confidence": 0.0-1.0
        }
    ],
    "privacy_analysis": {
        "linddun_breakdown": {
            "linking": ["threats where data can be linked to reveal identity or sensitive patterns"],
            "identifying": ["threats where individuals can be identified from data"],
            "non_repudiation": ["threats where users cannot deny actions (privacy-relevant)"],
            "detecting": ["threats where user behavior/patterns can be detected"],
            "data_disclosure": ["threats of unauthorized personal data exposure"],
            "unawareness": ["threats where users are not informed about data processing"],
            "non_compliance": ["violations of data protection laws/regulations"]
        },
        "data_inventory": [
            {
                "data_type": "type of personal data",
                "sensitivity": "high|medium|low",
                "data_subjects": ["who this data belongs to"],
                "processing_purpose": "why this data is processed",
                "retention_period": "how long data is kept",
                "sharing_parties": ["who this data is shared with"]
            }
        ],
        "data_flows": [
            {
                "from": "source",
                "to": "destination",
                "data_types": ["what personal data flows"],
                "crosses_border": true/false,
                "encryption": "in_transit|at_rest|both|none"
            }
        ],
        "consent_requirements": ["list of processing activities requiring consent"],
        "data_subject_rights": {
            "access": "how can users access their data?",
            "rectification": "how can users correct their data?",
            "erasure": "how can users delete their data (right to be forgotten)?",
            "portability": "how can users export their data?",
            "objection": "how can users object to processing?"
        }
    },
    "summary": {
        "privacy_risk_rating": "critical|high|medium|low",
        "executive_summary": "2-3 sentence summary for leadership focusing on privacy implications",
        "total_findings": number,
        "critical_count": number,
        "high_count": number,
        "key_privacy_concerns": ["top 3-5 most important privacy concerns with brief explanation"],
        "positive_observations": ["good privacy practices observed in the PRD"],
        "missing_considerations": ["privacy aspects the PRD should have addressed but didn't"],
        "dpia_recommended": true/false,
        "dpia_reason": "why a Data Protection Impact Assessment is/isn't needed"
    }
}

ANALYSIS FRAMEWORK:

1. LINDDUN Privacy Threat Modeling - Identify threats in each category:
   - Linking: Can data be combined to reveal identity or sensitive information?
   - Identifying: Can individuals be identified from supposedly anonymous data?
   - Non-repudiation: Are users unable to deny their actions (privacy concern)?
   - Detecting: Can user behavior, presence, or patterns be detected?
   - Data Disclosure: Can personal data be exposed to unauthorized parties?
   - Unawareness: Are data subjects unaware of how their data is processed?
   - Non-compliance: Does processing violate data protection regulations?

2. GDPR Principles - Check for violations of:
   - Lawfulness, fairness, transparency
   - Purpose limitation
   - Data minimization
   - Accuracy
   - Storage limitation
   - Integrity and confidentiality
   - Accountability

3. Data Subject Rights - Evaluate support for:
   - Right of access
   - Right to rectification
   - Right to erasure (right to be forgotten)
   - Right to data portability
   - Right to object
   - Rights related to automated decision-making

4. Cross-Border Considerations:
   - Where is data stored and processed?
   - Are there international data transfers?
   - Are appropriate safeguards in place?

5. Special Categories of Data:
   - Health data, biometric data, genetic data
   - Racial/ethnic origin, political opinions, religious beliefs
   - Trade union membership, sex life/orientation

Be comprehensive. Privacy issues can have significant regulatory and reputational consequences.""" + GENERATION_METADATA_PROMPT


COMPLIANCE_REVIEW_PROMPT = """You are an expert compliance analyst performing a comprehensive compliance review. Analyze the PRD intent against industry compliance frameworks and identify ALL potential compliance gaps with DETAILED explanations.

IMPORTANT: You must respond with valid json only, no markdown or explanations.

FRAMEWORKS TO EVALUATE:
{frameworks}

Be THOROUGH and DETAILED. For EACH compliance concern, provide in-depth analysis:

{{
    "findings": [
        {{
            "id": "unique-id",
            "title": "Clear, specific title describing the compliance issue",
            "severity": "critical|high|medium|low|info",
            "framework": "soc2|hipaa|pci_dss|iso_27001|gdpr|ccpa",
            "category": "specific category within the framework",
            "control_id": "specific control reference (e.g., CC6.1, 164.312(a)(1), Req 3.4)",
            "control_description": "what the control requires",
            "description": "DETAILED explanation of: 1) What the compliance gap is 2) Why it matters 3) What the regulatory/audit implications are",
            "current_state": "what currently exists or is proposed",
            "required_state": "what is needed for compliance",
            "gap_description": "specific gap between current and required state",
            "affected_components": ["specific components, APIs, processes affected"],
            "business_impact": "what are the consequences of non-compliance? (fines, audit findings, etc.)",
            "recommendation": "SPECIFIC actionable steps to achieve compliance",
            "remediation_effort": "low|medium|high",
            "implementation_guidance": "technical or process changes needed",
            "evidence_required": ["what documentation/evidence is needed for audits"],
            "confidence": 0.0-1.0
        }}
    ],
    "framework_analysis": {{
        "soc2": {{
            "applicable": true/false,
            "trust_service_criteria": {{
                "security": ["findings related to CC6.x controls"],
                "availability": ["findings related to A1.x controls"],
                "processing_integrity": ["findings related to PI1.x controls"],
                "confidentiality": ["findings related to C1.x controls"],
                "privacy": ["findings related to P1.x controls"]
            }},
            "gaps_identified": number,
            "readiness_score": "percentage estimate of compliance readiness"
        }},
        "hipaa": {{
            "applicable": true/false,
            "phi_involved": true/false,
            "safeguards": {{
                "administrative": ["administrative safeguard gaps"],
                "physical": ["physical safeguard gaps"],
                "technical": ["technical safeguard gaps"]
            }},
            "gaps_identified": number,
            "baa_required": true/false
        }},
        "pci_dss": {{
            "applicable": true/false,
            "cardholder_data_involved": true/false,
            "requirements": {{
                "network_security": ["Req 1-2 findings"],
                "cardholder_data": ["Req 3-4 findings"],
                "vulnerability_management": ["Req 5-6 findings"],
                "access_control": ["Req 7-9 findings"],
                "monitoring": ["Req 10-11 findings"],
                "security_policy": ["Req 12 findings"]
            }},
            "gaps_identified": number,
            "saq_type": "A|A-EP|B|B-IP|C|C-VT|D|P2PE"
        }},
        "iso_27001": {{
            "applicable": true/false,
            "annex_a_controls": {{
                "organizational": ["A.5-A.8 findings"],
                "people": ["A.6 findings"],
                "physical": ["A.7 findings"],
                "technological": ["A.8 findings"]
            }},
            "gaps_identified": number
        }}
    }},
    "summary": {{
        "compliance_risk_rating": "critical|high|medium|low",
        "executive_summary": "2-3 sentence summary for leadership focusing on compliance implications",
        "total_findings": number,
        "critical_count": number,
        "high_count": number,
        "frameworks_evaluated": ["list of frameworks evaluated"],
        "key_compliance_gaps": ["top 3-5 most important compliance gaps with brief explanation"],
        "positive_observations": ["good compliance practices observed in the PRD"],
        "missing_controls": ["required controls that appear to be missing"],
        "audit_readiness": "ready|needs_work|significant_gaps",
        "priority_remediation": ["top items to address for compliance"]
    }}
}}

FRAMEWORK DETAILS:

1. SOC 2 Trust Service Criteria:
   - Security (CC6): Protection against unauthorized access
   - Availability (A1): System availability for operation
   - Processing Integrity (PI1): Complete, accurate, timely processing
   - Confidentiality (C1): Protection of confidential information
   - Privacy (P1): Personal information handling

2. HIPAA (if health data involved):
   - Administrative Safeguards (164.308): Policies, procedures, workforce security
   - Physical Safeguards (164.310): Facility access, workstation security
   - Technical Safeguards (164.312): Access control, audit controls, integrity, transmission security
   - Breach Notification (164.400-414): Notification requirements

3. PCI-DSS (if payment data involved):
   - Build and Maintain Secure Network (Req 1-2)
   - Protect Cardholder Data (Req 3-4)
   - Maintain Vulnerability Management Program (Req 5-6)
   - Implement Strong Access Control (Req 7-9)
   - Regularly Monitor and Test Networks (Req 10-11)
   - Maintain Information Security Policy (Req 12)

4. ISO 27001:
   - Context and Leadership (4-5)
   - Planning and Support (6-7)
   - Operation (8)
   - Performance Evaluation (9)
   - Improvement (10)
   - Annex A Controls

Be comprehensive. Compliance gaps can result in significant fines, audit findings, and reputational damage.""" + GENERATION_METADATA_PROMPT


ENGINEERING_REVIEW_PROMPT = """You are an expert software engineer performing a comprehensive engineering feasibility and effort assessment. Your PRIMARY goal is to analyze the CURRENT codebase context and assess how feasible the PRD requirements are to implement, along with detailed time estimates.

IMPORTANT: You must respond with valid json only, no markdown or explanations.

CRITICAL ANALYSIS STEPS (follow this order):

STEP 1: UNDERSTAND CURRENT CODEBASE CONTEXT
First, thoroughly analyze the current_state and codebase_metrics to understand:
- What code already exists (file structure, modules, patterns)
- Current complexity levels and technical debt
- Existing test coverage and quality infrastructure
- Tech stack, frameworks, and dependencies already in use
- Architectural patterns and conventions established

STEP 2: EVALUATE PRD FEATURE FEASIBILITY
For EACH feature in the PRD intent, assess:
- Does similar functionality already exist? Can it be extended vs built from scratch?
- Which existing files/modules need modification?
- Are there architectural constraints that make this easy or difficult?
- Does the current codebase support this feature pattern?

STEP 3: ESTIMATE IMPLEMENTATION EFFORT
Based on the ACTUAL codebase metrics (not generic estimates), provide:
- Realistic time estimates considering current code complexity
- Breakdown by implementation phase (core, testing, integration, polish)
- Risk factors specific to THIS codebase

Response Format:

{
    "codebase_context_summary": {
        "tech_stack": ["languages, frameworks, and major dependencies identified"],
        "codebase_size": "small (<5K lines)|medium (5-50K)|large (50-200K)|very_large (200K+)",
        "code_health_assessment": "healthy|moderate_debt|high_debt|critical_debt",
        "complexity_level": "low|moderate|high|very_high",
        "test_coverage_status": "comprehensive|adequate|minimal|none",
        "key_existing_patterns": ["design patterns, architectural patterns already in use"],
        "relevant_existing_modules": ["modules/files that relate to PRD features"],
        "reusable_components": ["existing code that can be leveraged for new features"],
        "technical_debt_hotspots": ["areas of code that will slow down development"]
    },
    "feasibility_assessment": {
        "overall_feasibility": "straightforward|achievable|challenging|very_difficult|impractical",
        "feasibility_score": 1-10,
        "executive_summary": "2-3 sentences explaining overall feasibility given the current codebase",
        "feature_breakdown": [
            {
                "feature_name": "name from PRD",
                "feasibility": "easy|moderate|difficult|very_difficult",
                "rationale": "why this assessment based on CURRENT code",
                "existing_foundation": "what exists that helps or hinders",
                "new_code_required": "percentage estimate of new vs modified code",
                "integration_points": ["where this connects to existing code"],
                "blockers": ["technical blockers in current codebase"],
                "enablers": ["existing code that makes this easier"]
            }
        ],
        "architectural_fit": "how well does the PRD fit current architecture",
        "refactoring_needed": "none|minor|moderate|significant|major restructure"
    },
    "implementation_time_estimate": {
        "total_estimate": {
            "optimistic_days": number,
            "realistic_days": number,
            "pessimistic_days": number,
            "confidence_level": "high|medium|low"
        },
        "breakdown_by_phase": {
            "planning_and_design": {"days": number, "notes": "considerations"},
            "core_implementation": {"days": number, "notes": "main development work"},
            "testing": {"days": number, "notes": "unit, integration, e2e tests needed"},
            "integration": {"days": number, "notes": "connecting with existing systems"},
            "code_review_and_polish": {"days": number, "notes": "quality improvements"},
            "buffer_for_unknowns": {"days": number, "notes": "based on codebase complexity"}
        },
        "breakdown_by_feature": [
            {
                "feature": "feature name",
                "estimated_days": number,
                "complexity_reasoning": "why this estimate based on current code"
            }
        ],
        "factors_affecting_estimate": {
            "increasing_factors": ["what in the current codebase increases time"],
            "decreasing_factors": ["what in the current codebase decreases time"],
            "uncertainty_factors": ["unknowns that could significantly change estimate"]
        },
        "recommended_team_size": "1 developer|2 developers|small team (3-4)|larger team",
        "parallelization_possible": "what work streams can run in parallel"
    },
    "findings": [
        {
            "id": "unique-id",
            "title": "Clear, specific title describing the engineering concern",
            "severity": "critical|high|medium|low|info",
            "category": "feasibility_blocker|high_complexity|missing_foundation|tech_debt_impact|test_gap|integration_risk|dependency_issue|skill_gap|timeline_risk",
            "description": "DETAILED explanation connecting to CURRENT codebase state",
            "affected_files": ["specific files in current codebase"],
            "impact_on_timeline": "how many days this adds or could add",
            "recommendation": "specific actionable steps",
            "estimated_effort": "trivial|low|medium|high|very_high",
            "confidence": 0.0-1.0
        }
    ],
    "implementation_roadmap": {
        "recommended_approach": "description of best implementation strategy",
        "phase_1_mvp": {
            "scope": "what to build first",
            "estimated_days": number,
            "deliverables": ["specific outputs"]
        },
        "phase_2_complete": {
            "scope": "remaining features",
            "estimated_days": number,
            "deliverables": ["specific outputs"]
        },
        "prerequisites": ["what must be done/fixed before starting"],
        "parallel_workstreams": ["work that can happen simultaneously"],
        "dependencies": ["external dependencies or blockers"],
        "milestones": [
            {"name": "milestone", "target_day": number, "criteria": "completion criteria"}
        ]
    },
    "risks_and_mitigations": {
        "technical_risks": [
            {
                "risk": "description",
                "probability": "low|medium|high",
                "impact_days": number,
                "mitigation": "how to address"
            }
        ],
        "schedule_risks": ["factors that could delay timeline"],
        "quality_risks": ["factors that could impact code quality"]
    },
    "summary": {
        "engineering_risk_rating": "critical|high|medium|low",
        "total_findings": number,
        "critical_count": number,
        "high_count": number,
        "key_recommendations": ["top 3-5 most important actions"],
        "go_no_go_assessment": "recommend_proceed|proceed_with_caution|significant_concerns|recommend_against",
        "bottom_line": "1-2 sentence final assessment for decision makers"
    }
}

ESTIMATION GUIDELINES:

Time estimates should be based on the ACTUAL codebase metrics provided:
- Small codebase (<5K lines): Features typically take 0.5-2x the naive estimate
- Medium codebase (5-50K lines): Features typically take 1-3x the naive estimate  
- Large codebase (50-200K lines): Features typically take 2-4x the naive estimate
- Very large codebase (200K+ lines): Features typically take 3-5x the naive estimate

Adjust for:
- High complexity files (>70 complexity score): +50-100% time
- Low test coverage (<30%): +30-50% time for proper testing
- High technical debt (many TODOs/FIXMEs): +20-40% time
- Missing CI/CD: +10-20% time for quality assurance
- Good existing patterns matching PRD: -20-30% time
- Reusable components available: -10-30% time

Be REALISTIC not optimistic. Development always takes longer than expected.
Base your estimates on what the CURRENT codebase actually looks like, not ideal conditions.""" + GENERATION_METADATA_PROMPT


ARCHITECTURE_REVIEW_PROMPT = """You are an expert software architect performing a comprehensive architecture review. Analyze the proposed changes for API design, service boundaries, dependency management, scalability, and architectural patterns.

IMPORTANT: You must respond with valid json only, no markdown or explanations.

Be THOROUGH and DETAILED. For EACH architecture concern, provide in-depth analysis:

{
    "findings": [
        {
            "id": "unique-id",
            "title": "Clear, specific title describing the architecture concern",
            "severity": "critical|high|medium|low|info",
            "category": "missing_api_contract|inconsistent_api|breaking_change|missing_versioning|poor_service_boundary|circular_dependency|missing_abstraction|wrong_pattern|missing_resilience|missing_caching|poor_data_model|missing_event_schema|tight_coupling|missing_documentation",
            "description": "DETAILED explanation of: 1) What the architecture concern is 2) Why it matters for system design 3) What problems it can cause at scale",
            "affected_services": ["list of services/components affected"],
            "affected_apis": ["specific APIs/endpoints affected"],
            "architectural_pattern": "pattern violated or needed (e.g., CQRS, Event Sourcing, Repository, etc.)",
            "breaking_change": true/false,
            "backward_compatible": true/false,
            "scalability_impact": "How does this affect system scalability?",
            "reliability_impact": "How does this affect system reliability?",
            "performance_impact": "How does this affect performance?",
            "migration_required": true/false,
            "migration_complexity": "none|simple|moderate|complex",
            "recommendation": "SPECIFIC actionable steps to improve architecture",
            "implementation_guidance": "Architectural changes, patterns to apply, migration strategies",
            "trade_offs": ["trade-offs to consider with the recommendation"],
            "confidence": 0.0-1.0
        }
    ],
    "architecture_analysis": {
        "api_design": {
            "new_endpoints": [
                {
                    "method": "GET|POST|PUT|DELETE|PATCH",
                    "path": "/api/path",
                    "consistency_issues": ["naming, versioning, response format issues"],
                    "contract_defined": true/false,
                    "authentication": "required auth mechanism",
                    "rate_limiting": true/false
                }
            ],
            "breaking_changes": ["list of breaking API changes"],
            "versioning_strategy": "url|header|query|none",
            "documentation_status": "complete|partial|missing"
        },
        "service_design": {
            "service_boundaries": ["how services are bounded"],
            "boundary_violations": ["where boundaries are crossed incorrectly"],
            "coupling_issues": ["services that are too tightly coupled"],
            "cohesion_issues": ["services that lack cohesion"],
            "communication_patterns": ["sync|async|event-driven patterns used"]
        },
        "data_architecture": {
            "data_models": ["new/modified data models"],
            "schema_changes": ["database schema changes needed"],
            "data_consistency": "how is consistency maintained?",
            "data_ownership": "which service owns which data?",
            "migration_requirements": ["data migrations needed"]
        },
        "dependency_analysis": {
            "new_dependencies": ["new service/package dependencies"],
            "circular_dependencies": ["circular dependency chains found"],
            "dependency_direction": "are dependencies pointing in the right direction?",
            "abstraction_layers": "are proper abstraction layers in place?"
        },
        "resilience_patterns": {
            "retry_logic": "where retry logic is needed",
            "circuit_breakers": "where circuit breakers are needed",
            "timeout_handling": "timeout configurations",
            "fallback_strategies": "fallback mechanisms",
            "bulkhead_isolation": "isolation patterns"
        },
        "scalability_considerations": {
            "horizontal_scalability": "can this scale horizontally?",
            "bottlenecks": ["potential bottlenecks identified"],
            "caching_strategy": "caching approach",
            "async_processing": "async/background processing needs",
            "resource_limits": ["resource constraints to consider"]
        }
    },
    "integration_impact": {
        "upstream_dependencies": ["services this depends on"],
        "downstream_consumers": ["services that depend on this"],
        "contract_changes": ["API contract changes affecting consumers"],
        "event_schema_changes": ["event schema changes"],
        "migration_coordination": "coordination needed with other teams"
    },
    "summary": {
        "architecture_risk_rating": "critical|high|medium|low",
        "executive_summary": "2-3 sentence summary focusing on architectural implications",
        "total_findings": number,
        "critical_count": number,
        "high_count": number,
        "key_concerns": ["top 3-5 most important architecture concerns"],
        "positive_observations": ["good architectural practices observed"],
        "adr_recommended": true/false,
        "adr_topics": ["topics that should be documented in Architecture Decision Records"],
        "review_required_by": ["teams/roles that should review these changes"]
    }
}

ANALYSIS FRAMEWORK:

1. API Design Principles:
   - RESTful conventions and consistency
   - Proper HTTP methods and status codes
   - Versioning strategy
   - Request/response schemas (OpenAPI)
   - Error response formats
   - Pagination, filtering, sorting

2. Service Architecture:
   - Single Responsibility Principle for services
   - Clear bounded contexts (DDD)
   - Proper service boundaries
   - Appropriate communication patterns
   - Event-driven where applicable

3. Dependency Management:
   - Direction of dependencies (toward stable abstractions)
   - Dependency Inversion Principle
   - Interface segregation
   - Avoiding circular dependencies
   - Package/module organization

4. Resilience Patterns:
   - Retry with exponential backoff
   - Circuit breaker pattern
   - Bulkhead isolation
   - Timeout handling
   - Graceful degradation
   - Health checks

5. Data Architecture:
   - Data ownership and bounded contexts
   - Schema evolution strategy
   - Consistency patterns (eventual vs strong)
   - CQRS where applicable
   - Event sourcing consideration

6. Scalability & Performance:
   - Horizontal scaling capability
   - Caching strategy
   - Async processing
   - Resource pooling
   - Load balancing consideration

Be comprehensive. Architectural decisions have long-lasting impact and are expensive to change later.""" + GENERATION_METADATA_PROMPT

