from __future__ import annotations

from pathlib import Path


class WorkspaceManager:
    def __init__(self, repo_root: Path, base_dir_name: str = "backend_workspaces") -> None:
        self.repo_root = repo_root
        self.base_dir = repo_root / base_dir_name
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_job_workspace(self, job_id: str) -> Path:
        workspace = self.base_dir / job_id
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace


_workspace_manager = WorkspaceManager(repo_root=Path(__file__).resolve().parents[2])


def get_workspace_manager() -> WorkspaceManager:
    return _workspace_manager
