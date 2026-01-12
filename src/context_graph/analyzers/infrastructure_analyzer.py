"""
Infrastructure Analyzer - Analyze Infrastructure-as-Code files.

Identifies:
- Terraform configurations
- Docker/Container configurations
- Kubernetes manifests
- CloudFormation templates
- Ansible playbooks
- Helm charts
- Security misconfigurations in infrastructure
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from context_graph.core.models import Entity, EntityType, Relationship, RelationshipType
from context_graph.analyzers.codebase_analyzer import CodebaseAnalyzer, FileAnalysis


@dataclass
class InfrastructureMetrics:
    """Metrics from infrastructure analysis."""
    
    terraform_files: int = 0
    docker_files: int = 0
    kubernetes_manifests: int = 0
    cloudformation_templates: int = 0
    ansible_files: int = 0
    helm_charts: int = 0
    resources_defined: int = 0
    secrets_in_iac: int = 0
    security_groups: int = 0
    iam_policies: int = 0


class InfrastructureAnalyzer(CodebaseAnalyzer):
    """
    Analyze Infrastructure-as-Code files for security patterns.
    
    Supports:
    - Terraform (.tf, .tfvars)
    - Docker (Dockerfile, docker-compose.yml)
    - Kubernetes (.yaml, .yml with k8s patterns)
    - CloudFormation (.yaml, .json with CF patterns)
    - Ansible (.yaml, .yml with ansible patterns)
    - Helm (Chart.yaml, values.yaml)
    """
    
    def __init__(
        self,
        exclude_patterns: list[str] | None = None,
    ) -> None:
        super().__init__(exclude_patterns)
        self.metrics = InfrastructureMetrics()
    
    def supported_extensions(self) -> list[str]:
        return [".tf", ".tfvars", ".yaml", ".yml", ".json"]
    
    def analyze_file(self, file_path: Path) -> FileAnalysis:
        """Analyze an infrastructure file."""
        file_name = file_path.name.lower()
        
        # Handle Dockerfiles separately (no extension)
        if "dockerfile" in file_name:
            return self._analyze_dockerfile(file_path)
        
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return FileAnalysis(path=file_path, language="unknown")
        
        analysis = FileAnalysis(
            path=file_path,
            language=self._detect_iac_type(file_path, content),
            lines_of_code=len(content.split("\n")),
        )
        
        # Route to appropriate analyzer
        if file_path.suffix in [".tf", ".tfvars"]:
            self._analyze_terraform(content, file_path, analysis)
        elif self._is_kubernetes_manifest(file_path, content):
            self._analyze_kubernetes(content, file_path, analysis)
        elif self._is_cloudformation(content):
            self._analyze_cloudformation(content, file_path, analysis)
        elif self._is_ansible(file_path, content):
            self._analyze_ansible(content, file_path, analysis)
        elif self._is_helm(file_path):
            self._analyze_helm(content, file_path, analysis)
        elif self._is_docker_compose(file_path, content):
            self._analyze_docker_compose(content, file_path, analysis)
        
        return analysis
    
    def _detect_iac_type(self, file_path: Path, content: str) -> str:
        """Detect the type of IaC file."""
        if file_path.suffix in [".tf", ".tfvars"]:
            return "terraform"
        if "dockerfile" in file_path.name.lower():
            return "docker"
        if self._is_kubernetes_manifest(file_path, content):
            return "kubernetes"
        if self._is_cloudformation(content):
            return "cloudformation"
        if self._is_ansible(file_path, content):
            return "ansible"
        if self._is_helm(file_path):
            return "helm"
        if self._is_docker_compose(file_path, content):
            return "docker-compose"
        return "yaml"
    
    def _is_kubernetes_manifest(self, file_path: Path, content: str) -> bool:
        """Check if file is a Kubernetes manifest."""
        k8s_indicators = [
            "apiVersion:", "kind:", "metadata:", "spec:",
            "kubernetes.io", "k8s.io",
        ]
        k8s_kinds = [
            "Deployment", "Service", "Pod", "ConfigMap", "Secret",
            "Ingress", "StatefulSet", "DaemonSet", "Job", "CronJob",
            "PersistentVolumeClaim", "NetworkPolicy", "ServiceAccount",
        ]
        
        # Check for k8s directory patterns
        path_indicators = ["k8s/", "kubernetes/", "manifests/", "deploy/"]
        if any(p in str(file_path).lower() for p in path_indicators):
            return True
        
        # Check content
        has_api_version = "apiVersion:" in content
        has_kind = any(f"kind: {k}" in content for k in k8s_kinds)
        
        return has_api_version and has_kind
    
    def _is_cloudformation(self, content: str) -> bool:
        """Check if content is CloudFormation template."""
        cf_indicators = [
            "AWSTemplateFormatVersion",
            "AWS::", 
            "Resources:",
            "Fn::Ref",
            "!Ref",
            "!GetAtt",
        ]
        return sum(1 for i in cf_indicators if i in content) >= 2
    
    def _is_ansible(self, file_path: Path, content: str) -> bool:
        """Check if file is an Ansible playbook/role."""
        path_indicators = [
            "ansible/", "playbooks/", "roles/", 
            "tasks/", "handlers/", "vars/",
        ]
        if any(p in str(file_path).lower() for p in path_indicators):
            return True
        
        ansible_indicators = [
            "hosts:", "tasks:", "become:", "ansible.",
            "- name:", "register:", "when:",
        ]
        return sum(1 for i in ansible_indicators if i in content) >= 2
    
    def _is_helm(self, file_path: Path) -> bool:
        """Check if file is part of a Helm chart."""
        helm_files = ["chart.yaml", "values.yaml", "values.yml"]
        path_indicators = ["charts/", "templates/", "helm/"]
        
        return (file_path.name.lower() in helm_files or 
                any(p in str(file_path).lower() for p in path_indicators))
    
    def _is_docker_compose(self, file_path: Path, content: str) -> bool:
        """Check if file is docker-compose."""
        if "docker-compose" in file_path.name.lower():
            return True
        if "compose" in file_path.name.lower():
            return True
        return "services:" in content and ("image:" in content or "build:" in content)
    
    def _analyze_dockerfile(self, file_path: Path) -> FileAnalysis:
        """Analyze a Dockerfile."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return FileAnalysis(path=file_path, language="docker")
        
        self.metrics.docker_files += 1
        
        analysis = FileAnalysis(
            path=file_path,
            language="docker",
            lines_of_code=len(content.split("\n")),
        )
        
        analysis.entities.append(Entity(
            name=f"Dockerfile: {file_path.parent.name}",
            entity_type=EntityType.SERVICE,
            description="Docker container definition",
            source=str(file_path),
            properties={"iac_type": "docker"}
        ))
        
        # Security checks for Dockerfile
        security_issues = []
        
        # Running as root
        if not re.search(r'USER\s+\w+', content) or re.search(r'USER\s+root', content):
            security_issues.append("container_runs_as_root")
        
        # Using latest tag
        if re.search(r'FROM\s+\S+:latest', content):
            security_issues.append("using_latest_tag")
        
        # Hardcoded secrets
        if re.search(r'(ENV|ARG)\s+\S*(PASSWORD|SECRET|KEY|TOKEN)\s*=\s*\S+', content, re.IGNORECASE):
            security_issues.append("hardcoded_secrets_in_dockerfile")
            self.metrics.secrets_in_iac += 1
        
        # Exposing sensitive ports
        exposed_ports = re.findall(r'EXPOSE\s+(\d+)', content)
        sensitive_ports = ["22", "3306", "5432", "27017", "6379"]
        for port in exposed_ports:
            if port in sensitive_ports:
                security_issues.append(f"sensitive_port_exposed_{port}")
        
        # Good practices
        if re.search(r'HEALTHCHECK', content):
            analysis.security_controls.append("healthcheck_defined")
        
        if re.search(r'--no-cache', content):
            analysis.security_controls.append("no_cache_install")
        
        # Multi-stage build (security best practice)
        if content.count("FROM ") > 1:
            analysis.security_controls.append("multi_stage_build")
        
        analysis.security_controls.extend(security_issues)
        
        return analysis
    
    def _analyze_terraform(
        self,
        content: str,
        file_path: Path,
        analysis: FileAnalysis
    ) -> None:
        """Analyze Terraform files."""
        self.metrics.terraform_files += 1
        
        # Find resource definitions
        resources = re.findall(r'resource\s+"([^"]+)"\s+"([^"]+)"', content)
        for resource_type, resource_name in resources:
            self.metrics.resources_defined += 1
            
            entity_type = EntityType.SERVICE
            if "database" in resource_type or "rds" in resource_type:
                entity_type = EntityType.DATABASE
            elif "queue" in resource_type or "sqs" in resource_type:
                entity_type = EntityType.QUEUE
            
            analysis.entities.append(Entity(
                name=f"{resource_type}.{resource_name}",
                entity_type=entity_type,
                description=f"Terraform resource: {resource_type}",
                source=str(file_path),
                properties={"iac_type": "terraform", "resource_type": resource_type}
            ))
            
            # Track security groups
            if "security_group" in resource_type:
                self.metrics.security_groups += 1
            
            # Track IAM
            if "iam" in resource_type:
                self.metrics.iam_policies += 1
        
        # Security checks
        security_issues = []
        
        # Open security groups (0.0.0.0/0)
        if re.search(r'cidr_blocks\s*=\s*\[\s*"0\.0\.0\.0/0"\s*\]', content):
            security_issues.append("open_security_group_ingress")
        
        # Unencrypted storage
        if re.search(r'encrypted\s*=\s*false', content):
            security_issues.append("unencrypted_storage")
        
        # Public S3 buckets
        if re.search(r'acl\s*=\s*"public', content):
            security_issues.append("public_s3_bucket")
        
        # Hardcoded secrets
        secret_patterns = [
            r'password\s*=\s*"[^"$]',
            r'secret\s*=\s*"[^"$]',
            r'api_key\s*=\s*"[^"$]',
        ]
        for pattern in secret_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                security_issues.append("hardcoded_secrets_in_terraform")
                self.metrics.secrets_in_iac += 1
                break
        
        # Good practices
        if "terraform {" in content and "backend" in content:
            analysis.security_controls.append("remote_state_backend")
        
        if re.search(r'encryption_configuration|server_side_encryption', content):
            analysis.security_controls.append("encryption_enabled")
        
        if "aws_kms_key" in content:
            analysis.security_controls.append("kms_encryption")
        
        if re.search(r'logging\s*{|access_logs\s*{', content):
            analysis.security_controls.append("logging_enabled")
        
        analysis.security_controls.extend(security_issues)
    
    def _analyze_kubernetes(
        self,
        content: str,
        file_path: Path,
        analysis: FileAnalysis
    ) -> None:
        """Analyze Kubernetes manifests."""
        self.metrics.kubernetes_manifests += 1
        
        # Extract kind and name
        kind_match = re.search(r'kind:\s*(\w+)', content)
        name_match = re.search(r'name:\s*([^\s\n]+)', content)
        
        kind = kind_match.group(1) if kind_match else "Unknown"
        name = name_match.group(1) if name_match else "unnamed"
        
        entity_type = EntityType.SERVICE
        if kind in ["ConfigMap", "Secret"]:
            entity_type = EntityType.DATA
        elif kind == "NetworkPolicy":
            entity_type = EntityType.SECURITY_CONTROL
        
        analysis.entities.append(Entity(
            name=f"{kind}/{name}",
            entity_type=entity_type,
            description=f"Kubernetes {kind}",
            source=str(file_path),
            properties={"iac_type": "kubernetes", "kind": kind}
        ))
        self.metrics.resources_defined += 1
        
        # Security checks
        security_issues = []
        
        # Running as root
        if re.search(r'runAsUser:\s*0', content):
            security_issues.append("k8s_runs_as_root")
        
        # Privileged containers
        if re.search(r'privileged:\s*true', content):
            security_issues.append("k8s_privileged_container")
        
        # Host network
        if re.search(r'hostNetwork:\s*true', content):
            security_issues.append("k8s_host_network")
        
        # Host PID
        if re.search(r'hostPID:\s*true', content):
            security_issues.append("k8s_host_pid")
        
        # No resource limits
        if kind in ["Deployment", "Pod", "StatefulSet", "DaemonSet"]:
            if not re.search(r'limits:', content):
                security_issues.append("k8s_no_resource_limits")
        
        # No security context
        if kind in ["Deployment", "Pod"] and not re.search(r'securityContext:', content):
            security_issues.append("k8s_no_security_context")
        
        # Secrets in plain text
        if kind == "Secret" and re.search(r'stringData:', content):
            security_issues.append("k8s_plaintext_secret")
        
        # Good practices
        if re.search(r'readOnlyRootFilesystem:\s*true', content):
            analysis.security_controls.append("k8s_readonly_filesystem")
        
        if re.search(r'runAsNonRoot:\s*true', content):
            analysis.security_controls.append("k8s_non_root")
        
        if kind == "NetworkPolicy":
            analysis.security_controls.append("k8s_network_policy")
        
        if re.search(r'serviceAccountName:', content):
            analysis.security_controls.append("k8s_service_account")
        
        if re.search(r'livenessProbe:|readinessProbe:', content):
            analysis.security_controls.append("k8s_health_probes")
        
        analysis.security_controls.extend(security_issues)
    
    def _analyze_cloudformation(
        self,
        content: str,
        file_path: Path,
        analysis: FileAnalysis
    ) -> None:
        """Analyze CloudFormation templates."""
        self.metrics.cloudformation_templates += 1
        
        # Find resources
        resources = re.findall(r'"?(\w+)"?:\s*{\s*"Type":\s*"(AWS::[^"]+)"', content)
        for resource_name, resource_type in resources:
            self.metrics.resources_defined += 1
            
            analysis.entities.append(Entity(
                name=f"{resource_name} ({resource_type})",
                entity_type=EntityType.SERVICE,
                description=f"CloudFormation resource: {resource_type}",
                source=str(file_path),
                properties={"iac_type": "cloudformation", "resource_type": resource_type}
            ))
        
        # Security checks
        security_issues = []
        
        # Open security groups
        if re.search(r'CidrIp.*0\.0\.0\.0/0', content):
            security_issues.append("cf_open_security_group")
        
        # Public S3 buckets
        if re.search(r'PublicRead|PublicReadWrite', content):
            security_issues.append("cf_public_s3")
        
        # Unencrypted RDS
        if "AWS::RDS" in content and not re.search(r'StorageEncrypted.*true', content, re.IGNORECASE):
            security_issues.append("cf_unencrypted_rds")
        
        # Good practices
        if re.search(r'AWS::KMS::Key|KmsKeyId', content):
            analysis.security_controls.append("cf_kms_encryption")
        
        if re.search(r'AWS::WAF|AWS::Shield', content):
            analysis.security_controls.append("cf_waf_protection")
        
        analysis.security_controls.extend(security_issues)
    
    def _analyze_ansible(
        self,
        content: str,
        file_path: Path,
        analysis: FileAnalysis
    ) -> None:
        """Analyze Ansible playbooks/roles."""
        self.metrics.ansible_files += 1
        
        # Find tasks
        tasks = re.findall(r'-\s*name:\s*(.+)', content)
        
        analysis.entities.append(Entity(
            name=f"Ansible: {file_path.name}",
            entity_type=EntityType.SERVICE,
            description=f"Ansible playbook/role with {len(tasks)} tasks",
            source=str(file_path),
            properties={"iac_type": "ansible", "task_count": len(tasks)}
        ))
        
        # Security checks
        security_issues = []
        
        # Hardcoded passwords
        if re.search(r'password:\s*[\'"]?[^\s{\'"\n]+[\'"]?', content):
            if not re.search(r'password:\s*\{\{', content):  # Not a variable
                security_issues.append("ansible_hardcoded_password")
                self.metrics.secrets_in_iac += 1
        
        # No become_user specified when using become
        if re.search(r'become:\s*true', content) and not re.search(r'become_user:', content):
            security_issues.append("ansible_become_without_user")
        
        # Good practices
        if re.search(r'no_log:\s*true', content):
            analysis.security_controls.append("ansible_no_log")
        
        if "ansible-vault" in content or "vault_password" in content:
            analysis.security_controls.append("ansible_vault")
        
        analysis.security_controls.extend(security_issues)
    
    def _analyze_helm(
        self,
        content: str,
        file_path: Path,
        analysis: FileAnalysis
    ) -> None:
        """Analyze Helm chart files."""
        self.metrics.helm_charts += 1
        
        # Extract chart name
        name_match = re.search(r'name:\s*(\S+)', content)
        chart_name = name_match.group(1) if name_match else file_path.parent.name
        
        analysis.entities.append(Entity(
            name=f"Helm: {chart_name}",
            entity_type=EntityType.SERVICE,
            description="Helm chart",
            source=str(file_path),
            properties={"iac_type": "helm"}
        ))
        
        # Check values.yaml for security settings
        if "values" in file_path.name.lower():
            # Check for security context defaults
            if re.search(r'securityContext:', content):
                analysis.security_controls.append("helm_security_context")
            
            if re.search(r'serviceAccount:', content):
                analysis.security_controls.append("helm_service_account")
    
    def _analyze_docker_compose(
        self,
        content: str,
        file_path: Path,
        analysis: FileAnalysis
    ) -> None:
        """Analyze docker-compose files."""
        self.metrics.docker_files += 1
        
        # Find services
        services = re.findall(r'^\s{2}(\w+):\s*$', content, re.MULTILINE)
        
        for service in services:
            analysis.entities.append(Entity(
                name=f"Service: {service}",
                entity_type=EntityType.SERVICE,
                description="Docker Compose service",
                source=str(file_path),
                properties={"iac_type": "docker-compose"}
            ))
        
        # Security checks
        security_issues = []
        
        # Privileged mode
        if re.search(r'privileged:\s*true', content):
            security_issues.append("compose_privileged")
        
        # Host network
        if re.search(r'network_mode:\s*[\'"]?host', content):
            security_issues.append("compose_host_network")
        
        # Environment secrets
        if re.search(r'environment:.*(?:PASSWORD|SECRET|KEY|TOKEN)\s*:', content, re.DOTALL | re.IGNORECASE):
            security_issues.append("compose_env_secrets")
        
        # Good practices
        if re.search(r'healthcheck:', content):
            analysis.security_controls.append("compose_healthcheck")
        
        if re.search(r'read_only:\s*true', content):
            analysis.security_controls.append("compose_readonly")
        
        if re.search(r'user:', content):
            analysis.security_controls.append("compose_non_root_user")
        
        analysis.security_controls.extend(security_issues)
    
    def get_metrics(self) -> InfrastructureMetrics:
        """Return collected infrastructure metrics."""
        return self.metrics
    
    def reset_metrics(self) -> None:
        """Reset metrics for a new analysis."""
        self.metrics = InfrastructureMetrics()


