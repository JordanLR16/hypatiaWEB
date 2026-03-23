from __future__ import annotations

import filecmp
import shutil
import sys
from pathlib import Path
from typing import List, Set

from backend.presets.manila_dalian_over_kuiper import (
    GROUND_STATIONS,
    LIMITED_SATELLITE_IDX_MAP,
    LIMITED_SATELLITE_SET,
    MAX_GSL_LENGTH_M,
    MAX_ISL_LENGTH_M,
    NUM_ORBS,
    NUM_SATS_PER_ORB,
    SATELLITES,
    TIME_STEP_MS,
    DURATION_S,
    build_step_1_requests,
)
from backend.services.network_state_service import NetworkStateService


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


def _write_reference_outputs(reference_root: Path) -> None:
    _ensure_satgen_import()
    import satgen  # type: ignore

    generated_root = reference_root / "temp" / "gen_data"
    generated_root.mkdir(parents=True, exist_ok=True)

    requests = build_step_1_requests(output_root="temp/gen_data")
    for request in requests:
        output_dir = generated_root / request.name
        output_dir.mkdir(parents=True, exist_ok=True)

        with (output_dir / "ground_stations.basic.txt").open("w", encoding="utf-8") as handle:
            for station in GROUND_STATIONS:
                handle.write(
                    f"{station.gid},{station.name},{station.latitude_deg},{station.longitude_deg},{station.elevation_m:g}\n"
                )
        satgen.extend_ground_stations(
            str(output_dir / "ground_stations.basic.txt"),
            str(output_dir / "ground_stations.txt"),
        )

        with (output_dir / "tles.txt").open("w", encoding="utf-8") as handle:
            handle.write(f"1 {len(SATELLITES)}\n")
            for satellite in SATELLITES:
                handle.write(f"{satellite.name}\n")
                handle.write(f"{satellite.tle_line1}\n")
                handle.write(f"{satellite.tle_line2}\n")

        complete_isls = satgen.generate_plus_grid_isls(
            str(output_dir / "isls_complete.temp.txt"),
            NUM_ORBS,
            NUM_SATS_PER_ORB,
            isl_shift=0,
            idx_offset=0,
        )
        limited_set = set(LIMITED_SATELLITE_SET)
        with (output_dir / "isls.txt").open("w", encoding="utf-8") as handle:
            for left, right in complete_isls:
                if left in limited_set and right in limited_set:
                    handle.write(
                        f"{LIMITED_SATELLITE_IDX_MAP[left]} {LIMITED_SATELLITE_IDX_MAP[right]}\n"
                    )

        satgen.generate_description(
            str(output_dir / "description.txt"),
            MAX_GSL_LENGTH_M,
            MAX_ISL_LENGTH_M,
        )

        ground_stations = satgen.read_ground_stations_extended(str(output_dir / "ground_stations.txt"))
        if request.dynamic_state.algorithm.value == "algorithm_free_one_only_over_isls":
            interfaces_per_satellite = 1
            satellite_bandwidth = 1.0
        else:
            interfaces_per_satellite = len(ground_stations)
            satellite_bandwidth = float(len(ground_stations))

        satgen.generate_simple_gsl_interfaces_info(
            str(output_dir / "gsl_interfaces_info.txt"),
            len(SATELLITES),
            len(ground_stations),
            interfaces_per_satellite,
            1,
            satellite_bandwidth,
            1,
        )

        satgen.help_dynamic_state(
            str(generated_root),
            1,
            request.name,
            TIME_STEP_MS,
            DURATION_S,
            MAX_GSL_LENGTH_M,
            MAX_ISL_LENGTH_M,
            request.dynamic_state.algorithm.value,
            False,
        )


def _write_backend_outputs(backend_root: Path) -> None:
    _clean_dir(backend_root)
    service = NetworkStateService()
    for request in build_step_1_requests(output_root="temp/gen_data"):
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


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    verification_root = repo_root / "backend_workspaces" / "step1_parity"
    reference_root = verification_root / "reference"
    backend_root = verification_root / "backend"

    _clean_dir(reference_root)
    _clean_dir(backend_root)

    print("Generating reference outputs...")
    _write_reference_outputs(reference_root)
    print("Generating backend outputs...")
    _write_backend_outputs(backend_root)

    reference_dir = reference_root / "temp" / "gen_data"
    backend_dir = backend_root / "temp" / "gen_data"
    print("Comparing generated artifacts...")
    _assert_directories_match(reference_dir, backend_dir)
    print("Parity check passed.")


if __name__ == "__main__":
    main()
