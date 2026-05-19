from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from backend.domain.enums import DynamicStateAlgorithm, IslSelection, JobStatus


class GroundStation(BaseModel):
    gid: int = Field(..., description="Ground-station identifier used in generated files.")
    name: str = Field(..., min_length=1)
    latitude_deg: float
    longitude_deg: float
    elevation_m: float = 0.0


class TleSatellite(BaseModel):
    sid: int = Field(..., description="Satellite identifier used in generated files.")
    name: str = Field(..., min_length=1)
    tle_line1: str = Field(..., min_length=1)
    tle_line2: str = Field(..., min_length=1)


class ManualConstellationConfig(BaseModel):
    name: str = Field(..., min_length=1)
    num_orbits: int = Field(..., gt=0)
    num_sats_per_orbit: int = Field(..., gt=0)
    phase_diff: bool
    inclination_degree: float
    eccentricity: float = Field(..., ge=0)
    arg_of_perigee_degree: float
    mean_motion_rev_per_day: float = Field(..., gt=0)


class IslConfig(BaseModel):
    selection: IslSelection = IslSelection.PLUS_GRID
    isl_shift: int = 0
    idx_offset: int = 0
    limited_satellite_set: Optional[List[int]] = None
    limited_satellite_idx_map: Optional[Dict[int, int]] = None
    num_orbits: Optional[int] = Field(default=None, gt=0)
    num_sats_per_orbit: Optional[int] = Field(default=None, gt=0)


class DynamicStateConfig(BaseModel):
    algorithm: DynamicStateAlgorithm
    time_step_ms: int = Field(..., gt=0)
    duration_s: int = Field(..., gt=0)
    num_threads: int = Field(default=1, gt=0)
    start_time_s: int = Field(default=0, ge=0)
    print_logs: bool = False


class DynamicStateDefaultsConfig(BaseModel):
    time_step_ms: int = Field(..., gt=0)
    duration_s: int = Field(..., gt=0)
    num_threads: int = Field(default=1, gt=0)
    start_time_s: int = Field(default=0, ge=0)
    print_logs: bool = False


class DescriptionConfig(BaseModel):
    max_gsl_length_m: float = Field(..., gt=0)
    max_isl_length_m: float = Field(..., gt=0)


class NetworkStateScenarioConfig(BaseModel):
    base_name: str = Field(..., min_length=1, description="Base name for generated request directories.")
    output_root: str = Field(default="generated", min_length=1, description="Root folder relative to the repo.")
    name_template: str = Field(
        default="{base_name}_{algorithm}",
        min_length=1,
        description="Template used to generate request names.",
    )
    ground_stations: List[GroundStation] = Field(..., min_length=1)
    description: DescriptionConfig
    dynamic_state_defaults: DynamicStateDefaultsConfig
    dynamic_state_algorithms: List[DynamicStateAlgorithm] = Field(..., min_length=1)
    isl_config: IslConfig = Field(default_factory=IslConfig)
    satellites: Optional[List[TleSatellite]] = None
    manual_constellation: Optional[ManualConstellationConfig] = None

    @model_validator(mode="after")
    def validate_scenario(self) -> "NetworkStateScenarioConfig":
        _validate_constellation_source(self.satellites, self.manual_constellation)
        _validate_name_template(self.name_template, self.base_name, self.dynamic_state_algorithms[0])
        _validate_isl_metadata(self.isl_config, self.manual_constellation)
        return self


class NetworkStateJobCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, description="Name of the generated network-state directory.")
    output_root: str = Field(default="generated", min_length=1, description="Root folder relative to the repo.")
    ground_stations: List[GroundStation] = Field(..., min_length=1)
    description: DescriptionConfig
    dynamic_state: DynamicStateConfig
    isl_config: IslConfig = Field(default_factory=IslConfig)
    satellites: Optional[List[TleSatellite]] = None
    manual_constellation: Optional[ManualConstellationConfig] = None

    @model_validator(mode="after")
    def validate_request(self) -> "NetworkStateJobCreateRequest":
        _validate_constellation_source(self.satellites, self.manual_constellation)
        _validate_isl_metadata(self.isl_config, self.manual_constellation)
        return self


def _validate_constellation_source(
    satellites: Optional[List[TleSatellite]],
    manual_constellation: Optional[ManualConstellationConfig],
) -> None:
    has_satellites = bool(satellites)
    has_manual_constellation = manual_constellation is not None
    if has_satellites == has_manual_constellation:
        raise ValueError("Provide exactly one of 'satellites' or 'manual_constellation'")


def _validate_name_template(
    name_template: str,
    base_name: str,
    algorithm: DynamicStateAlgorithm,
) -> None:
    try:
        name_template.format(base_name=base_name, algorithm=algorithm.value)
    except KeyError as exc:
        raise ValueError(
            "name_template may only reference 'base_name' and 'algorithm'"
        ) from exc


def _validate_isl_metadata(
    isl_config: IslConfig,
    manual_constellation: Optional[ManualConstellationConfig],
) -> None:
    if isl_config.selection != IslSelection.PLUS_GRID:
        return
    if manual_constellation is not None:
        return
    if isl_config.num_orbits is None or isl_config.num_sats_per_orbit is None:
        raise ValueError(
            "PLUS_GRID ISL generation requires 'num_orbits' and "
            "'num_sats_per_orbit' when using inline satellites"
        )


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
