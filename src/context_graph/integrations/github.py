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
            try:
                shutil.rmtree(self.path)
            except (PermissionError, OSError) as e:
                # On macOS, sandboxed apps (like Electron) create files with
                # com.apple.provenance extended attribute that can't be removed.
                # Try using subprocess as a fallback.
                import logging
                logging.warning(f"shutil.rmtree failed for {self.path}, trying rm -rf: {e}")
                try:
                    subprocess.run(
                        ["rm", "-rf", str(self.path)],
                        check=False,
                        capture_output=True,
                    )
                except Exception:
                    # Final fallback: just log and continue, don't crash
                    logging.warning(f"Could not cleanup temp directory: {self.path}")


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
            # Use cache directory from environment (set by Electron) or fall back to temp.
            # 
            # IMPORTANT: macOS Sandbox Restrictions (see docs/TROUBLESHOOTING.md)
            # - ~/Library/Caches/ fails when Python is spawned by sandboxed Electron
            # - /var/folders/ (tempfile.gettempdir()) has quarantine restrictions
            # - Only /tmp (/private/tmp) reliably has write access on macOS
            #
            env_cache_dir = os.environ.get("CONTEXT_GRAPH_CACHE_DIR")
            if env_cache_dir:
                # Use the directory provided by Electron (always has write access)
                user_cache = Path(env_cache_dir)
            else:
                import platform
                if platform.system() == "Darwin":
                    # Use /tmp directly - only path that reliably works on macOS
                    # See docs/TROUBLESHOOTING.md for full explanation
                    user_cache = Path("/tmp") / "context-graph-repos"
                else:
                    user_cache = Path.home() / ".cache" / "context-graph" / "repos"
            
            # Create directory with proper error handling
            try:
                user_cache.mkdir(parents=True, exist_ok=True)
            except (PermissionError, OSError) as e:
                # Final fallback: use /tmp directly
                import logging
                logging.warning(f"Could not create cache dir {user_cache}: {e}, using /tmp")
                user_cache = Path("/tmp") / "context-graph-repos"
                user_cache.mkdir(parents=True, exist_ok=True)
            
            # Check if we already have this repo cloned (any suffix)
            # Reuse existing clone to avoid permission issues with macOS sandbox
            # 
            # IMPORTANT: On macOS, Electron-spawned Python processes have sandbox
            # restrictions that block ALL git operations (clone, fetch, etc.)
            # The only workaround is to reuse pre-cloned repos without any git ops.
            existing_clones = list(user_cache.glob(f"{repo.name}-*"))
            if existing_clones:
                # Reuse the most recent existing clone
                existing_clone = sorted(existing_clones, key=lambda p: p.stat().st_mtime)[-1]
                if (existing_clone / ".git").exists():
                    import logging
                    logging.info(f"Reusing existing clone (no git ops due to sandbox): {existing_clone}")
                    # Don't try git fetch - it's blocked by macOS sandbox when
                    # Python is spawned by Electron. Just use the existing clone as-is.
                    # Users can manually refresh by clearing /tmp/context-graph-repos/
                    return ClonedRepo(
                        path=existing_clone,
                        repo=repo,
                        temp_dir=False,  # Don't delete - it's cached
                    )
            
            clone_path = user_cache / f"{repo.name}-{os.getpid()}"
            
            # If clone_path already exists (stale from previous run), remove it
            if clone_path.exists():
                self._force_remove_directory(clone_path)
            
            is_temp = True
        
        # Try to clone - first via tarball download (bypasses sandbox), then git clone
        clone_success = False
        
        # Method 1: Download tarball via HTTP (works in sandboxed environments)
        # This bypasses git entirely, using GitHub's archive API
        import platform
        if platform.system() == "Darwin":
            try:
                clone_success = self._download_tarball(repo, clone_path)
            except Exception as e:
                import logging
                logging.warning(f"Tarball download failed, will try git clone: {e}")
        
        # Method 2: Traditional git clone (fallback, may fail in sandbox)
        if not clone_success:
            clone_url = repo.clone_url
            if self.token:
                clone_url = f"https://{self.token}@github.com/{repo.owner}/{repo.name}.git"
            
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
    
    def _download_tarball(self, repo: GitHubRepo, target_path: Path) -> bool:
        """
        Download repository as tarball and extract it.
        
        This bypasses git entirely, using GitHub's archive API via HTTP.
        Works in sandboxed environments where git operations are blocked.
        
        Returns:
            True if successful, False otherwise
        """
        import tarfile
        import urllib.request
        import logging
        
        branch = repo.branch or "main"
        
        # GitHub tarball URL format
        tarball_url = f"https://github.com/{repo.owner}/{repo.name}/archive/refs/heads/{branch}.tar.gz"
        
        # Add auth header if token available
        headers = {}
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        
        logging.info(f"Downloading tarball from {tarball_url}")
        
        try:
            # Create request with headers
            request = urllib.request.Request(tarball_url, headers=headers)
            
            # Download to temp file
            temp_tarball = target_path.parent / f"{repo.name}-download.tar.gz"
            
            with urllib.request.urlopen(request, timeout=120) as response:
                with open(temp_tarball, 'wb') as f:
                    # Read in chunks to handle large repos
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
            
            # Extract tarball
            logging.info(f"Extracting tarball to {target_path}")
            with tarfile.open(temp_tarball, 'r:gz') as tar:
                # Extract to parent directory first (tarball contains a root folder)
                tar.extractall(path=target_path.parent)
            
            # GitHub tarballs extract to {repo}-{branch}/ folder
            extracted_name = f"{repo.name}-{branch}"
            extracted_path = target_path.parent / extracted_name
            
            # Rename to target path
            if extracted_path.exists():
                if target_path.exists():
                    shutil.rmtree(target_path)
                extracted_path.rename(target_path)
            
            # Create a fake .git directory so our code recognizes it as a repo
            git_dir = target_path / ".git"
            git_dir.mkdir(exist_ok=True)
            (git_dir / "HEAD").write_text(f"ref: refs/heads/{branch}\n")
            (git_dir / "config").write_text(f"[remote \"origin\"]\n\turl = {repo.clone_url}\n")
            
            # Cleanup temp file
            if temp_tarball.exists():
                temp_tarball.unlink()
            
            logging.info(f"Successfully downloaded and extracted {repo.full_name}")
            return True
            
        except urllib.error.HTTPError as e:
            # Branch might not exist, try 'master' as fallback
            if e.code == 404 and branch == "main":
                logging.info("Branch 'main' not found, trying 'master'")
                repo_copy = GitHubRepo(
                    owner=repo.owner,
                    name=repo.name,
                    url=repo.url,
                    branch="master",
                    commit=repo.commit,
                    pr_number=repo.pr_number,
                )
                return self._download_tarball(repo_copy, target_path)
            logging.warning(f"HTTP error downloading tarball: {e}")
            return False
        except Exception as e:
            logging.warning(f"Failed to download tarball: {e}")
            # Cleanup partial download
            if target_path.exists():
                shutil.rmtree(target_path, ignore_errors=True)
            return False
    
    def _force_remove_directory(self, path: Path) -> None:
        """
        Force remove a directory, handling macOS extended attributes.
        
        macOS sandbox can add com.apple.quarantine or com.apple.provenance
        attributes that prevent normal deletion.
        """
        import logging
        
        if not path.exists():
            return
        
        try:
            # First, try to clear extended attributes (macOS specific)
            import platform
            if platform.system() == "Darwin":
                subprocess.run(
                    ["xattr", "-cr", str(path)],
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
            
            # Try standard removal
            shutil.rmtree(path)
        except (PermissionError, OSError) as e:
            logging.warning(f"shutil.rmtree failed for {path}: {e}, trying rm -rf")
            try:
                # Fallback: use rm -rf which handles more edge cases
                subprocess.run(
                    ["rm", "-rf", str(path)],
                    check=False,
                    capture_output=True,
                    timeout=60,
                )
            except Exception as e2:
                logging.warning(f"rm -rf also failed for {path}: {e2}")
    
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

