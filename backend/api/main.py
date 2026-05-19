from fastapi import FastAPI

from backend.api.routes.health import router as health_router
from backend.api.routes.network_state import router as network_state_router
from backend.api.routes.network_state import scenario_router as network_state_scenario_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Hypatia Backend",
        version="0.1.0",
        description="Experimental API wrapper around Hypatia network-state generation.",
    )
    app.include_router(health_router)
    app.include_router(network_state_router)
    app.include_router(network_state_scenario_router)
    return app


app = create_app()
