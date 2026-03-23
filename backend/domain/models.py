from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from backend.domain.enums import DynamicStateAlgorithm, IslSelection, JobStatus


class GroundStation(BaseModel):
    gid: int = Field(..., description="Ground-station identifier used in generated files.")
    name: str
    latitude_deg: float
    longitude_deg: float
    elevation_m: float = 0.0


class TleSatellite(BaseModel):
    sid: int = Field(..., description="Satellite identifier used in generated files.")
    name: str
    tle_line1: str
    tle_line2: str


class ManualConstellationConfig(BaseModel):
    name: str
    num_orbits: int
    num_sats_per_orbit: int
    phase_diff: bool
    inclination_degree: float
    eccentricity: float
    arg_of_perigee_degree: float
    mean_motion_rev_per_day: float


class IslConfig(BaseModel):
    selection: IslSelection = IslSelection.PLUS_GRID
    isl_shift: int = 0
    idx_offset: int = 0
    limited_satellite_set: Optional[List[int]] = None
    limited_satellite_idx_map: Optional[Dict[int, int]] = None
    num_orbits: Optional[int] = None
    num_sats_per_orbit: Optional[int] = None


class DynamicStateConfig(BaseModel):
    algorithm: DynamicStateAlgorithm
    time_step_ms: int
    duration_s: int
    num_threads: int = 1
    start_time_s: int = 0
    print_logs: bool = False


class DescriptionConfig(BaseModel):
    max_gsl_length_m: float
    max_isl_length_m: float


class NetworkStateJobCreateRequest(BaseModel):
    name: str = Field(..., description="Name of the generated network-state directory.")
    output_root: str = Field(default="generated", description="Root folder relative to the repo.")
    ground_stations: List[GroundStation]
    description: DescriptionConfig
    dynamic_state: DynamicStateConfig
    isl_config: IslConfig = Field(default_factory=IslConfig)
    satellites: Optional[List[TleSatellite]] = None
    manual_constellation: Optional[ManualConstellationConfig] = None


class ArtifactRecord(BaseModel):
    name: str
    path: str


class NetworkStateJobResult(BaseModel):
    name: str
    output_directory: str
    dynamic_state_directory: str
    artifacts: List[ArtifactRecord]


class JobRecord(BaseModel):
    id: str
    kind: str
    status: JobStatus
    request_payload: Dict[str, Any]
    artifacts: List[ArtifactRecord] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    @classmethod
    def new(cls, kind: str, request_payload: Dict[str, Any]) -> "JobRecord":
        return cls(
            id=f"job_{uuid4().hex[:12]}",
            kind=kind,
            status=JobStatus.QUEUED,
            request_payload=request_payload,
            created_at=datetime.now(timezone.utc),
        )
