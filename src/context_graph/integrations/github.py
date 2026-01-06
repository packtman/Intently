"""
GitHub Integration - Clone and analyze repositories directly from GitHub.

Supports:
- Public and private repositories
- Specific branches, tags, or commits
- Pull request analysis
- Automatic cleanup
"""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
import subprocess


@dataclass
class GitHubRepo:
    """Parsed GitHub repository information."""
    
    owner: str
    name: str
    url: str
    branch: Optional[str] = None
    commit: Optional[str] = None
    pr_number: Optional[int] = None
    
    @property
    def clone_url(self) -> str:
        """Get the clone URL."""
        return f"https://github.com/{self.owner}/{self.name}.git"
    
    @property
    def full_name(self) -> str:
        """Get owner/repo format."""
        return f"{self.owner}/{self.name}"


@dataclass
class ClonedRepo:
    """A cloned repository ready for analysis."""
    
    path: Path
    repo: GitHubRepo
    temp_dir: bool = True  # Whether this is a temporary directory
    
    def cleanup(self) -> None:
        """Remove the cloned repository."""
        if self.temp_dir and self.path.exists():
            shutil.rmtree(self.path)


class GitHubIntegration:
    """
    GitHub integration for cloning and analyzing repositories.
    
    Usage:
        github = GitHubIntegration(token="ghp_...")  # Optional for private repos
        
        # Clone a repo
        repo = github.clone("https://github.com/owner/repo")
        
        # Clone specific branch
        repo = github.clone("https://github.com/owner/repo", branch="develop")
        
        # Clone and checkout PR
        repo = github.clone("https://github.com/owner/repo", pr=123)
        
        # Analyze
        state = analyzer.analyze_codebase(repo.path)
        
        # Cleanup
        repo.cleanup()
    """
    
    def __init__(
        self,
        token: Optional[str] = None,
        cache_dir: Optional[Path] = None,
    ) -> None:
        """
        Initialize GitHub integration.
        
        Args:
            token: GitHub personal access token for private repos
            cache_dir: Directory to cache cloned repos (uses temp if not specified)
        """
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.cache_dir = cache_dir
    
    def parse_url(
        self,
        url: str,
        branch: Optional[str] = None,
        commit: Optional[str] = None,
        pr: Optional[int] = None,
    ) -> GitHubRepo:
        """
        Parse a GitHub URL into components.
        
        Supports formats:
        - https://github.com/owner/repo
        - https://github.com/owner/repo.git
        - https://github.com/owner/repo/tree/branch
        - https://github.com/owner/repo/pull/123
        - github.com/owner/repo
        - owner/repo
        """
        url = url.strip()
        
        # Normalize common URL typos
        url = url.replace("https:/github.com", "https://github.com")
        url = url.replace("http:/github.com", "https://github.com")
        
        # Handle owner/repo format
        if "/" in url and not url.startswith(("http", "github")):
            parts = url.split("/")
            if len(parts) == 2:
                return GitHubRepo(
                    owner=parts[0],
                    name=parts[1],
                    url=url,
                    branch=branch,
                    commit=commit,
                    pr_number=pr,
                )
        
        # Parse URL
        if not url.startswith("http"):
            url = f"https://{url}"
        
        parsed = urlparse(url)
        path_parts = parsed.path.strip("/").split("/")
        
        if len(path_parts) < 2:
            raise ValueError(f"Invalid GitHub URL: {url}")
        
        owner = path_parts[0]
        name = path_parts[1].replace(".git", "")
        
        # Extract branch from URL if present
        detected_branch = branch
        detected_pr = pr
        
        if len(path_parts) >= 4:
            if path_parts[2] == "tree":
                detected_branch = "/".join(path_parts[3:])
            elif path_parts[2] == "pull" and path_parts[3].isdigit():
                detected_pr = int(path_parts[3])
        
        return GitHubRepo(
            owner=owner,
            name=name,
            url=url,
            branch=detected_branch,
            commit=commit,
            pr_number=detected_pr,
        )
    
    def clone(
        self,
        url: str,
        branch: Optional[str] = None,
        commit: Optional[str] = None,
        pr: Optional[int] = None,
        depth: int = 1,
        target_dir: Optional[Path] = None,
    ) -> ClonedRepo:
        """
        Clone a GitHub repository.
        
        Args:
            url: GitHub URL or owner/repo
            branch: Branch to checkout
            commit: Specific commit to checkout
            pr: Pull request number to checkout
            depth: Clone depth (1 for shallow clone)
            target_dir: Where to clone (uses temp dir if not specified)
            
        Returns:
            ClonedRepo with path to cloned repository
        """
        repo = self.parse_url(url, branch, commit, pr)
        
        # Determine target directory
        if target_dir:
            clone_path = target_dir
            is_temp = False
        elif self.cache_dir:
            clone_path = self.cache_dir / repo.owner / repo.name
            is_temp = False
        else:
            clone_path = Path(tempfile.mkdtemp(prefix=f"ctx-{repo.name}-"))
            is_temp = True
        
        # Build clone URL with token if available
        clone_url = repo.clone_url
        if self.token:
            clone_url = f"https://{self.token}@github.com/{repo.owner}/{repo.name}.git"
        
        # Clone the repository
        clone_cmd = ["git", "clone"]
        
        if depth > 0:
            clone_cmd.extend(["--depth", str(depth)])
        
        if repo.branch and not repo.pr_number:
            clone_cmd.extend(["--branch", repo.branch])
        
        clone_cmd.extend([clone_url, str(clone_path)])
        
        try:
            subprocess.run(
                clone_cmd,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to clone repository: {e.stderr}")
        
        # Handle PR checkout
        if repo.pr_number:
            self._checkout_pr(clone_path, repo.pr_number)
        
        # Handle specific commit
        if repo.commit:
            self._checkout_commit(clone_path, repo.commit)
        
        return ClonedRepo(
            path=clone_path,
            repo=repo,
            temp_dir=is_temp,
        )
    
    def _checkout_pr(self, repo_path: Path, pr_number: int) -> None:
        """Checkout a pull request."""
        try:
            # Fetch the PR
            subprocess.run(
                ["git", "fetch", "origin", f"pull/{pr_number}/head:pr-{pr_number}"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            # Checkout the PR branch
            subprocess.run(
                ["git", "checkout", f"pr-{pr_number}"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to checkout PR #{pr_number}: {e.stderr}")
    
    def _checkout_commit(self, repo_path: Path, commit: str) -> None:
        """Checkout a specific commit."""
        try:
            subprocess.run(
                ["git", "checkout", commit],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to checkout commit {commit}: {e.stderr}")
    
    def get_default_branch(self, url: str) -> str:
        """Get the default branch of a repository."""
        repo = self.parse_url(url)
        
        clone_url = repo.clone_url
        if self.token:
            clone_url = f"https://{self.token}@github.com/{repo.owner}/{repo.name}.git"
        
        try:
            result = subprocess.run(
                ["git", "ls-remote", "--symref", clone_url, "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            # Parse output like: ref: refs/heads/main  HEAD
            for line in result.stdout.split("\n"):
                if line.startswith("ref:"):
                    return line.split("/")[-1].split()[0]
        except subprocess.CalledProcessError:
            pass
        
        return "main"  # Default fallback
    
    def list_branches(self, url: str) -> list[str]:
        """List all branches in a repository."""
        repo = self.parse_url(url)
        
        clone_url = repo.clone_url
        if self.token:
            clone_url = f"https://{self.token}@github.com/{repo.owner}/{repo.name}.git"
        
        try:
            result = subprocess.run(
                ["git", "ls-remote", "--heads", clone_url],
                capture_output=True,
                text=True,
                check=True,
            )
            branches = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    # Format: <sha>\trefs/heads/<branch>
                    ref = line.split("\t")[1]
                    branch = ref.replace("refs/heads/", "")
                    branches.append(branch)
            return branches
        except subprocess.CalledProcessError:
            return []


# Convenience function for quick cloning
def clone_github_repo(
    url: str,
    branch: Optional[str] = None,
    pr: Optional[int] = None,
    token: Optional[str] = None,
) -> ClonedRepo:
    """
    Quick clone a GitHub repository.
    
    Args:
        url: GitHub URL or owner/repo
        branch: Optional branch to checkout
        pr: Optional PR number to checkout
        token: GitHub token for private repos
        
    Returns:
        ClonedRepo ready for analysis
    """
    github = GitHubIntegration(token=token)
    return github.clone(url, branch=branch, pr=pr)

