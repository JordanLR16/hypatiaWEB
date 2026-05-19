# Backend Scaffold

This package is a first-pass service wrapper around the existing Hypatia workflow.

Current scope:

- `FastAPI` app entrypoint in `backend.api.main`
- `POST /v1/network-state-jobs` for fully expanded network-state job requests
- `POST /v1/network-state-scenarios/jobs` for scenario-first job creation
- `GET /v1/network-state-jobs/{job_id}`
- In-memory job repository
- File-based workspace manager
- `NetworkStateService` that wraps the current `satgen` generation flow
- Scenario-to-request builders in `backend.request_builders`
- A Manila/Dalian reduced-Kuiper preset retained as an example and parity fixture

The preferred input shape is now `NetworkStateScenarioConfig`. A scenario
describes the reusable topology, dynamic-state defaults, and algorithms to run.
The backend expands it into one `NetworkStateJobCreateRequest` per algorithm and
enqueues those jobs through the same network-state job pipeline.

Presets under `backend.presets` are convenience factories for known scenarios.
They should not be required by normal API callers.

Scenario-first job creation:

```bash
curl -X POST http://localhost:8000/v1/network-state-scenarios/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "base_name": "example_network",
    "output_root": "generated",
    "name_template": "{base_name}_{algorithm}",
    "ground_stations": [
      {
        "gid": 1,
        "name": "Station A",
        "latitude_deg": 14.5,
        "longitude_deg": 121.0,
        "elevation_m": 15.0
      }
    ],
    "description": {
      "max_gsl_length_m": 1000000.0,
      "max_isl_length_m": 2000000.0
    },
    "dynamic_state_defaults": {
      "time_step_ms": 1000,
      "duration_s": 30
    },
    "dynamic_state_algorithms": [
      "algorithm_free_one_only_over_isls"
    ],
    "isl_config": {
      "selection": "isls_none"
    },
    "satellites": [
      {
        "sid": 0,
        "name": "InlineSat-0",
        "tle_line1": "1 00001U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    01",
        "tle_line2": "2 00001  53.0000  42.0000 0000001   0.0000 142.9412 14.80000000    00"
      }
    ]
  }'
```

The response is a list of queued jobs. Poll each job with:

```bash
curl http://localhost:8000/v1/network-state-jobs/<job_id>
```

Step-1 parity check against the current integration script logic:

```bash
python3 -m backend.scripts.verify_step1_parity
```

Backend unit/API tests:

```bash
python3 -m unittest discover -v -s backend/tests
```

Run locally after installing `fastapi` and an ASGI server such as `uvicorn`:

```bash
uvicorn backend.api.main:app --reload
```

Example next steps:

1. Add persistent job storage instead of the in-memory repository.
2. Extract ns-3 run generation into `RunConfigService`.
3. Add a `SimulationService` for worker-side subprocess orchestration.
