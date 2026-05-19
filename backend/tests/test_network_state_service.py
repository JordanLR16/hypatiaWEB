import sys
import shutil
import unittest
from uuid import uuid4
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from backend.domain.enums import DynamicStateAlgorithm, IslSelection
from backend.domain.models import (
    DescriptionConfig,
    DynamicStateConfig,
    GroundStation,
    IslConfig,
    ManualConstellationConfig,
    NetworkStateJobCreateRequest,
    TleSatellite,
)
from backend.services.network_state_service import NetworkStateService


TEST_TMP_ROOT = Path(__file__).resolve().parents[2] / "backend_workspaces" / "test_tmp"


class _FakeSatgen:
    def __init__(self) -> None:
        self.calls = []

    def extend_ground_stations(self, basic_path: str, output_path: str) -> None:
        self.calls.append(("extend_ground_stations", basic_path, output_path))
        lines = Path(basic_path).read_text(encoding="utf-8").splitlines()
        Path(output_path).write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    def generate_tles_from_scratch_manual(
        self,
        output_path: str,
        name: str,
        num_orbits: int,
        num_sats_per_orbit: int,
        phase_diff: bool,
        inclination_degree: float,
        eccentricity: float,
        arg_of_perigee_degree: float,
        mean_motion_rev_per_day: float,
        start_time_s: int,
    ) -> None:
        self.calls.append(
            (
                "generate_tles_from_scratch_manual",
                output_path,
                name,
                num_orbits,
                num_sats_per_orbit,
                phase_diff,
                inclination_degree,
                eccentricity,
                arg_of_perigee_degree,
                mean_motion_rev_per_day,
                start_time_s,
            )
        )
        Path(output_path).write_text(
            f"manual:{name}:{num_orbits}:{num_sats_per_orbit}:{start_time_s}\n",
            encoding="utf-8",
        )

    def generate_empty_isls(self, output_path: str) -> None:
        self.calls.append(("generate_empty_isls", output_path))
        Path(output_path).write_text("", encoding="utf-8")

    def generate_plus_grid_isls(
        self,
        output_path: str,
        num_orbits: int,
        num_sats_per_orbit: int,
        isl_shift: int = 0,
        idx_offset: int = 0,
    ):
        self.calls.append(
            (
                "generate_plus_grid_isls",
                output_path,
                num_orbits,
                num_sats_per_orbit,
                isl_shift,
                idx_offset,
            )
        )
        Path(output_path).write_text("0 1\n1 2\n", encoding="utf-8")
        return [(0, 1), (1, 2)]

    def generate_description(self, output_path: str, max_gsl_length_m: float, max_isl_length_m: float) -> None:
        self.calls.append(("generate_description", output_path, max_gsl_length_m, max_isl_length_m))
        Path(output_path).write_text(
            f"gsl={max_gsl_length_m},isl={max_isl_length_m}\n",
            encoding="utf-8",
        )

    def read_ground_stations_extended(self, output_path: str):
        self.calls.append(("read_ground_stations_extended", output_path))
        return [line for line in Path(output_path).read_text(encoding="utf-8").splitlines() if line]

    def generate_simple_gsl_interfaces_info(
        self,
        output_path: str,
        satellite_count: int,
        ground_station_count: int,
        interfaces_per_satellite: int,
        ground_station_interfaces: int,
        satellite_bandwidth: float,
        ground_station_bandwidth: int,
    ) -> None:
        self.calls.append(
            (
                "generate_simple_gsl_interfaces_info",
                output_path,
                satellite_count,
                ground_station_count,
                interfaces_per_satellite,
                ground_station_interfaces,
                satellite_bandwidth,
                ground_station_bandwidth,
            )
        )
        Path(output_path).write_text(
            (
                f"sats={satellite_count},gs={ground_station_count},"
                f"ifs={interfaces_per_satellite},bw={satellite_bandwidth}\n"
            ),
            encoding="utf-8",
        )

    def help_dynamic_state(
        self,
        output_root: str,
        num_threads: int,
        request_name: str,
        time_step_ms: int,
        duration_s: int,
        max_gsl_length_m: float,
        max_isl_length_m: float,
        algorithm: str,
        print_logs: bool,
        start_time_s: int = 0,
    ) -> None:
        self.calls.append(
            (
                "help_dynamic_state",
                output_root,
                num_threads,
                request_name,
                time_step_ms,
                duration_s,
                max_gsl_length_m,
                max_isl_length_m,
                algorithm,
                print_logs,
                start_time_s,
            )
        )
        dynamic_state_dir = Path(output_root) / request_name / f"dynamic_state_{time_step_ms}ms_for_{duration_s}s"
        dynamic_state_dir.mkdir(parents=True, exist_ok=True)
        (dynamic_state_dir / "fstate_0.txt").write_text("ok\n", encoding="utf-8")


def _build_request_with_inline_satellite() -> NetworkStateJobCreateRequest:
    return NetworkStateJobCreateRequest(
        name="scenario_request",
        output_root="generated",
        ground_stations=[
            GroundStation(
                gid=1,
                name="Station A",
                latitude_deg=14.5,
                longitude_deg=121.0,
                elevation_m=15.0,
            )
        ],
        description=DescriptionConfig(
            max_gsl_length_m=111.0,
            max_isl_length_m=222.0,
        ),
        dynamic_state=DynamicStateConfig(
            algorithm=DynamicStateAlgorithm.FREE_ONE_ONLY_OVER_ISLS,
            time_step_ms=1000,
            duration_s=30,
            num_threads=2,
            start_time_s=9,
            print_logs=True,
        ),
        isl_config=IslConfig(selection=IslSelection.NONE),
        satellites=[
            TleSatellite(
                sid=0,
                name="InlineSat-0",
                tle_line1="1 00001U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    01",
                tle_line2="2 00001  53.0000  42.0000 0000001   0.0000 142.9412 14.80000000    00",
            )
        ],
    )


