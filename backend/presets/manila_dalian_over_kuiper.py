from __future__ import annotations

import math
from typing import List

from backend.domain.enums import DynamicStateAlgorithm, IslSelection
from backend.domain.models import (
    DescriptionConfig,
    DynamicStateConfig,
    GroundStation,
    IslConfig,
    NetworkStateJobCreateRequest,
    TleSatellite,
)

# WGS72 value; taken from the original Hypatia integration test setup.
EARTH_RADIUS_M = 6378135.0
ALTITUDE_M = 630000
SATELLITE_CONE_RADIUS_M = ALTITUDE_M / math.tan(math.radians(30.0))
MAX_GSL_LENGTH_M = math.sqrt(SATELLITE_CONE_RADIUS_M ** 2 + ALTITUDE_M ** 2)
MAX_ISL_LENGTH_M = 2 * math.sqrt((EARTH_RADIUS_M + ALTITUDE_M) ** 2 - (EARTH_RADIUS_M + 80000) ** 2)
NUM_ORBS = 34
NUM_SATS_PER_ORB = 34
TIME_STEP_MS = 100
DURATION_S = 200
NUM_THREADS = 1

GROUND_STATIONS = [
    GroundStation(gid=0, name="Manila", latitude_deg=14.6042, longitude_deg=120.9822, elevation_m=0.0),
    GroundStation(gid=1, name="Dalian", latitude_deg=38.913811, longitude_deg=121.602322, elevation_m=0.0),
]

LIMITED_SATELLITE_SET = [
    183,
    184,
    215,
    216,
    217,
    218,
    249,
    250,
    615,
    616,
    647,
    648,
    649,
    650,
    682,
    683,
    684,
]

LIMITED_SATELLITE_IDX_MAP = {
    183: 0,
    184: 1,
    215: 2,
    216: 3,
    217: 4,
    218: 5,
    249: 6,
    250: 7,
    615: 8,
    616: 9,
    647: 10,
    648: 11,
    649: 12,
    650: 13,
    682: 14,
    683: 15,
    684: 16,
}

