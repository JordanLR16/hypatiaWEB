# Backend Scaffold

This package is a first-pass service wrapper around the existing Hypatia workflow.

Current scope:

- `FastAPI` app entrypoint in `backend.api.main`
- `POST /v1/network-state-jobs`
- `GET /v1/network-state-jobs/{job_id}`
- In-memory job repository
- File-based workspace manager
- `NetworkStateService` that wraps the current `satgen` generation flow
- A Manila/Dalian reduced-Kuiper preset for step-1 parity checks

Step-1 parity check against the current integration script logic:

```bash
python3 -m backend.scripts.verify_step1_parity
```

Run locally after installing `fastapi` and an ASGI server such as `uvicorn`:

```bash
uvicorn backend.api.main:app --reload
```

Example next steps:

1. Add persistent job storage instead of the in-memory repository.
2. Extract ns-3 run generation into `RunConfigService`.
3. Add a `SimulationService` for worker-side subprocess orchestration.
