import unittest

from backend.domain.enums import DynamicStateAlgorithm, IslSelection
from backend.domain.models import (
    DescriptionConfig,
    DynamicStateDefaultsConfig,
    GroundStation,
    IslConfig,
    ManualConstellationConfig,
    NetworkStateScenarioConfig,
    TleSatellite,
)
from backend.request_builders.network_state import build_network_state_requests_from_scenario


def _build_ground_station() -> GroundStation:
    return GroundStation(
        gid=1,
        name="Test Station",
        latitude_deg=14.5995,
        longitude_deg=120.9842,
        elevation_m=12.0,
    )


def _build_satellite() -> TleSatellite:
    return TleSatellite(
        sid=7,
        name="TestSat-7",
        tle_line1="1 00007U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    07",
        tle_line2="2 00007  53.0000  42.0000 0000001   0.0000 142.9412 14.80000000    00",
    )


class TestBuildNetworkStateRequestsFromScenario(unittest.TestCase):
    def test_builds_one_request_per_algorithm(self) -> None:
        scenario = NetworkStateScenarioConfig(
            base_name="scenario_a",
            output_root="generated",
            name_template="{base_name}_{algorithm}",
            ground_stations=[_build_ground_station()],
            description=DescriptionConfig(
                max_gsl_length_m=1000.0,
                max_isl_length_m=2000.0,
            ),
            dynamic_state_defaults=DynamicStateDefaultsConfig(
                time_step_ms=500,
                duration_s=60,
                num_threads=2,
                start_time_s=3,
                print_logs=True,
            ),
            dynamic_state_algorithms=[
                DynamicStateAlgorithm.FREE_ONE_ONLY_OVER_ISLS,
                DynamicStateAlgorithm.FREE_GS_ONE_SAT_MANY_ONLY_OVER_ISLS,
            ],
            isl_config=IslConfig(selection=IslSelection.NONE),
            satellites=[_build_satellite()],
        )

        requests = build_network_state_requests_from_scenario(scenario)

        self.assertEqual(2, len(requests))
        self.assertEqual(
            [
                "scenario_a_algorithm_free_one_only_over_isls",
                "scenario_a_algorithm_free_gs_one_sat_many_only_over_isls",
            ],
            [request.name for request in requests],
        )
        self.assertEqual([500, 500], [request.dynamic_state.time_step_ms for request in requests])
        self.assertEqual([60, 60], [request.dynamic_state.duration_s for request in requests])
        self.assertEqual([2, 2], [request.dynamic_state.num_threads for request in requests])
        self.assertEqual([3, 3], [request.dynamic_state.start_time_s for request in requests])
        self.assertEqual([True, True], [request.dynamic_state.print_logs for request in requests])
        self.assertEqual(IslSelection.NONE, requests[0].isl_config.selection)
        self.assertEqual("TestSat-7", requests[0].satellites[0].name)

    def test_supports_manual_constellation_scenarios(self) -> None:
        scenario = NetworkStateScenarioConfig(
            base_name="manual_case",
            ground_stations=[_build_ground_station()],
            description=DescriptionConfig(
                max_gsl_length_m=123.0,
                max_isl_length_m=456.0,
            ),
            dynamic_state_defaults=DynamicStateDefaultsConfig(
                time_step_ms=100,
                duration_s=20,
            ),
            dynamic_state_algorithms=[DynamicStateAlgorithm.FREE_ONE_ONLY_GS_RELAYS],
            manual_constellation=ManualConstellationConfig(
                name="ManualNet",
                num_orbits=3,
                num_sats_per_orbit=4,
                phase_diff=True,
                inclination_degree=53.0,
                eccentricity=0.0000001,
                arg_of_perigee_degree=0.0,
                mean_motion_rev_per_day=15.0,
            ),
        )

        requests = build_network_state_requests_from_scenario(scenario)

        self.assertEqual(1, len(requests))
        self.assertIsNone(requests[0].satellites)
        self.assertEqual("ManualNet", requests[0].manual_constellation.name)
        self.assertEqual(3, requests[0].manual_constellation.num_orbits)
        self.assertEqual(4, requests[0].manual_constellation.num_sats_per_orbit)

    def test_rejects_scenarios_without_satellites_or_manual_constellation(self) -> None:
        scenario = NetworkStateScenarioConfig(
            base_name="invalid_case",
            ground_stations=[_build_ground_station()],
            description=DescriptionConfig(
                max_gsl_length_m=123.0,
                max_isl_length_m=456.0,
            ),
            dynamic_state_defaults=DynamicStateDefaultsConfig(
                time_step_ms=100,
                duration_s=20,
            ),
            dynamic_state_algorithms=[DynamicStateAlgorithm.FREE_ONE_ONLY_GS_RELAYS],
        )

        with self.assertRaisesRegex(
            ValueError,
            "requires either 'satellites' or 'manual_constellation'",
        ):
            build_network_state_requests_from_scenario(scenario)
