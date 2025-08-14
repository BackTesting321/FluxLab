import uuid
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import PreviewRequestSerializer


@api_view(["POST"])
def preview(request):
    serializer = PreviewRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    ops = data.get("ops") or []
    if data.get("auto_policy"):
        ops = [
            {"type": "denoise", "level": "light"},
            {"type": "upscale", "scale": 2},
        ]

    input_size = [1024, 1024]
    output_size = [2048, 2048] if any(op.get("type") == "upscale" for op in ops) else input_size
    preview_path = f"storage/runs/previews/{uuid.uuid4()}.jpg"

    preview_data = {
        "input": {"image_path": data["image_path"], "size": input_size},
        "ops": ops,
        "time": 1.23,
        "output": {"image_path": preview_path, "size": output_size},
    }

    return Response({"ok": True, "preview": preview_data})
