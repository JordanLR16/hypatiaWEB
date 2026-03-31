from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from backend.domain.enums import DynamicStateAlgorithm, IslSelection
from backend.domain.models import (
    DescriptionConfig,
    DynamicStateDefaultsConfig,
    IslConfig,
    NetworkStateJobCreateRequest,
    NetworkStateScenarioConfig,
)
from backend.presets.components.ground_station_sets import (
    MANILA_DALIAN_GROUND_STATIONS,
    build_manila_dalian_ground_stations,
)
from backend.presets.components.reduced_kuiper_630 import (
    LIMITED_SATELLITE_IDX_MAP,
    LIMITED_SATELLITE_SET,
    MAX_GSL_LENGTH_M,
    MAX_ISL_LENGTH_M,
    NUM_ORBS,
    NUM_SATS_PER_ORB,
    SATELLITES,
    resolve_reduced_kuiper_630_gsl_interface_config,
    write_reduced_kuiper_630_filtered_isls_file,
    write_reduced_kuiper_630_tles_file,
)
from backend.request_builders.network_state import build_network_state_requests_from_scenario

TIME_STEP_MS = 100
DURATION_S = 200
NUM_THREADS = 1
STEP_1_ALGORITHMS = [
    DynamicStateAlgorithm.FREE_ONE_ONLY_OVER_ISLS,
    DynamicStateAlgorithm.FREE_GS_ONE_SAT_MANY_ONLY_OVER_ISLS,
]


def write_ground_stations_basic_file(output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8") as handle:
        for station in MANILA_DALIAN_GROUND_STATIONS:
            handle.write(
                f"{station.gid},{station.name},{station.latitude_deg},{station.longitude_deg},{station.elevation_m:g}\n"
            )


def write_tles_file(output_path: Path) -> None:
    write_reduced_kuiper_630_tles_file(output_path)


def write_filtered_isls_file(satgen_module, output_dir: Path) -> None:
    write_reduced_kuiper_630_filtered_isls_file(satgen_module, output_dir)


def resolve_gsl_interface_config(algorithm: DynamicStateAlgorithm, ground_station_count: int) -> Tuple[int, float]:
    return resolve_reduced_kuiper_630_gsl_interface_config(algorithm, ground_station_count)


def build_request(
    algorithm: DynamicStateAlgorithm,
    output_root: str = "generated",
    time_step_ms: int = TIME_STEP_MS,
    duration_s: int = DURATION_S,
    num_threads: int = NUM_THREADS,
) -> NetworkStateScenarioConfig:
    return NetworkStateScenarioConfig(
        base_name="reduced_kuiper_630",
        output_root=output_root,
        name_template="{base_name}_{algorithm}",
        ground_stations=build_manila_dalian_ground_stations(),
        description=DescriptionConfig(
            max_gsl_length_m=MAX_GSL_LENGTH_M,
            max_isl_length_m=MAX_ISL_LENGTH_M,
        ),
        dynamic_state_defaults=DynamicStateDefaultsConfig(
            time_step_ms=time_step_ms,
            duration_s=duration_s,
            num_threads=num_threads,
            print_logs=False,
        ),
        dynamic_state_algorithms=[algorithm],
        isl_config=IslConfig(
            selection=IslSelection.PLUS_GRID,
            isl_shift=0,
            idx_offset=0,
            limited_satellite_set=LIMITED_SATELLITE_SET,
            limited_satellite_idx_map=LIMITED_SATELLITE_IDX_MAP,
            num_orbits=NUM_ORBS,
            num_sats_per_orbit=NUM_SATS_PER_ORB,
        ),
        satellites=list(SATELLITES),
    )


def build_step_1_scenario(
    output_root: str = "generated",
    time_step_ms: int = TIME_STEP_MS,
    duration_s: int = DURATION_S,
    num_threads: int = NUM_THREADS,
) -> NetworkStateScenarioConfig:
    return NetworkStateScenarioConfig(
        base_name="reduced_kuiper_630",
        output_root=output_root,
        name_template="{base_name}_{algorithm}",
        ground_stations=build_manila_dalian_ground_stations(),
        description=DescriptionConfig(
            max_gsl_length_m=MAX_GSL_LENGTH_M,
            max_isl_length_m=MAX_ISL_LENGTH_M,
        ),
        dynamic_state_defaults=DynamicStateDefaultsConfig(
            time_step_ms=time_step_ms,
            duration_s=duration_s,
            num_threads=num_threads,
            print_logs=False,
        ),
        dynamic_state_algorithms=list(STEP_1_ALGORITHMS),
        isl_config=IslConfig(
            selection=IslSelection.PLUS_GRID,
            isl_shift=0,
            idx_offset=0,
            limited_satellite_set=LIMITED_SATELLITE_SET,
            limited_satellite_idx_map=LIMITED_SATELLITE_IDX_MAP,
            num_orbits=NUM_ORBS,
            num_sats_per_orbit=NUM_SATS_PER_ORB,
        ),
        satellites=list(SATELLITES),
    )


def build_step_1_requests(
    output_root: str = "generated",
    time_step_ms: int = TIME_STEP_MS,
    duration_s: int = DURATION_S,
    num_threads: int = NUM_THREADS,
) -> List[NetworkStateJobCreateRequest]:
    scenario = build_step_1_scenario(
        output_root=output_root,
        time_step_ms=time_step_ms,
        duration_s=duration_s,
        num_threads=num_threads,
    )
    return build_network_state_requests_from_scenario(scenario)
