from __future__ import annotations

from typing import List

from backend.domain.models import (
    DynamicStateConfig,
    NetworkStateJobCreateRequest,
    NetworkStateScenarioConfig,
)


def build_network_state_requests_from_scenario(
    scenario: NetworkStateScenarioConfig,
) -> List[NetworkStateJobCreateRequest]:
    if scenario.satellites is None and scenario.manual_constellation is None:
        raise ValueError("Scenario config requires either 'satellites' or 'manual_constellation'")

    requests = []
    for algorithm in scenario.dynamic_state_algorithms:
        request_name = scenario.name_template.format(
            base_name=scenario.base_name,
            algorithm=algorithm.value,
        )
        requests.append(
            NetworkStateJobCreateRequest(
                name=request_name,
                output_root=scenario.output_root,
                ground_stations=list(scenario.ground_stations),
                description=scenario.description,
                dynamic_state=DynamicStateConfig(
                    algorithm=algorithm,
                    time_step_ms=scenario.dynamic_state_defaults.time_step_ms,
                    duration_s=scenario.dynamic_state_defaults.duration_s,
                    num_threads=scenario.dynamic_state_defaults.num_threads,
                    start_time_s=scenario.dynamic_state_defaults.start_time_s,
                    print_logs=scenario.dynamic_state_defaults.print_logs,
                ),
                isl_config=scenario.isl_config,
                satellites=list(scenario.satellites) if scenario.satellites else None,
                manual_constellation=scenario.manual_constellation,
            )
        )
    return requests
