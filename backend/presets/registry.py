from typing import Callable, List

from backend.domain.models import NetworkStateJobCreateRequest
from backend.presets.manila_dalian_over_kuiper import build_step_1_requests


PresetBuilder = Callable[..., List[NetworkStateJobCreateRequest]]

_PRESET_BUILDERS = {
    "manila_dalian_over_kuiper": build_step_1_requests,
}


def list_presets() -> List[str]:
    return sorted(_PRESET_BUILDERS.keys())


def get_preset_builder(name: str) -> PresetBuilder:
    if name not in _PRESET_BUILDERS:
        raise KeyError("Unknown preset: %s" % name)
    return _PRESET_BUILDERS[name]
