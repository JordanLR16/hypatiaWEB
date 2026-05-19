import shutil
import unittest
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.api.main import create_app
from backend.api.routes.network_state import (
    get_job_repository,
    get_network_state_service,
    get_workspace_manager,
)
from backend.domain.models import ArtifactRecord, NetworkStateJobResult
from backend.infra.repository import InMemoryJobRepository
from backend.infra.workspace import WorkspaceManager


TEST_WORKSPACE_ROOT = Path(__file__).resolve().parents[2] / "backend_workspaces" / "api_test_tmp"


class _FakeNetworkStateService:
    def __init__(self) -> None:
        self.requests = []

    def generate(self, request, workspace: Path) -> NetworkStateJobResult:
        self.requests.append(request)
        output_dir = workspace / request.output_root / request.name
        dynamic_state_dir = output_dir / (
            f"dynamic_state_{request.dynamic_state.time_step_ms}"
            f"ms_for_{request.dynamic_state.duration_s}s"
        )
        dynamic_state_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = output_dir / "description.txt"
        artifact_path.write_text("ok\n", encoding="utf-8")
        return NetworkStateJobResult(
            name=request.name,
            output_directory=str(output_dir),
            dynamic_state_directory=str(dynamic_state_dir),
            artifacts=[
                ArtifactRecord(
                    name="description.txt",
                    path=str(artifact_path),
                )
            ],
        )


def _request_payload() -> dict:
    return {
        "name": "direct_request",
        "output_root": "generated",
        "ground_stations": [
            {
                "gid": 1,
                "name": "Station A",
                "latitude_deg": 14.5,
                "longitude_deg": 121.0,
                "elevation_m": 15.0,
            }
        ],
        "description": {
            "max_gsl_length_m": 111.0,
            "max_isl_length_m": 222.0,
        },
        "dynamic_state": {
            "algorithm": "algorithm_free_one_only_over_isls",
            "time_step_ms": 1000,
            "duration_s": 30,
        },
        "isl_config": {
            "selection": "isls_none",
        },
        "satellites": [
            {
                "sid": 0,
                "name": "InlineSat-0",
                "tle_line1": "1 00001U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    01",
                "tle_line2": "2 00001  53.0000  42.0000 0000001   0.0000 142.9412 14.80000000    00",
            }
        ],
    }


def _scenario_payload() -> dict:
    payload = _request_payload()
    return {
        "base_name": "scenario_request",
        "output_root": payload["output_root"],
        "name_template": "{base_name}_{algorithm}",
        "ground_stations": payload["ground_stations"],
        "description": payload["description"],
        "dynamic_state_defaults": {
            "time_step_ms": 1000,
            "duration_s": 30,
        },
        "dynamic_state_algorithms": [
            "algorithm_free_one_only_over_isls",
            "algorithm_free_gs_one_sat_many_only_over_isls",
        ],
        "isl_config": payload["isl_config"],
        "satellites": payload["satellites"],
    }


class TestNetworkStateApi(unittest.TestCase):
    def setUp(self) -> None:
        TEST_WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
        self.workspace_root = TEST_WORKSPACE_ROOT / uuid4().hex[:8]
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.repository = InMemoryJobRepository()
        self.workspace_manager = WorkspaceManager(
            repo_root=self.workspace_root,
            base_dir_name="jobs",
        )
        self.service = _FakeNetworkStateService()
        self.app = create_app()
        self.app.dependency_overrides[get_job_repository] = lambda: self.repository
        self.app.dependency_overrides[get_workspace_manager] = lambda: self.workspace_manager
        self.app.dependency_overrides[get_network_state_service] = lambda: self.service
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()
        shutil.rmtree(self.workspace_root, ignore_errors=True)

    def test_create_network_state_job_accepts_non_preset_request(self) -> None:
        response = self.client.post("/v1/network-state-jobs", json=_request_payload())

        self.assertEqual(202, response.status_code)
        body = response.json()
        self.assertEqual("network_state", body["kind"])
        self.assertEqual("direct_request", body["request_payload"]["name"])

        status_response = self.client.get(f"/v1/network-state-jobs/{body['id']}")
        self.assertEqual(200, status_response.status_code)
        status_body = status_response.json()
        self.assertEqual("succeeded", status_body["status"])
        self.assertEqual("direct_request", status_body["metadata"]["name"])
        self.assertEqual(1, len(self.service.requests))

    def test_create_network_state_jobs_from_scenario_enqueues_one_job_per_algorithm(self) -> None:
        response = self.client.post("/v1/network-state-scenarios/jobs", json=_scenario_payload())

        self.assertEqual(202, response.status_code)
        body = response.json()
        self.assertEqual(2, len(body))
        self.assertEqual(
            [
                "scenario_request_algorithm_free_one_only_over_isls",
                "scenario_request_algorithm_free_gs_one_sat_many_only_over_isls",
            ],
            [job["request_payload"]["name"] for job in body],
        )

        for job in body:
            status_response = self.client.get(f"/v1/network-state-jobs/{job['id']}")
            self.assertEqual(200, status_response.status_code)
            self.assertEqual("succeeded", status_response.json()["status"])
        self.assertEqual(2, len(self.service.requests))

    def test_create_network_state_jobs_from_scenario_rejects_invalid_payloads(self) -> None:
        payload = _scenario_payload()
        payload["dynamic_state_algorithms"] = []

        response = self.client.post("/v1/network-state-scenarios/jobs", json=payload)

        self.assertEqual(422, response.status_code)
        self.assertEqual(0, len(self.service.requests))
