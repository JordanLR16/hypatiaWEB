from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path
from typing import List, Optional, Set

from backend.domain.enums import DynamicStateAlgorithm, IslSelection
from backend.domain.models import GroundStation, NetworkStateJobCreateRequest, TleSatellite
from backend.presets.registry import get_preset_builder, list_presets
from backend.services.network_state_service import NetworkStateService

DEFAULT_SMOKE_TIME_STEP_MS = 100000
DEFAULT_SMOKE_DURATION_S = 1000
PRESET_NAME = "manila_dalian_over_kuiper"


def _ensure_satgen_import() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    satgenpy_dir = repo_root / "satgenpy"
    satgenpy_dir_str = str(satgenpy_dir)
    if satgenpy_dir_str not in sys.path:
        sys.path.insert(0, satgenpy_dir_str)


def _clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _write_ground_stations_basic_file(output_path: Path, ground_stations: List[GroundStation]) -> None:
    with output_path.open("w", encoding="utf-8") as handle:
        for station in ground_stations:
            elevation = int(station.elevation_m) if float(station.elevation_m).is_integer() else station.elevation_m
            handle.write(
                f"{station.gid},{station.name},"
                f"{station.latitude_deg},{station.longitude_deg},{elevation}\n"
            )


def _write_tles_file(satgen_module, output_path: Path, request: NetworkStateJobCreateRequest) -> None:
    if request.satellites:
        _write_inline_tles(output_path, request.satellites)
        return
    if request.manual_constellation:
        config = request.manual_constellation
        satgen_module.generate_tles_from_scratch_manual(
            str(output_path),
            config.name,
            config.num_orbits,
            config.num_sats_per_orbit,
            config.phase_diff,
            config.inclination_degree,
            config.eccentricity,
            config.arg_of_perigee_degree,
            config.mean_motion_rev_per_day,
            request.dynamic_state.start_time_s,
        )
        return
    raise ValueError("Either 'satellites' or 'manual_constellation' must be supplied")


def _write_inline_tles(output_path: Path, satellites: List[TleSatellite]) -> None:
    with output_path.open("w", encoding="utf-8") as handle:
        handle.write(f"1 {len(satellites)}\n")
        for satellite in satellites:
            handle.write(f"{satellite.name}\n")
            handle.write(f"{satellite.tle_line1}\n")
            handle.write(f"{satellite.tle_line2}\n")


def _write_isls_file(satgen_module, output_dir: Path, request: NetworkStateJobCreateRequest) -> None:
    isls_path = output_dir / "isls.txt"
    isl_config = request.isl_config
    if isl_config.selection == IslSelection.NONE:
        satgen_module.generate_empty_isls(str(isls_path))
        return

    num_orbits = isl_config.num_orbits or (
        request.manual_constellation.num_orbits if request.manual_constellation else None
    )
    num_sats_per_orbit = isl_config.num_sats_per_orbit or (
        request.manual_constellation.num_sats_per_orbit if request.manual_constellation else None
    )
    if num_orbits is None or num_sats_per_orbit is None:
        raise ValueError("ISL generation requires orbit counts via isl_config or manual_constellation")

    complete_isls = satgen_module.generate_plus_grid_isls(
        str(output_dir / "isls_complete.temp.txt"),
        num_orbits,
        num_sats_per_orbit,
        isl_shift=isl_config.isl_shift,
        idx_offset=isl_config.idx_offset,
    )

    if not isl_config.limited_satellite_set:
        with isls_path.open("w", encoding="utf-8") as handle:
            for left, right in complete_isls:
                handle.write(f"{left} {right}\n")
        return

    limited_set = set(isl_config.limited_satellite_set)
    idx_map = isl_config.limited_satellite_idx_map or {}
    with isls_path.open("w", encoding="utf-8") as handle:
        for left, right in complete_isls:
            if left not in limited_set or right not in limited_set:
                continue
            handle.write(f"{idx_map.get(left, left)} {idx_map.get(right, right)}\n")


def _resolve_gsl_interface_config(
    algorithm: DynamicStateAlgorithm,
    ground_station_count: int,
) -> tuple[int, float]:
    if algorithm in {
        DynamicStateAlgorithm.FREE_ONE_ONLY_GS_RELAYS,
        DynamicStateAlgorithm.FREE_ONE_ONLY_OVER_ISLS,
    }:
        return 1, 1.0
    if algorithm in {
        DynamicStateAlgorithm.FREE_GS_ONE_SAT_MANY_ONLY_OVER_ISLS,
        DynamicStateAlgorithm.PAIRED_MANY_ONLY_OVER_ISLS,
    }:
        return ground_station_count, float(ground_station_count)
    raise ValueError(f"Unsupported dynamic state algorithm: {algorithm.value}")


def _build_requests(
    preset_name: str,
    output_root: str,
    time_step_ms: Optional[int] = None,
    duration_s: Optional[int] = None,
) -> List[NetworkStateJobCreateRequest]:
    preset_builder = get_preset_builder(preset_name)
    kwargs = {"output_root": output_root}
    if time_step_ms is not None:
        kwargs["time_step_ms"] = time_step_ms
    if duration_s is not None:
        kwargs["duration_s"] = duration_s
    return preset_builder(**kwargs)


