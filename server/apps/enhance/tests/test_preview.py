from django.test import TestCase
from rest_framework.test import APIClient


class EnhancePreviewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auto_policy_basic(self):
        resp = self.client.post(
            "/api/enhance/preview",
            {"image_path": "img.jpg", "auto_policy": "BASIC"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["applied_pipeline"]), 3)

    def test_manual_pipeline(self):
        pipeline = [
            {"type": "denoise", "params": {"level": "light"}},
            {"type": "face_restore", "params": {"level": "light"}},
            {"type": "upscale", "params": {"scale": 2}},
        ]
        resp = self.client.post(
            "/api/enhance/preview",
            {"image_path": "img.jpg", "pipeline": pipeline, "auto_policy": "OFF"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["applied_pipeline"]), 3)

    def test_unknown_step(self):
        pipeline = [{"type": "unknown", "params": {}}]
        resp = self.client.post(
            "/api/enhance/preview",
            {"image_path": "img.jpg", "pipeline": pipeline, "auto_policy": "OFF"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_off_without_pipeline(self):
        resp = self.client.post(
            "/api/enhance/preview",
            {"image_path": "img.jpg", "auto_policy": "OFF"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_response_fields(self):
        resp = self.client.post(
            "/api/enhance/preview",
            {"image_path": "img.jpg", "auto_policy": "BASIC"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        for field in [
            "applied_pipeline",
            "estimated_time_ms",
            "logs",
            "quality_before",
            "quality_after",
        ]:
            self.assertIn(field, data)
