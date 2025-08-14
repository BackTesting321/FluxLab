"""Utility helpers for image enhancement simulation.

This module contains only lightweight mock implementations which allow the
API layer to operate without any heavy dependencies.  The mapping between
auto‑policies and pipelines is intentionally simple:

* **BASIC** – denoise(light) → face_restore(light) → upscale(x1.5)
* **AGGRESSIVE** – denoise(strong) → face_restore(strong) → upscale(x2)

The functions below do **not** perform any real image processing.  They only
validate the configuration and provide deterministic estimations that are
used by tests and the API responses.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List


class StepType(str, Enum):
    """Supported enhancement steps."""

    UPSCALE = "upscale"
    FACE_RESTORE = "face_restore"
    DENOISE = "denoise"


class AutoPolicy(str, Enum):
    """Automatic pipeline selection policy."""

    OFF = "OFF"
    BASIC = "BASIC"
    AGGRESSIVE = "AGGRESSIVE"


# Exposed constant for serializers/tests
SUPPORTED_STEPS = [s.value for s in StepType]


@dataclass
class StepSimulation:
    name: str
    params: Dict[str, object]
    delta_quality: float
    est_time_ms: int


def build_auto_policy_pipeline(policy: AutoPolicy, quality_score: float) -> List[Dict]:
    """Return a pipeline for the given auto policy.

    ``quality_score`` is currently unused but kept for future extensions where
    the policy may depend on the score.
    """

    if policy == AutoPolicy.BASIC:
        return [
            {"type": StepType.DENOISE.value, "params": {"level": "light"}},
            {"type": StepType.FACE_RESTORE.value, "params": {"level": "light"}},
            {"type": StepType.UPSCALE.value, "params": {"scale": 1.5}},
        ]
    if policy == AutoPolicy.AGGRESSIVE:
        return [
            {"type": StepType.DENOISE.value, "params": {"level": "strong"}},
            {"type": StepType.FACE_RESTORE.value, "params": {"level": "strong"}},
            {"type": StepType.UPSCALE.value, "params": {"scale": 2}},
        ]
    return []


def validate_pipeline(pipeline: List[Dict]) -> List[Dict]:
    """Validate pipeline configuration.

    Raises ``ValueError`` if the pipeline contains unknown steps or conflicting
    parameters.  The function returns the pipeline back for convenience.
    """

    for step in pipeline:
        s_type = step.get("type")
        if s_type not in SUPPORTED_STEPS:
            raise ValueError(f"Unknown step: {s_type}")
        params = step.get("params", {})
        if s_type == StepType.UPSCALE.value:
            scale = params.get("scale")
            try:
                scale_val = float(scale)
            except (TypeError, ValueError):
                raise ValueError("Upscale step requires numeric 'scale'")
            if scale_val <= 0:
                raise ValueError("Upscale 'scale' must be > 0")
        elif s_type in (StepType.DENOISE.value, StepType.FACE_RESTORE.value):
            level = params.get("level")
            if level not in ("light", "strong"):
                raise ValueError(
                    f"{s_type} step requires level to be 'light' or 'strong'"
                )
    return pipeline


def simulate_step(step: Dict) -> StepSimulation:
    """Simulate execution of a single step."""

    s_type = step["type"]
    params = step.get("params", {})

    if s_type == StepType.DENOISE.value:
        level = params.get("level", "light")
        delta = 0.02 if level == "light" else 0.05
        est = 100 if level == "light" else 200
        norm = {"level": level}
    elif s_type == StepType.FACE_RESTORE.value:
        level = params.get("level", "light")
        delta = 0.03 if level == "light" else 0.07
        est = 120 if level == "light" else 240
        norm = {"level": level}
    elif s_type == StepType.UPSCALE.value:
        scale = float(params.get("scale", 1.0))
        delta = 0.04 * max(scale - 1.0, 0)
        est = int(150 * scale)
        norm = {"scale": scale}
    else:
        raise ValueError(f"Unknown step: {s_type}")

    return StepSimulation(name=s_type, params=norm, delta_quality=delta, est_time_ms=est)


def estimate_quality(image_path: str) -> float:
    """Return mocked quality score for the input image (0..1)."""

    # Deterministic pseudo score based on path hash for reproducibility in tests
    return (hash(image_path) % 100) / 100.0