def _write_reference_outputs(reference_root: Path, requests: List[NetworkStateJobCreateRequest]) -> None:
    _ensure_satgen_import()
    import satgen  # type: ignore

    generated_root = reference_root / "temp" / "gen_data"
    generated_root.mkdir(parents=True, exist_ok=True)

    for request in requests:
        output_dir = generated_root / request.name
        output_dir.mkdir(parents=True, exist_ok=True)

        _write_ground_stations_basic_file(output_dir / "ground_stations.basic.txt", request.ground_stations)
        satgen.extend_ground_stations(
            str(output_dir / "ground_stations.basic.txt"),
            str(output_dir / "ground_stations.txt"),
        )

        _write_tles_file(satgen, output_dir / "tles.txt", request)
        _write_isls_file(satgen, output_dir, request)

        satgen.generate_description(
            str(output_dir / "description.txt"),
            request.description.max_gsl_length_m,
            request.description.max_isl_length_m,
        )

        ground_stations = satgen.read_ground_stations_extended(str(output_dir / "ground_stations.txt"))
        interfaces_per_satellite, satellite_bandwidth = _resolve_gsl_interface_config(
            request.dynamic_state.algorithm,
            len(ground_stations),
        )

        satgen.generate_simple_gsl_interfaces_info(
            str(output_dir / "gsl_interfaces_info.txt"),
            _resolve_satellite_count(request),
            len(ground_stations),
            interfaces_per_satellite,
            1,
            satellite_bandwidth,
            1,
        )

        satgen.help_dynamic_state(
            str(generated_root),
            request.dynamic_state.num_threads,
            request.name,
            request.dynamic_state.time_step_ms,
            request.dynamic_state.duration_s,
            request.description.max_gsl_length_m,
            request.description.max_isl_length_m,
            request.dynamic_state.algorithm.value,
            request.dynamic_state.print_logs,
            request.dynamic_state.start_time_s,
        )


def _resolve_satellite_count(request: NetworkStateJobCreateRequest) -> int:
    if request.satellites:
        return len(request.satellites)
    if request.manual_constellation:
        return request.manual_constellation.num_orbits * request.manual_constellation.num_sats_per_orbit
    raise ValueError("Unable to determine satellite count")


def _write_backend_outputs(backend_root: Path, requests: List[NetworkStateJobCreateRequest]) -> None:
    _clean_dir(backend_root)
    service = NetworkStateService()
    for request in requests:
        service.generate(request=request, workspace=backend_root)


def _collect_relative_files(root: Path) -> Set[str]:
    return {
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file()
    }


def _assert_directories_match(reference_dir: Path, backend_dir: Path) -> None:
    reference_files = _collect_relative_files(reference_dir)
    backend_files = _collect_relative_files(backend_dir)
    if reference_files != backend_files:
        missing = sorted(reference_files - backend_files)
        extra = sorted(backend_files - reference_files)
        raise AssertionError(
            "File sets differ.\n"
            f"Missing in backend: {missing[:10]}\n"
            f"Extra in backend: {extra[:10]}"
        )

    mismatches: List[str] = []
    for relative_path in sorted(reference_files):
        left = reference_dir / relative_path
        right = backend_dir / relative_path
        if not filecmp.cmp(left, right, shallow=False):
            mismatches.append(relative_path)

    if mismatches:
        raise AssertionError(f"File contents differ for {len(mismatches)} files. Sample: {mismatches[:10]}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare legacy step-1 outputs against backend-generated outputs.",
    )
    parser.add_argument(
        "--preset",
        default=PRESET_NAME,
        choices=list_presets(),
        help="Preset name registered in backend.presets.registry.",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run the preset's default dynamic-state configuration.",
    )
    parser.add_argument(
        "--time-step-ms",
        type=int,
        default=DEFAULT_SMOKE_TIME_STEP_MS,
        help="Dynamic-state time step in milliseconds for the parity run.",
    )
    parser.add_argument(
        "--duration-s",
        type=int,
        default=DEFAULT_SMOKE_DURATION_S,
        help="Simulation duration in seconds for the parity run.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    full_requests = _build_requests(
        preset_name=args.preset,
        output_root="temp/gen_data",
    )
    if not full_requests:
        raise ValueError(f"Preset '{args.preset}' did not produce any requests")

    if args.full:
        requests = full_requests
    else:
        requests = _build_requests(
            preset_name=args.preset,
            output_root="temp/gen_data",
            time_step_ms=args.time_step_ms,
            duration_s=args.duration_s,
        )

    time_step_ms = requests[0].dynamic_state.time_step_ms
    duration_s = requests[0].dynamic_state.duration_s

    repo_root = Path(__file__).resolve().parents[2]
    verification_root = repo_root / "backend_workspaces" / "step1_parity"
    reference_root = verification_root / "reference"
    backend_root = verification_root / "backend"

    _clean_dir(reference_root)
    _clean_dir(backend_root)

    print(
        "Generating reference outputs "
        f"for preset='{args.preset}' "
        f"(time_step_ms={time_step_ms}, duration_s={duration_s})..."
    )
    _write_reference_outputs(reference_root, requests)
    print("Generating backend outputs...")
    _write_backend_outputs(backend_root, requests)

    reference_dir = reference_root / "temp" / "gen_data"
    backend_dir = backend_root / "temp" / "gen_data"
    print("Comparing generated artifacts...")
    _assert_directories_match(reference_dir, backend_dir)
    print("Parity check passed.")


if __name__ == "__main__":
    main()
