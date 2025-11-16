"""
Git information capture.
"""

import os
from typing import Dict, Optional

try:
    from git import Repo, InvalidGitRepositoryError
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False


class GitInfo:
    """Capture git information from current repository."""

    @staticmethod
    def get_info(path: Optional[str] = None) -> Dict[str, str]:
        """
        Get git information.

        Args:
            path: Path to git repository (default: current directory)

        Returns:
            Dictionary with git information

        Raises:
            Exception: If git is not available or not a git repository
        """
        if not GIT_AVAILABLE:
            raise Exception("GitPython not available. Install with: pip install GitPython")

        if path is None:
            path = os.getcwd()

        try:
            repo = Repo(path, search_parent_directories=True)

            # Get commit hash
            commit = repo.head.commit.hexsha

            # Get branch name
            try:
                branch = repo.active_branch.name
            except:
                branch = None

            # Get remote URL
            try:
                remote_url = repo.remote("origin").url
            except:
                remote_url = None

            # Check for uncommitted changes
            is_dirty = repo.is_dirty()

            return {
                "commit": commit,
                "branch": branch,
                "remote": remote_url,
                "is_dirty": is_dirty,
            }
        except InvalidGitRepositoryError:
            raise Exception(f"Not a git repository: {path}")
