from __future__ import annotations

from rest_framework import serializers

from .utils import AutoPolicy, SUPPORTED_STEPS, validate_pipeline


class EnhanceStepConfigSerializer(serializers.Serializer):
    """Configuration of a single enhancement step."""

    type = serializers.ChoiceField(choices=SUPPORTED_STEPS)
    params = serializers.DictField(required=False, default=dict)


class EnhancePipelineConfigSerializer(serializers.ListSerializer):
    child = EnhanceStepConfigSerializer()


class EnhancePreviewRequestSerializer(serializers.Serializer):
    dataset_id = serializers.IntegerField(required=False)
    image_path = serializers.CharField(required=False)
    pipeline = EnhanceStepConfigSerializer(many=True, required=False)
    auto_policy = serializers.ChoiceField(
        choices=[p.value for p in AutoPolicy], default=AutoPolicy.OFF.value
    )
    return_mode = serializers.ChoiceField(
        choices=["metadata", "image"],
        default="metadata",
        source="return",
    )

    def validate(self, attrs):
        if not attrs.get("dataset_id") and not attrs.get("image_path"):
            raise serializers.ValidationError("dataset_id or image_path must be provided")

        pipeline = attrs.get("pipeline")
        policy = attrs.get("auto_policy")

        if policy == AutoPolicy.OFF.value and not pipeline:
            raise serializers.ValidationError(
                "pipeline must be provided when auto_policy is OFF"
            )

        if pipeline:
            # Validates steps and params
            try:
                validate_pipeline(pipeline)
            except ValueError as exc:  # pragma: no cover - defensive
                raise serializers.ValidationError({"pipeline": str(exc)})

        return attrs
