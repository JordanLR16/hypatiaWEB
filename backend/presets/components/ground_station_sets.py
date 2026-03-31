from typing import List

from backend.domain.models import GroundStation


MANILA_DALIAN_GROUND_STATIONS = [
    GroundStation(gid=0, name="Manila", latitude_deg=14.6042, longitude_deg=120.9822, elevation_m=0.0),
    GroundStation(gid=1, name="Dalian", latitude_deg=38.913811, longitude_deg=121.602322, elevation_m=0.0),
]


def build_manila_dalian_ground_stations() -> List[GroundStation]:
    return list(MANILA_DALIAN_GROUND_STATIONS)
