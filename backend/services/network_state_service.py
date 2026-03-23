from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

from backend.domain.enums import DynamicStateAlgorithm, IslSelection
from backend.domain.models import (
    ArtifactRecord,
    GroundStation,
    NetworkStateJobCreateRequest,
    NetworkStateJobResult,
    TleSatellite,
)


def _ensure_satgen_import() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    satgenpy_dir = repo_root / "satgenpy"
    satgenpy_dir_str = str(satgenpy_dir)
    if satgenpy_dir_str not in sys.path:
        sys.path.insert(0, satgenpy_dir_str)


class NetworkStateService:
    def __init__(self) -> None:
        _ensure_satgen_import()
        import satgen  # type: ignore

        self._satgen = satgen

    def generate(self, request: NetworkStateJobCreateRequest, workspace: Path) -> NetworkStateJobResult:
        output_root = workspace / request.output_root
        output_dir = output_root / request.name
        output_dir.mkdir(parents=True, exist_ok=True)

        self._write_ground_stations(output_dir, request.ground_stations)
        self._write_tles(output_dir, request)
        self._write_isls(output_dir, request)
        self._write_description(output_dir, request)
        self._write_gsl_interfaces_info(output_dir, request)
        self._generate_dynamic_state(output_root, request)

        dynamic_state_dir = output_dir / self._dynamic_state_dir_name(request)
        artifacts = [
            ArtifactRecord(name="ground_stations.basic.txt", path=str(output_dir / "ground_stations.basic.txt")),
            ArtifactRecord(name="ground_stations.txt", path=str(output_dir / "ground_stations.txt")),
            ArtifactRecord(name="tles.txt", path=str(output_dir / "tles.txt")),
            ArtifactRecord(name="isls.txt", path=str(output_dir / "isls.txt")),
            ArtifactRecord(name="description.txt", path=str(output_dir / "description.txt")),
            ArtifactRecord(name="gsl_interfaces_info.txt", path=str(output_dir / "gsl_interfaces_info.txt")),
            ArtifactRecord(name=dynamic_state_dir.name, path=str(dynamic_state_dir)),
        ]
        return NetworkStateJobResult(
            name=request.name,
            output_directory=str(output_dir),
            dynamic_state_directory=str(dynamic_state_dir),
            artifacts=artifacts,
        )

    def _write_ground_stations(self, output_dir: Path, ground_stations: List[GroundStation]) -> None:
        basic_path = output_dir / "ground_stations.basic.txt"
        with basic_path.open("w", encoding="utf-8") as handle:
            for station in ground_stations:
                elevation = int(station.elevation_m) if float(station.elevation_m).is_integer() else station.elevation_m
                handle.write(
                    f"{station.gid},{station.name},"
                    f"{station.latitude_deg},{station.longitude_deg},{elevation}\n"
                )
        self._satgen.extend_ground_stations(str(basic_path), str(output_dir / "ground_stations.txt"))

    def _write_tles(self, output_dir: Path, request: NetworkStateJobCreateRequest) -> None:
        tles_path = output_dir / "tles.txt"
        if request.satellites:
            self._write_inline_tles(tles_path, request.satellites)
            return
        if request.manual_constellation:
            config = request.manual_constellation
            self._satgen.generate_tles_from_scratch_manual(
                str(tles_path),
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

    def _write_inline_tles(self, tles_path: Path, satellites: List[TleSatellite]) -> None:
        with tles_path.open("w", encoding="utf-8") as handle:
            handle.write(f"1 {len(satellites)}\n")
            for satellite in satellites:
                handle.write(f"{satellite.name}\n")
                handle.write(f"{satellite.tle_line1}\n")
                handle.write(f"{satellite.tle_line2}\n")

    def _write_isls(self, output_dir: Path, request: NetworkStateJobCreateRequest) -> None:
        isls_path = output_dir / "isls.txt"
        isl_config = request.isl_config
        if isl_config.selection == IslSelection.NONE:
            self._satgen.generate_empty_isls(str(isls_path))
            return

        num_orbits = isl_config.num_orbits or request.manual_constellation and request.manual_constellation.num_orbits
        num_sats_per_orbit = (
            isl_config.num_sats_per_orbit
            or request.manual_constellation
            and request.manual_constellation.num_sats_per_orbit
        )
        if num_orbits is None or num_sats_per_orbit is None:
            raise ValueError("ISL generation requires orbit counts via isl_config or manual_constellation")

        complete_isls = self._satgen.generate_plus_grid_isls(
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

    def _write_description(self, output_dir: Path, request: NetworkStateJobCreateRequest) -> None:
        self._satgen.generate_description(
            str(output_dir / "description.txt"),
            request.description.max_gsl_length_m,
            request.description.max_isl_length_m,
        )

    def _write_gsl_interfaces_info(self, output_dir: Path, request: NetworkStateJobCreateRequest) -> None:
        ground_stations = self._satgen.read_ground_stations_extended(str(output_dir / "ground_stations.txt"))
        satellite_count = self._resolve_satellite_count(request)
        interfaces_per_satellite = self._resolve_gsl_interfaces_per_satellite(
            request.dynamic_state.algorithm,
            len(ground_stations),
        )
        satellite_bandwidth = float(interfaces_per_satellite)

        self._satgen.generate_simple_gsl_interfaces_info(
            str(output_dir / "gsl_interfaces_info.txt"),
            satellite_count,
            len(ground_stations),
            interfaces_per_satellite,
            1,
            satellite_bandwidth,
            1,
        )

    def _generate_dynamic_state(self, output_root: Path, request: NetworkStateJobCreateRequest) -> None:
        config = request.dynamic_state
        self._satgen.help_dynamic_state(
            str(output_root),
            config.num_threads,
            request.name,
            config.time_step_ms,
            config.duration_s,
            request.description.max_gsl_length_m,
            request.description.max_isl_length_m,
            config.algorithm.value,
            config.print_logs,
            config.start_time_s,
        )

    def _resolve_satellite_count(self, request: NetworkStateJobCreateRequest) -> int:
        if request.satellites:
            return len(request.satellites)
        if request.manual_constellation:
            return request.manual_constellation.num_orbits * request.manual_constellation.num_sats_per_orbit
        raise ValueError("Unable to determine satellite count")

    def _resolve_gsl_interfaces_per_satellite(
        self,
        algorithm: DynamicStateAlgorithm,
        ground_station_count: int,
    ) -> int:
        if algorithm in {
            DynamicStateAlgorithm.FREE_ONE_ONLY_GS_RELAYS,
            DynamicStateAlgorithm.FREE_ONE_ONLY_OVER_ISLS,
        }:
            return 1
        if algorithm in {
            DynamicStateAlgorithm.FREE_GS_ONE_SAT_MANY_ONLY_OVER_ISLS,
            DynamicStateAlgorithm.PAIRED_MANY_ONLY_OVER_ISLS,
        }:
            return ground_station_count
        raise ValueError(f"Unsupported dynamic state algorithm: {algorithm}")

    def _dynamic_state_dir_name(self, request: NetworkStateJobCreateRequest) -> str:
        return (
            f"dynamic_state_{request.dynamic_state.time_step_ms}"
            f"ms_for_{request.dynamic_state.duration_s}s"
        )


_network_state_service = None  # type: Optional[NetworkStateService]


def get_network_state_service() -> NetworkStateService:
    global _network_state_service
    if _network_state_service is None:
        _network_state_service = NetworkStateService()
    return _network_state_service
