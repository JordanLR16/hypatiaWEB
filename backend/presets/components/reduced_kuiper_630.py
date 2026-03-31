from __future__ import annotations

import math
from pathlib import Path
from typing import List, Tuple

from backend.domain.enums import DynamicStateAlgorithm
from backend.domain.models import TleSatellite

# WGS72 value; taken from the original Hypatia integration test setup.
EARTH_RADIUS_M = 6378135.0
ALTITUDE_M = 630000
SATELLITE_CONE_RADIUS_M = ALTITUDE_M / math.tan(math.radians(30.0))
MAX_GSL_LENGTH_M = math.sqrt(SATELLITE_CONE_RADIUS_M ** 2 + ALTITUDE_M ** 2)
MAX_ISL_LENGTH_M = 2 * math.sqrt((EARTH_RADIUS_M + ALTITUDE_M) ** 2 - (EARTH_RADIUS_M + 80000) ** 2)
NUM_ORBS = 34
NUM_SATS_PER_ORB = 34

LIMITED_SATELLITE_SET = [
    183, 184, 215, 216, 217, 218, 249, 250, 615, 616, 647, 648, 649, 650, 682, 683, 684,
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
    TleSatellite(sid=0, name="Kuiper-630 0", tle_line1="1 00184U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    06", tle_line2="2 00184  51.9000  52.9412 0000001   0.0000 142.9412 14.80000000    00"),
    TleSatellite(sid=1, name="Kuiper-630 1", tle_line1="1 00185U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    07", tle_line2="2 00185  51.9000  52.9412 0000001   0.0000 153.5294 14.80000000    07"),
    TleSatellite(sid=2, name="Kuiper-630 2", tle_line1="1 00216U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    02", tle_line2="2 00216  51.9000  63.5294 0000001   0.0000 116.4706 14.80000000    04"),
    TleSatellite(sid=3, name="Kuiper-630 3", tle_line1="1 00217U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    03", tle_line2="2 00217  51.9000  63.5294 0000001   0.0000 127.0588 14.80000000    01"),
    TleSatellite(sid=4, name="Kuiper-630 4", tle_line1="1 00218U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    04", tle_line2="2 00218  51.9000  63.5294 0000001   0.0000 137.6471 14.80000000    00"),
    TleSatellite(sid=5, name="Kuiper-630 5", tle_line1="1 00219U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    05", tle_line2="2 00219  51.9000  63.5294 0000001   0.0000 148.2353 14.80000000    08"),
    TleSatellite(sid=6, name="Kuiper-630 6", tle_line1="1 00250U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    00", tle_line2="2 00250  51.9000  74.1176 0000001   0.0000 121.7647 14.80000000    02"),
    TleSatellite(sid=7, name="Kuiper-630 7", tle_line1="1 00251U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    01", tle_line2="2 00251  51.9000  74.1176 0000001   0.0000 132.3529 14.80000000    00"),
    TleSatellite(sid=8, name="Kuiper-630 8", tle_line1="1 00616U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    06", tle_line2="2 00616  51.9000 190.5882 0000001   0.0000  31.7647 14.80000000    05"),
    TleSatellite(sid=9, name="Kuiper-630 9", tle_line1="1 00617U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    07", tle_line2="2 00617  51.9000 190.5882 0000001   0.0000  42.3529 14.80000000    03"),
    TleSatellite(sid=10, name="Kuiper-630 10", tle_line1="1 00648U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    01", tle_line2="2 00648  51.9000 201.1765 0000001   0.0000  15.8824 14.80000000    09"),
    TleSatellite(sid=11, name="Kuiper-630 11", tle_line1="1 00649U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    02", tle_line2="2 00649  51.9000 201.1765 0000001   0.0000  26.4706 14.80000000    07"),
    TleSatellite(sid=12, name="Kuiper-630 12", tle_line1="1 00650U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    04", tle_line2="2 00650  51.9000 201.1765 0000001   0.0000  37.0588 14.80000000    05"),
    TleSatellite(sid=13, name="Kuiper-630 13", tle_line1="1 00651U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    05", tle_line2="2 00651  51.9000 201.1765 0000001   0.0000  47.6471 14.80000000    04"),
    TleSatellite(sid=14, name="Kuiper-630 14", tle_line1="1 00683U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    00", tle_line2="2 00683  51.9000 211.7647 0000001   0.0000  21.1765 14.80000000    08"),
    TleSatellite(sid=15, name="Kuiper-630 15", tle_line1="1 00684U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    01", tle_line2="2 00684  51.9000 211.7647 0000001   0.0000  31.7647 14.80000000    05"),
    TleSatellite(sid=16, name="Kuiper-630 16", tle_line1="1 00685U 00000ABC 00001.00000000  .00000000  00000-0  00000+0 0    02", tle_line2="2 00685  51.9000 211.7647 0000001   0.0000  42.3529 14.80000000    03"),
]


def build_reduced_kuiper_630_satellites() -> List[TleSatellite]:
    return list(SATELLITES)


def write_reduced_kuiper_630_tles_file(output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8") as handle:
        handle.write(f"1 {len(SATELLITES)}\n")
        for satellite in SATELLITES:
            handle.write(f"{satellite.name}\n")
            handle.write(f"{satellite.tle_line1}\n")
            handle.write(f"{satellite.tle_line2}\n")


def write_reduced_kuiper_630_filtered_isls_file(satgen_module, output_dir: Path) -> None:
    complete_isls = satgen_module.generate_plus_grid_isls(
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
                handle.write(f"{LIMITED_SATELLITE_IDX_MAP[left]} {LIMITED_SATELLITE_IDX_MAP[right]}\n")


def resolve_reduced_kuiper_630_gsl_interface_config(
    algorithm: DynamicStateAlgorithm,
    ground_station_count: int,
) -> Tuple[int, float]:
    if algorithm == DynamicStateAlgorithm.FREE_ONE_ONLY_OVER_ISLS:
        return 1, 1.0
    if algorithm == DynamicStateAlgorithm.FREE_GS_ONE_SAT_MANY_ONLY_OVER_ISLS:
        return ground_station_count, float(ground_station_count)
    raise ValueError("Unsupported reduced Kuiper-630 algorithm: %s" % algorithm.value)