SATELLITES = [
    TleSatellite(
        sid=0,
        name="Kuiper-630 0",
        tle_line1="1 00184U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    06",
        tle_line2="2 00184  51.9000  52.9412 0000001   0.0000 142.9412 14.80000000    00",
    ),
    TleSatellite(
        sid=1,
        name="Kuiper-630 1",
        tle_line1="1 00185U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    07",
        tle_line2="2 00185  51.9000  52.9412 0000001   0.0000 153.5294 14.80000000    07",
    ),
    TleSatellite(
        sid=2,
        name="Kuiper-630 2",
        tle_line1="1 00216U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    02",
        tle_line2="2 00216  51.9000  63.5294 0000001   0.0000 116.4706 14.80000000    04",
    ),
    TleSatellite(
        sid=3,
        name="Kuiper-630 3",
        tle_line1="1 00217U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    03",
        tle_line2="2 00217  51.9000  63.5294 0000001   0.0000 127.0588 14.80000000    01",
    ),
    TleSatellite(
        sid=4,
        name="Kuiper-630 4",
        tle_line1="1 00218U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    04",
        tle_line2="2 00218  51.9000  63.5294 0000001   0.0000 137.6471 14.80000000    00",
    ),
    TleSatellite(
        sid=5,
        name="Kuiper-630 5",
        tle_line1="1 00219U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    05",
        tle_line2="2 00219  51.9000  63.5294 0000001   0.0000 148.2353 14.80000000    08",
    ),
    TleSatellite(
        sid=6,
        name="Kuiper-630 6",
        tle_line1="1 00250U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    00",
        tle_line2="2 00250  51.9000  74.1176 0000001   0.0000 121.7647 14.80000000    02",
    ),
    TleSatellite(
        sid=7,
        name="Kuiper-630 7",
        tle_line1="1 00251U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    01",
        tle_line2="2 00251  51.9000  74.1176 0000001   0.0000 132.3529 14.80000000    00",
    ),
    TleSatellite(
        sid=8,
        name="Kuiper-630 8",
        tle_line1="1 00616U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    06",
        tle_line2="2 00616  51.9000 190.5882 0000001   0.0000  31.7647 14.80000000    05",
    ),
    TleSatellite(
        sid=9,
        name="Kuiper-630 9",
        tle_line1="1 00617U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    07",
        tle_line2="2 00617  51.9000 190.5882 0000001   0.0000  42.3529 14.80000000    03",
    ),
    TleSatellite(
        sid=10,
        name="Kuiper-630 10",
        tle_line1="1 00648U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    01",
        tle_line2="2 00648  51.9000 201.1765 0000001   0.0000  15.8824 14.80000000    09",
    ),
    TleSatellite(
        sid=11,
        name="Kuiper-630 11",
        tle_line1="1 00649U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    02",
        tle_line2="2 00649  51.9000 201.1765 0000001   0.0000  26.4706 14.80000000    07",
    ),
    TleSatellite(
        sid=12,
        name="Kuiper-630 12",
        tle_line1="1 00650U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    04",
        tle_line2="2 00650  51.9000 201.1765 0000001   0.0000  37.0588 14.80000000    05",
    ),
    TleSatellite(
        sid=13,
        name="Kuiper-630 13",
        tle_line1="1 00651U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    05",
        tle_line2="2 00651  51.9000 201.1765 0000001   0.0000  47.6471 14.80000000    04",
    ),
    TleSatellite(
        sid=14,
        name="Kuiper-630 14",
        tle_line1="1 00683U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    00",
        tle_line2="2 00683  51.9000 211.7647 0000001   0.0000  21.1765 14.80000000    08",
    ),
    TleSatellite(
        sid=15,
        name="Kuiper-630 15",
        tle_line1="1 00684U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    01",
        tle_line2="2 00684  51.9000 211.7647 0000001   0.0000  31.7647 14.80000000    05",
    ),
    TleSatellite(
        sid=16,
        name="Kuiper-630 16",
        tle_line1="1 00685U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    02",
        tle_line2="2 00685  51.9000 211.7647 0000001   0.0000  42.3529 14.80000000    03",
    ),
]


def build_request(
    algorithm: DynamicStateAlgorithm,
    output_root: str = "generated",
) -> NetworkStateJobCreateRequest:
    return NetworkStateJobCreateRequest(
        name=f"reduced_kuiper_630_{algorithm.value}",
        output_root=output_root,
        ground_stations=GROUND_STATIONS,
        description=DescriptionConfig(
            max_gsl_length_m=MAX_GSL_LENGTH_M,
            max_isl_length_m=MAX_ISL_LENGTH_M,
        ),
        dynamic_state=DynamicStateConfig(
            algorithm=algorithm,
            time_step_ms=TIME_STEP_MS,
            duration_s=DURATION_S,
            num_threads=NUM_THREADS,
            print_logs=False,
        ),
        isl_config=IslConfig(
            selection=IslSelection.PLUS_GRID,
            isl_shift=0,
            idx_offset=0,
            limited_satellite_set=LIMITED_SATELLITE_SET,
            limited_satellite_idx_map=LIMITED_SATELLITE_IDX_MAP,
            num_orbits=NUM_ORBS,
            num_sats_per_orbit=NUM_SATS_PER_ORB,
        ),
        satellites=SATELLITES,
    )


def build_step_1_requests(output_root: str = "generated") -> List[NetworkStateJobCreateRequest]:
    return [
        build_request(DynamicStateAlgorithm.FREE_ONE_ONLY_OVER_ISLS, output_root=output_root),
        build_request(DynamicStateAlgorithm.FREE_GS_ONE_SAT_MANY_ONLY_OVER_ISLS, output_root=output_root),
    ]
