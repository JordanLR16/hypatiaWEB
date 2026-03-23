from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, List

from backend.domain.enums import JobStatus
from backend.domain.models import ArtifactRecord, JobRecord


class InMemoryJobRepository:
    def __init__(self) -> None:
        self._jobs: Dict[str, JobRecord] = {}
        self._lock = Lock()

    def create_job(self, kind: str, request_payload: Dict[str, Any]) -> JobRecord:
        job = JobRecord.new(kind=kind, request_payload=request_payload)
        with self._lock:
            self._jobs[job.id] = job
        return job

    def _get_required_unlocked(self, job_id: str) -> JobRecord:
        if job_id not in self._jobs:
            raise KeyError(f"Job '{job_id}' was not found")
        return self._jobs[job_id]

    def get_required(self, job_id: str) -> JobRecord:
        with self._lock:
            return self._get_required_unlocked(job_id)

    def mark_running(self, job_id: str) -> None:
        with self._lock:
            job = self._get_required_unlocked(job_id)
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now(timezone.utc)

    def mark_succeeded(
        self,
        job_id: str,
        artifacts: List[ArtifactRecord],
        metadata: Dict[str, Any],
    ) -> None:
        with self._lock:
            job = self._get_required_unlocked(job_id)
            job.status = JobStatus.SUCCEEDED
            job.artifacts = artifacts
            job.metadata = metadata
            job.finished_at = datetime.now(timezone.utc)

    def mark_failed(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._get_required_unlocked(job_id)
            job.status = JobStatus.FAILED
            job.error = error
            job.finished_at = datetime.now(timezone.utc)


_job_repository = InMemoryJobRepository()


def get_job_repository() -> InMemoryJobRepository:
    return _job_repository
