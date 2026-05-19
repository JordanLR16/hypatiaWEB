from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from typing import Dict, List

from backend.domain.models import JobRecord, NetworkStateJobCreateRequest, NetworkStateScenarioConfig
from backend.infra.repository import InMemoryJobRepository, get_job_repository
from backend.infra.workspace import WorkspaceManager, get_workspace_manager
from backend.request_builders.network_state import build_network_state_requests_from_scenario
from backend.services.network_state_service import NetworkStateService, get_network_state_service


router = APIRouter(prefix="/v1/network-state-jobs", tags=["network-state"])
scenario_router = APIRouter(prefix="/v1/network-state-scenarios", tags=["network-state"])


def _model_dump(model: object) -> Dict:
    if hasattr(model, "model_dump"):
        return model.model_dump()  # type: ignore[no-any-return]
    if hasattr(model, "dict"):
        return model.dict()  # type: ignore[no-any-return]
    raise TypeError(f"Unsupported model type: {type(model)!r}")


def _enqueue_network_state_job(
    request: NetworkStateJobCreateRequest,
    background_tasks: BackgroundTasks,
    job_repository: InMemoryJobRepository,
    workspace_manager: WorkspaceManager,
    service: NetworkStateService,
) -> JobRecord:
    job = job_repository.create_job(kind="network_state", request_payload=_model_dump(request))

    def run_job() -> None:
        job_repository.mark_running(job.id)
        try:
            workspace = workspace_manager.create_job_workspace(job.id)
            result = service.generate(request=request, workspace=workspace)
            job_repository.mark_succeeded(job.id, artifacts=result.artifacts, metadata=_model_dump(result))
        except Exception as exc:  # pragma: no cover - defensive API boundary
            job_repository.mark_failed(job.id, str(exc))

    background_tasks.add_task(run_job)
    return job_repository.get_required(job.id)


@router.post("", response_model=JobRecord, status_code=status.HTTP_202_ACCEPTED)
def create_network_state_job(
    request: NetworkStateJobCreateRequest,
    background_tasks: BackgroundTasks,
    job_repository: InMemoryJobRepository = Depends(get_job_repository),
    workspace_manager: WorkspaceManager = Depends(get_workspace_manager),
    service: NetworkStateService = Depends(get_network_state_service),
) -> JobRecord:
    return _enqueue_network_state_job(
        request=request,
        background_tasks=background_tasks,
        job_repository=job_repository,
        workspace_manager=workspace_manager,
        service=service,
    )


@scenario_router.post("/jobs", response_model=List[JobRecord], status_code=status.HTTP_202_ACCEPTED)
def create_network_state_jobs_from_scenario(
    scenario: NetworkStateScenarioConfig,
    background_tasks: BackgroundTasks,
    job_repository: InMemoryJobRepository = Depends(get_job_repository),
    workspace_manager: WorkspaceManager = Depends(get_workspace_manager),
    service: NetworkStateService = Depends(get_network_state_service),
) -> List[JobRecord]:
    requests = build_network_state_requests_from_scenario(scenario)
    return [
        _enqueue_network_state_job(
            request=request,
            background_tasks=background_tasks,
            job_repository=job_repository,
            workspace_manager=workspace_manager,
            service=service,
        )
        for request in requests
    ]


@router.get("/{job_id}", response_model=JobRecord)
def get_network_state_job(
    job_id: str,
    job_repository: InMemoryJobRepository = Depends(get_job_repository),
) -> JobRecord:
    try:
        return job_repository.get_required(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
