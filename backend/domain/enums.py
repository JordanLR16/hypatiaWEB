from enum import Enum


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class IslSelection(str, Enum):
    PLUS_GRID = "isls_plus_grid"
    NONE = "isls_none"


class DynamicStateAlgorithm(str, Enum):
    FREE_ONE_ONLY_GS_RELAYS = "algorithm_free_one_only_gs_relays"
    FREE_ONE_ONLY_OVER_ISLS = "algorithm_free_one_only_over_isls"
    FREE_GS_ONE_SAT_MANY_ONLY_OVER_ISLS = "algorithm_free_gs_one_sat_many_only_over_isls"
    PAIRED_MANY_ONLY_OVER_ISLS = "algorithm_paired_many_only_over_isls"
