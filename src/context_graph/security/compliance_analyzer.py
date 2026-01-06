"""
Compliance Analyzer - Multi-framework compliance gap analysis.

Implements:
- SOC 2 Trust Service Criteria
- HIPAA safeguards
- PCI-DSS requirements
- ISO 27001 controls
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from context_graph.core.models import (
    ComplianceFinding,
    ComplianceCategory,
    ComplianceFramework,
    Severity,
    ReviewDimension,
)
from context_graph.security.delta_analyzer import DeltaAnalysisResult


@dataclass
class ComplianceControl:
    """A compliance control requirement."""
    
    id: str
    name: str
    description: str
    framework: ComplianceFramework
    category: ComplianceCategory
    severity: Severity = Severity.MEDIUM
    
    # Control requirements
    requirement_text: str = ""
    
    # Matching conditions
    requires_authentication: bool = False
    requires_encryption: bool = False
    requires_logging: bool = False
    requires_access_control: bool = False
    requires_data_handling: bool = False
    requires_phi: bool = False
    requires_payment_data: bool = False
    requires_network_boundary: bool = False
    
    # Evidence requirements
    evidence_required: list[str] = field(default_factory=list)
    
    # Remediation
    recommendation: str = ""
    remediation_effort: str = "medium"  # low, medium, high


# SOC 2 Controls
SOC2_CONTROLS = [
    # Security (CC6)
    ComplianceControl(
        id="CC6.1",
        name="Logical and Physical Access Controls",
        description="System access is restricted to authorized users",
        framework=ComplianceFramework.SOC2,
        category=ComplianceCategory.SOC2_SECURITY,
        severity=Severity.HIGH,
        requirement_text="The entity implements logical access security software, infrastructure, and architectures over protected information assets",
        requires_access_control=True,
        evidence_required=["Access control policy", "User provisioning records", "Access reviews"],
        recommendation="Implement role-based access control with principle of least privilege",
        remediation_effort="medium",
    ),
    ComplianceControl(
        id="CC6.2",
        name="User Registration and Authorization",
        description="New users are registered and authorized before access is granted",
        framework=ComplianceFramework.SOC2,
        category=ComplianceCategory.SOC2_SECURITY,
        severity=Severity.HIGH,
        requirement_text="Prior to issuing system credentials and granting system access, the entity registers and authorizes new internal and external users",
        requires_authentication=True,
        evidence_required=["User registration process", "Authorization workflow", "Access request approvals"],
        recommendation="Implement formal user registration and authorization process",
        remediation_effort="medium",
    ),
    ComplianceControl(
        id="CC6.3",
        name="User Removal",
        description="System credentials are removed when no longer needed",
        framework=ComplianceFramework.SOC2,
        category=ComplianceCategory.SOC2_SECURITY,
        severity=Severity.MEDIUM,
        requirement_text="The entity removes credentials and access upon termination or role change",
        requires_access_control=True,
        evidence_required=["Offboarding process", "Access removal evidence", "Termination checklist"],
        recommendation="Implement automated access removal on termination/role change",
        remediation_effort="medium",
    ),
    ComplianceControl(
        id="CC6.6",
        name="System Boundaries",
        description="System boundaries are established and maintained",
        framework=ComplianceFramework.SOC2,
        category=ComplianceCategory.SOC2_SECURITY,
        severity=Severity.HIGH,
        requirement_text="The entity implements controls to restrict access at system boundaries",
        requires_network_boundary=True,
        evidence_required=["Network diagram", "Firewall rules", "Boundary protection documentation"],
        recommendation="Define and document system boundaries with appropriate controls",
        remediation_effort="high",
    ),
    ComplianceControl(
        id="CC6.7",
        name="Data Transmission Protection",
        description="Data in transit is protected",
        framework=ComplianceFramework.SOC2,
        category=ComplianceCategory.SOC2_SECURITY,
        severity=Severity.HIGH,
        requirement_text="The entity restricts the transmission, movement, and removal of information to authorized internal and external users",
        requires_encryption=True,
        evidence_required=["Encryption policy", "TLS configuration", "Data transmission controls"],
        recommendation="Implement TLS 1.2+ for all data transmission",
        remediation_effort="medium",
    ),
    
    # Availability (A1)
    ComplianceControl(
        id="A1.1",
        name="Capacity Management",
        description="System capacity is maintained to meet availability requirements",
        framework=ComplianceFramework.SOC2,
        category=ComplianceCategory.SOC2_AVAILABILITY,
        severity=Severity.MEDIUM,
        requirement_text="The entity maintains, monitors, and evaluates current processing capacity and use",
        evidence_required=["Capacity planning documentation", "Monitoring dashboards", "Scaling procedures"],
        recommendation="Implement capacity monitoring and auto-scaling",
        remediation_effort="medium",
    ),
    ComplianceControl(
        id="A1.2",
        name="Recovery and Continuity",
        description="Business continuity and disaster recovery plans are in place",
        framework=ComplianceFramework.SOC2,
        category=ComplianceCategory.SOC2_AVAILABILITY,
        severity=Severity.HIGH,
        evidence_required=["DR plan", "BCP documentation", "Recovery test results"],
        recommendation="Implement and test disaster recovery procedures",
        remediation_effort="high",
    ),
    
    # Confidentiality (C1)
    ComplianceControl(
        id="C1.1",
        name="Confidential Information Identification",
        description="Confidential information is identified and classified",
        framework=ComplianceFramework.SOC2,
        category=ComplianceCategory.SOC2_CONFIDENTIALITY,
        severity=Severity.MEDIUM,
        requirement_text="Confidential information is identified and classified",
        requires_data_handling=True,
        evidence_required=["Data classification policy", "Data inventory", "Classification labels"],
        recommendation="Implement data classification scheme and apply to all data",
        remediation_effort="medium",
    ),
    ComplianceControl(
        id="C1.2",
        name="Confidential Data Disposal",
        description="Confidential data is securely disposed when no longer needed",
        framework=ComplianceFramework.SOC2,
        category=ComplianceCategory.SOC2_CONFIDENTIALITY,
        severity=Severity.MEDIUM,
        requires_data_handling=True,
        evidence_required=["Data retention policy", "Disposal procedures", "Disposal logs"],
        recommendation="Implement secure data disposal procedures",
        remediation_effort="medium",
    ),
    
    # Processing Integrity (PI1)
    ComplianceControl(
        id="PI1.1",
        name="Data Processing Accuracy",
        description="Data processing is complete, accurate, and timely",
        framework=ComplianceFramework.SOC2,
        category=ComplianceCategory.SOC2_PROCESSING_INTEGRITY,
        severity=Severity.MEDIUM,
        evidence_required=["Data validation procedures", "Error handling documentation", "Processing logs"],
        recommendation="Implement input validation and processing verification",
        remediation_effort="medium",
    ),
]

# HIPAA Controls
HIPAA_CONTROLS = [
    # Administrative Safeguards (164.308)
    ComplianceControl(
        id="164.308(a)(1)",
        name="Security Management Process",
        description="Implement policies and procedures to prevent, detect, contain, and correct security violations",
        framework=ComplianceFramework.HIPAA,
        category=ComplianceCategory.HIPAA_ACCESS_CONTROL,
        severity=Severity.HIGH,
        requires_phi=True,
        evidence_required=["Risk analysis", "Risk management plan", "Security policies"],
        recommendation="Conduct regular risk assessments and maintain security policies",
        remediation_effort="high",
    ),
    ComplianceControl(
        id="164.308(a)(3)",
        name="Workforce Security",
        description="Implement policies to ensure appropriate access to ePHI",
        framework=ComplianceFramework.HIPAA,
        category=ComplianceCategory.HIPAA_ACCESS_CONTROL,
        severity=Severity.HIGH,
        requires_phi=True,
        requires_access_control=True,
        evidence_required=["Workforce clearance procedures", "Access authorization", "Termination procedures"],
        recommendation="Implement workforce security policies with access authorization",
        remediation_effort="medium",
    ),
    ComplianceControl(
        id="164.308(a)(4)",
        name="Information Access Management",
        description="Implement policies for authorizing access to ePHI",
        framework=ComplianceFramework.HIPAA,
        category=ComplianceCategory.HIPAA_ACCESS_CONTROL,
        severity=Severity.HIGH,
        requires_phi=True,
        requires_access_control=True,
        evidence_required=["Access policies", "Isolation procedures", "Access reviews"],
        recommendation="Implement role-based access control for ePHI",
        remediation_effort="medium",
    ),
    ComplianceControl(
        id="164.308(a)(5)",
        name="Security Awareness Training",
        description="Implement security awareness and training program",
        framework=ComplianceFramework.HIPAA,
        category=ComplianceCategory.HIPAA_ACCESS_CONTROL,
        severity=Severity.MEDIUM,
        requires_phi=True,
        evidence_required=["Training program", "Training records", "Security reminders"],
        recommendation="Implement security awareness training program",
        remediation_effort="medium",
    ),
    
    # Technical Safeguards (164.312)
    ComplianceControl(
        id="164.312(a)(1)",
        name="Access Control",
        description="Implement technical policies to allow access only to authorized persons",
        framework=ComplianceFramework.HIPAA,
        category=ComplianceCategory.HIPAA_ACCESS_CONTROL,
        severity=Severity.CRITICAL,
        requires_phi=True,
        requires_access_control=True,
        requires_authentication=True,
        evidence_required=["Unique user identification", "Emergency access procedure", "Automatic logoff", "Encryption"],
        recommendation="Implement unique user IDs, automatic logoff, and encryption for ePHI access",
        remediation_effort="high",
    ),
    ComplianceControl(
        id="164.312(b)",
        name="Audit Controls",
        description="Implement hardware, software, and procedures to record and examine access",
        framework=ComplianceFramework.HIPAA,
        category=ComplianceCategory.HIPAA_AUDIT_LOGGING,
        severity=Severity.HIGH,
        requires_phi=True,
        requires_logging=True,
        evidence_required=["Audit logs", "Log review procedures", "Monitoring tools"],
        recommendation="Implement comprehensive audit logging for all ePHI access",
        remediation_effort="medium",
    ),
    ComplianceControl(
        id="164.312(c)(1)",
        name="Integrity Controls",
        description="Implement policies to protect ePHI from improper alteration or destruction",
        framework=ComplianceFramework.HIPAA,
        category=ComplianceCategory.HIPAA_PHI_HANDLING,
        severity=Severity.HIGH,
        requires_phi=True,
        evidence_required=["Integrity verification", "Data validation procedures"],
        recommendation="Implement data integrity controls and verification mechanisms",
        remediation_effort="medium",
    ),
    ComplianceControl(
        id="164.312(d)",
        name="Person or Entity Authentication",
        description="Implement procedures to verify identity before granting access",
        framework=ComplianceFramework.HIPAA,
        category=ComplianceCategory.HIPAA_ACCESS_CONTROL,
        severity=Severity.CRITICAL,
        requires_phi=True,
        requires_authentication=True,
        evidence_required=["Authentication procedures", "MFA implementation"],
        recommendation="Implement multi-factor authentication for ePHI access",
        remediation_effort="medium",
    ),
    ComplianceControl(
        id="164.312(e)(1)",
        name="Transmission Security",
        description="Implement measures to guard against unauthorized access during transmission",
        framework=ComplianceFramework.HIPAA,
        category=ComplianceCategory.HIPAA_ENCRYPTION,
        severity=Severity.CRITICAL,
        requires_phi=True,
        requires_encryption=True,
        evidence_required=["Encryption policy", "TLS configuration", "VPN documentation"],
        recommendation="Implement encryption for all ePHI transmission",
        remediation_effort="medium",
    ),
]

# PCI-DSS Controls
PCI_DSS_CONTROLS = [
    # Requirement 1-2: Network Security
    ComplianceControl(
        id="Req 1.1",
        name="Firewall Configuration",
        description="Install and maintain network security controls",
        framework=ComplianceFramework.PCI_DSS,
        category=ComplianceCategory.PCI_NETWORK_SECURITY,
        severity=Severity.HIGH,
        requires_payment_data=True,
        requires_network_boundary=True,
        evidence_required=["Firewall rules", "Network diagram", "Change management records"],
        recommendation="Implement and document firewall configuration standards",
        remediation_effort="high",
    ),
    ComplianceControl(
        id="Req 2.1",
        name="Secure Configurations",
        description="Apply secure configurations to all system components",
        framework=ComplianceFramework.PCI_DSS,
        category=ComplianceCategory.PCI_NETWORK_SECURITY,
        severity=Severity.HIGH,
        requires_payment_data=True,
        evidence_required=["Hardening standards", "Configuration baseline", "Compliance scan results"],
        recommendation="Implement configuration hardening standards",
        remediation_effort="medium",
    ),
    
    # Requirement 3-4: Cardholder Data Protection
    ComplianceControl(
        id="Req 3.1",
        name="Data Storage Minimization",
        description="Keep cardholder data storage to a minimum",
        framework=ComplianceFramework.PCI_DSS,
        category=ComplianceCategory.PCI_CARDHOLDER_DATA,
        severity=Severity.CRITICAL,
        requires_payment_data=True,
        requires_data_handling=True,
        evidence_required=["Data retention policy", "Data flow diagram", "Data inventory"],
        recommendation="Minimize storage of cardholder data and implement retention policies",
        remediation_effort="high",
    ),
    ComplianceControl(
        id="Req 3.4",
        name="PAN Protection",
        description="Render PAN unreadable anywhere it is stored",
        framework=ComplianceFramework.PCI_DSS,
        category=ComplianceCategory.PCI_CARDHOLDER_DATA,
        severity=Severity.CRITICAL,
        requires_payment_data=True,
        requires_encryption=True,
        evidence_required=["Encryption implementation", "Key management procedures", "Tokenization documentation"],
        recommendation="Implement strong encryption or tokenization for stored PAN",
        remediation_effort="high",
    ),
    ComplianceControl(
        id="Req 4.1",
        name="Transmission Encryption",
        description="Protect cardholder data during transmission over open networks",
        framework=ComplianceFramework.PCI_DSS,
        category=ComplianceCategory.PCI_CARDHOLDER_DATA,
        severity=Severity.CRITICAL,
        requires_payment_data=True,
        requires_encryption=True,
        evidence_required=["TLS configuration", "Certificate management", "Network diagram"],
        recommendation="Use strong cryptography for cardholder data transmission",
        remediation_effort="medium",
    ),
    
    # Requirement 7-9: Access Control
    ComplianceControl(
        id="Req 7.1",
        name="Access Restriction",
        description="Limit access to system components to individuals whose job requires it",
        framework=ComplianceFramework.PCI_DSS,
        category=ComplianceCategory.PCI_ACCESS_CONTROL,
        severity=Severity.HIGH,
        requires_payment_data=True,
        requires_access_control=True,
        evidence_required=["Access control policy", "Role definitions", "Access reviews"],
        recommendation="Implement role-based access control with need-to-know principle",
        remediation_effort="medium",
    ),
    ComplianceControl(
        id="Req 8.1",
        name="User Identification",
        description="Identify users and authenticate access to system components",
        framework=ComplianceFramework.PCI_DSS,
        category=ComplianceCategory.PCI_ACCESS_CONTROL,
        severity=Severity.HIGH,
        requires_payment_data=True,
        requires_authentication=True,
        evidence_required=["User management procedures", "Authentication standards", "Password policy"],
        recommendation="Implement unique user IDs and strong authentication",
        remediation_effort="medium",
    ),
    
    # Requirement 10-11: Monitoring
    ComplianceControl(
        id="Req 10.1",
        name="Audit Logging",
        description="Log and monitor all access to cardholder data and network resources",
        framework=ComplianceFramework.PCI_DSS,
        category=ComplianceCategory.PCI_MONITORING,
        severity=Severity.HIGH,
        requires_payment_data=True,
        requires_logging=True,
        evidence_required=["Audit logging configuration", "Log retention policy", "Log review procedures"],
        recommendation="Implement comprehensive audit logging for all CDE access",
        remediation_effort="medium",
    ),
    ComplianceControl(
        id="Req 11.3",
        name="Vulnerability Management",
        description="Perform internal and external vulnerability scans",
        framework=ComplianceFramework.PCI_DSS,
        category=ComplianceCategory.PCI_MONITORING,
        severity=Severity.HIGH,
        requires_payment_data=True,
        evidence_required=["Vulnerability scan reports", "Penetration test reports", "Remediation evidence"],
        recommendation="Implement regular vulnerability scanning and penetration testing",
        remediation_effort="high",
    ),
]

# ISO 27001 Controls
ISO_27001_CONTROLS = [
    ComplianceControl(
        id="A.5.1",
        name="Information Security Policies",
        description="Policies for information security shall be defined and approved",
        framework=ComplianceFramework.ISO_27001,
        category=ComplianceCategory.ISO_INFORMATION_SECURITY,
        severity=Severity.MEDIUM,
        evidence_required=["Information security policy", "Policy review records"],
        recommendation="Establish and maintain information security policies",
        remediation_effort="medium",
    ),
    ComplianceControl(
        id="A.6.1",
        name="Access Control Policy",
        description="An access control policy shall be established based on business requirements",
        framework=ComplianceFramework.ISO_27001,
        category=ComplianceCategory.ISO_ACCESS_MANAGEMENT,
        severity=Severity.HIGH,
        requires_access_control=True,
        evidence_required=["Access control policy", "Access review records", "User provisioning procedures"],
        recommendation="Implement formal access control policy and procedures",
        remediation_effort="medium",
    ),
    ComplianceControl(
        id="A.8.2",
        name="Cryptographic Controls",
        description="A policy on use of cryptographic controls shall be developed",
        framework=ComplianceFramework.ISO_27001,
        category=ComplianceCategory.ISO_CRYPTOGRAPHY,
        severity=Severity.HIGH,
        requires_encryption=True,
        evidence_required=["Cryptography policy", "Key management procedures", "Encryption standards"],
        recommendation="Implement cryptographic policy and key management",
        remediation_effort="medium",
    ),
    ComplianceControl(
        id="A.8.8",
        name="Technical Vulnerability Management",
        description="Information about technical vulnerabilities shall be obtained and evaluated",
        framework=ComplianceFramework.ISO_27001,
        category=ComplianceCategory.ISO_OPERATIONS_SECURITY,
        severity=Severity.HIGH,
        evidence_required=["Vulnerability management process", "Patch management", "Vulnerability reports"],
        recommendation="Implement vulnerability management program",
        remediation_effort="medium",
    ),
    ComplianceControl(
        id="A.8.15",
        name="Logging",
        description="Logs that record activities shall be produced and protected",
        framework=ComplianceFramework.ISO_27001,
        category=ComplianceCategory.ISO_OPERATIONS_SECURITY,
        severity=Severity.MEDIUM,
        requires_logging=True,
        evidence_required=["Logging policy", "Log management procedures", "Log protection measures"],
        recommendation="Implement comprehensive logging with protection",
        remediation_effort="medium",
    ),
    ComplianceControl(
        id="A.5.24",
        name="Information Security Incident Management",
        description="A consistent approach to management of information security incidents",
        framework=ComplianceFramework.ISO_27001,
        category=ComplianceCategory.ISO_INCIDENT_MANAGEMENT,
        severity=Severity.HIGH,
        evidence_required=["Incident response plan", "Incident records", "Post-incident reviews"],
        recommendation="Establish incident response procedures",
        remediation_effort="high",
    ),
]


class CompliancePatternMatcher:
    """
    Matches compliance controls against delta analysis results.
    """
    
    def __init__(
        self, 
        frameworks: list[ComplianceFramework] | None = None,
    ) -> None:
        # Default to common frameworks
        self.frameworks = frameworks or [
            ComplianceFramework.SOC2,
            ComplianceFramework.HIPAA,
            ComplianceFramework.PCI_DSS,
        ]
        
        # Build control registry based on selected frameworks
        self.controls: list[ComplianceControl] = []
        if ComplianceFramework.SOC2 in self.frameworks:
            self.controls.extend(SOC2_CONTROLS)
        if ComplianceFramework.HIPAA in self.frameworks:
            self.controls.extend(HIPAA_CONTROLS)
        if ComplianceFramework.PCI_DSS in self.frameworks:
            self.controls.extend(PCI_DSS_CONTROLS)
        if ComplianceFramework.ISO_27001 in self.frameworks:
            self.controls.extend(ISO_27001_CONTROLS)
        
        # Data type indicators
        self.phi_indicators = {
            "health", "medical", "diagnosis", "treatment", "prescription",
            "patient", "healthcare", "hipaa", "phi", "ephi", "clinical",
        }
        
        self.payment_indicators = {
            "card", "credit", "debit", "payment", "pan", "cvv", "expiry",
            "cardholder", "pci", "stripe", "merchant", "transaction",
        }
    
    def match(self, delta_result: DeltaAnalysisResult) -> list[ComplianceFinding]:
        """
        Match controls against delta and generate compliance findings.
        
        Args:
            delta_result: The delta analysis result
            
        Returns:
            List of compliance findings
        """
        findings: list[ComplianceFinding] = []
        
        # Analyze delta for compliance-relevant information
        has_phi = self._check_phi_presence(delta_result)
        has_payment_data = self._check_payment_data(delta_result)
        has_authentication = self._check_authentication(delta_result)
        has_encryption = self._check_encryption_needs(delta_result)
        has_logging = self._check_logging_needs(delta_result)
        has_access_control = self._check_access_control(delta_result)
        has_data_handling = bool(delta_result.new_data_models)
        has_network_boundary = self._check_network_boundary(delta_result)
        
        # Match controls
        for control in self.controls:
            if self._control_applies(
                control,
                has_phi,
                has_payment_data,
                has_authentication,
                has_encryption,
                has_logging,
                has_access_control,
                has_data_handling,
                has_network_boundary,
                delta_result,
            ):
                finding = self._create_finding(control, delta_result)
                findings.append(finding)
        
        # Deduplicate and sort
        findings = self._deduplicate_findings(findings)
        findings = self._sort_by_severity(findings)
        
        return findings
    
    def _check_phi_presence(self, delta: DeltaAnalysisResult) -> bool:
        """Check if delta involves PHI (Protected Health Information)."""
        for model in delta.new_data_models:
            model_name = model.get("name", "").lower()
            if any(indicator in model_name for indicator in self.phi_indicators):
                return True
            
            fields = model.get("fields", [])
            for field_info in fields:
                field_name = field_info.get("name", "").lower() if isinstance(field_info, dict) else str(field_info).lower()
                if any(indicator in field_name for indicator in self.phi_indicators):
                    return True
        
        for boundary in delta.trust_boundary_impacts:
            if any(indicator in boundary.lower() for indicator in self.phi_indicators):
                return True
        
        return False
    
    def _check_payment_data(self, delta: DeltaAnalysisResult) -> bool:
        """Check if delta involves payment/cardholder data."""
        for model in delta.new_data_models:
            model_name = model.get("name", "").lower()
            if any(indicator in model_name for indicator in self.payment_indicators):
                return True
            
            fields = model.get("fields", [])
            for field_info in fields:
                field_name = field_info.get("name", "").lower() if isinstance(field_info, dict) else str(field_info).lower()
                if any(indicator in field_name for indicator in self.payment_indicators):
                    return True
        
        for boundary in delta.trust_boundary_impacts:
            if any(indicator in boundary.lower() for indicator in self.payment_indicators):
                return True
        
        return False
    
    def _check_authentication(self, delta: DeltaAnalysisResult) -> bool:
        """Check if delta involves authentication."""
        return delta.modifies_auth_flow or any(
            "auth" in ep.get("path", "").lower() or
            "login" in ep.get("path", "").lower() or
            "session" in ep.get("path", "").lower()
            for ep in delta.new_endpoints
        )
    
    def _check_encryption_needs(self, delta: DeltaAnalysisResult) -> bool:
        """Check if delta introduces encryption requirements."""
        # New endpoints or data models typically need encryption
        return bool(delta.new_endpoints or delta.new_data_models) or delta.introduces_pii
    
    def _check_logging_needs(self, delta: DeltaAnalysisResult) -> bool:
        """Check if delta introduces logging requirements."""
        # Any new functionality needs logging
        return bool(delta.new_endpoints)
    
    def _check_access_control(self, delta: DeltaAnalysisResult) -> bool:
        """Check if delta involves access control."""
        return bool(delta.auth_requirement_changes) or delta.modifies_auth_flow
    
    def _check_network_boundary(self, delta: DeltaAnalysisResult) -> bool:
        """Check if delta crosses network boundaries."""
        return bool(delta.trust_boundary_impacts) or delta.introduces_external_integration
    
    def _control_applies(
        self,
        control: ComplianceControl,
        has_phi: bool,
        has_payment_data: bool,
        has_authentication: bool,
        has_encryption: bool,
        has_logging: bool,
        has_access_control: bool,
        has_data_handling: bool,
        has_network_boundary: bool,
        delta: DeltaAnalysisResult,
    ) -> bool:
        """Check if a control applies to the delta."""
        # Check framework-specific requirements
        if control.requires_phi and not has_phi:
            return False
        
        if control.requires_payment_data and not has_payment_data:
            return False
        
        # For non-PHI/payment specific controls, check other conditions
        if not control.requires_phi and not control.requires_payment_data:
            # At least one condition must match
            conditions_met = False
            
            if control.requires_authentication and has_authentication:
                conditions_met = True
            if control.requires_encryption and has_encryption:
                conditions_met = True
            if control.requires_logging and has_logging:
                conditions_met = True
            if control.requires_access_control and has_access_control:
                conditions_met = True
            if control.requires_data_handling and has_data_handling:
                conditions_met = True
            if control.requires_network_boundary and has_network_boundary:
                conditions_met = True
            
            # If control has specific requirements but none are met, skip
            has_requirements = any([
                control.requires_authentication,
                control.requires_encryption,
                control.requires_logging,
                control.requires_access_control,
                control.requires_data_handling,
                control.requires_network_boundary,
            ])
            
            if has_requirements and not conditions_met:
                return False
        
        return True
    
    def _create_finding(
        self,
        control: ComplianceControl,
        delta: DeltaAnalysisResult,
    ) -> ComplianceFinding:
        """Create a compliance finding from a matched control."""
        # Determine current state
        current_state = "Not explicitly addressed in PRD"
        
        # Check for relevant existing controls
        for existing in delta.delta.affected_components:
            if any(keyword in existing.lower() for keyword in ["auth", "encrypt", "log", "access"]):
                current_state = f"Existing control: {existing}"
                break
        
        # Determine gap
        gap_description = f"Control {control.id} requirements may not be fully addressed"
        if control.requires_phi:
            gap_description = "PHI handling requires specific safeguards as per HIPAA"
        elif control.requires_payment_data:
            gap_description = "Cardholder data handling requires PCI-DSS compliance"
        
        return ComplianceFinding(
            id=uuid4(),
            title=control.name,
            description=control.description,
            severity=control.severity,
            category=control.category,
            dimension=ReviewDimension.COMPLIANCE,
            framework=control.framework,
            control_id=control.id,
            control_description=control.description,
            requirement_text=control.requirement_text,
            current_state=current_state,
            required_state=control.requirement_text,
            gap_description=gap_description,
            source_type="pattern",
            source_reference=f"control:{control.id}",
            recommendation=control.recommendation,
            mitigations=control.evidence_required,
            remediation_effort=control.remediation_effort,
            confidence=0.7,
        )
    
    def _deduplicate_findings(self, findings: list[ComplianceFinding]) -> list[ComplianceFinding]:
        """Remove duplicate findings."""
        seen_keys: set[str] = set()
        unique_findings: list[ComplianceFinding] = []
        
        for finding in findings:
            key = f"{finding.framework}:{finding.control_id}"
            if key not in seen_keys:
                seen_keys.add(key)
                unique_findings.append(finding)
        
        return unique_findings
    
    def _sort_by_severity(self, findings: list[ComplianceFinding]) -> list[ComplianceFinding]:
        """Sort findings by severity and framework."""
        severity_order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
            Severity.INFO: 4,
        }
        findings.sort(key=lambda f: (severity_order.get(f.severity, 5), f.framework.value))
        return findings
    
    def get_framework_summary(self, findings: list[ComplianceFinding]) -> dict[str, Any]:
        """Generate summary by framework."""
        summary: dict[str, Any] = {}
        
        for framework in self.frameworks:
            framework_findings = [f for f in findings if f.framework == framework]
            summary[framework.value] = {
                "total_findings": len(framework_findings),
                "critical": sum(1 for f in framework_findings if f.severity == Severity.CRITICAL),
                "high": sum(1 for f in framework_findings if f.severity == Severity.HIGH),
                "medium": sum(1 for f in framework_findings if f.severity == Severity.MEDIUM),
                "low": sum(1 for f in framework_findings if f.severity == Severity.LOW),
                "categories": list(set(f.category.value for f in framework_findings)),
            }
        
        return summary