class TestNetworkStateService(unittest.TestCase):
    def setUp(self) -> None:
        TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)

    def _make_workspace(self, label: str) -> Path:
        workspace = TEST_TMP_ROOT / f"{label}_{uuid4().hex[:8]}"
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace

    def test_generate_creates_artifacts_for_non_preset_request(self) -> None:
        fake_satgen = _FakeSatgen()
        with patch.dict(sys.modules, {"satgen": fake_satgen}):
            service = NetworkStateService()

        request = _build_request_with_inline_satellite()
        workspace = self._make_workspace("inline")
        try:
            result = service.generate(request=request, workspace=workspace)
            output_dir = Path(result.output_directory)
            self.assertTrue((output_dir / "ground_stations.basic.txt").exists())
            self.assertTrue((output_dir / "ground_stations.txt").exists())
            self.assertTrue((output_dir / "tles.txt").exists())
            self.assertTrue((output_dir / "isls.txt").exists())
            self.assertTrue((output_dir / "description.txt").exists())
            self.assertTrue((output_dir / "gsl_interfaces_info.txt").exists())
            self.assertTrue(Path(result.dynamic_state_directory).exists())
            self.assertTrue((Path(result.dynamic_state_directory) / "fstate_0.txt").exists())
            self.assertEqual(7, len(result.artifacts))
            self.assertIn("InlineSat-0", (output_dir / "tles.txt").read_text(encoding="utf-8"))
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

        self.assertIn(
            ("generate_empty_isls", str(Path(result.output_directory) / "isls.txt")),
            fake_satgen.calls,
        )

    def test_generate_uses_manual_constellation_when_inline_satellites_are_absent(self) -> None:
        fake_satgen = _FakeSatgen()
        with patch.dict(sys.modules, {"satgen": fake_satgen}):
            service = NetworkStateService()

        request = NetworkStateJobCreateRequest(
            name="manual_request",
            output_root="generated",
            ground_stations=[
                GroundStation(
                    gid=5,
                    name="Station B",
                    latitude_deg=35.0,
                    longitude_deg=139.0,
                    elevation_m=20.0,
                )
            ],
            description=DescriptionConfig(
                max_gsl_length_m=333.0,
                max_isl_length_m=444.0,
            ),
            dynamic_state=DynamicStateConfig(
                algorithm=DynamicStateAlgorithm.FREE_GS_ONE_SAT_MANY_ONLY_OVER_ISLS,
                time_step_ms=2000,
                duration_s=45,
            ),
            isl_config=IslConfig(
                selection=IslSelection.PLUS_GRID,
                num_orbits=3,
                num_sats_per_orbit=4,
            ),
            manual_constellation=ManualConstellationConfig(
                name="ManualNet",
                num_orbits=3,
                num_sats_per_orbit=4,
                phase_diff=False,
                inclination_degree=53.0,
                eccentricity=0.0000001,
                arg_of_perigee_degree=0.0,
                mean_motion_rev_per_day=15.0,
            ),
        )

        workspace = self._make_workspace("manual")
        try:
            result = service.generate(request=request, workspace=workspace)
            output_dir = Path(result.output_directory)
            self.assertIn("manual:ManualNet:3:4:0", (output_dir / "tles.txt").read_text(encoding="utf-8"))
            self.assertEqual("0 1\n1 2\n", (output_dir / "isls.txt").read_text(encoding="utf-8"))
            self.assertIn("ifs=1", (output_dir / "gsl_interfaces_info.txt").read_text(encoding="utf-8"))
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

        manual_calls = [call for call in fake_satgen.calls if call[0] == "generate_tles_from_scratch_manual"]
        self.assertEqual(1, len(manual_calls))

    def test_generate_rejects_missing_orbit_counts_for_plus_grid_isls(self) -> None:
        with self.assertRaisesRegex(
            ValidationError,
            "PLUS_GRID ISL generation requires",
        ):
            NetworkStateJobCreateRequest(
                name="invalid_request",
                output_root="generated",
                ground_stations=[
                    GroundStation(
                        gid=1,
                        name="Station A",
                        latitude_deg=10.0,
                        longitude_deg=20.0,
                        elevation_m=0.0,
                    )
                ],
                description=DescriptionConfig(
                    max_gsl_length_m=111.0,
                    max_isl_length_m=222.0,
                ),
                dynamic_state=DynamicStateConfig(
                    algorithm=DynamicStateAlgorithm.FREE_ONE_ONLY_OVER_ISLS,
                    time_step_ms=1000,
                    duration_s=30,
                ),
                isl_config=IslConfig(selection=IslSelection.PLUS_GRID),
                satellites=[
                    TleSatellite(
                        sid=0,
                        name="InlineSat-0",
                        tle_line1="1 00001U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    01",
                        tle_line2="2 00001  53.0000  42.0000 0000001   0.0000 142.9412 14.80000000    00",
                    )
                ],
            )
