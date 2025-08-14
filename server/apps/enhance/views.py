from __future__ import annotations

from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import EnhancePreviewRequestSerializer
from .utils import (
    AutoPolicy,
    build_auto_policy_pipeline,
    estimate_quality,
    simulate_step,
    validate_pipeline,
)


@api_view(["POST"])
def preview(request):
    serializer = EnhancePreviewRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    pipeline = data.get("pipeline")
    policy = data.get("auto_policy")
    image_path = data.get("image_path") or ""

    quality_before = estimate_quality(image_path)

    if not pipeline:
        pipeline = build_auto_policy_pipeline(AutoPolicy(policy), quality_before)
        validate_pipeline(pipeline)

    applied = []
    logs = []
    est_total = 0
    quality_after = quality_before

    for step_cfg in pipeline:
        sim = simulate_step(step_cfg)
        applied.append({"type": sim.name, "params": sim.params})
        est_total += sim.est_time_ms
        quality_after += sim.delta_quality
        logs.append(f"Applied {sim.name} with {sim.params}")

    result = {
        "ok": True,
        "applied_pipeline": applied,
        "estimated_time_ms": est_total,
        "quality_before": round(quality_before, 3),
        "quality_after": round(quality_after, 3),
        "logs": logs,
    }

    return Response(result)
