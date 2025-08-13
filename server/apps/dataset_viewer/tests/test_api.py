from django.test import TestCase
from rest_framework.test import APIClient
from dataset_viewer.models import Dataset


class DatasetAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_datasets_list_empty(self):
        resp = self.client.get("/api/datasets/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_scan_invalid_dir(self):
        resp = self.client.post(
            "/api/datasets/scan/",
            {"name": "ds", "root_dir": "/no/such/dir"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_dataset_items_empty(self):
        ds = Dataset.objects.create(name="ds1", root_dir="/tmp")
        resp = self.client.get(f"/api/datasets/{ds.id}/items/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"count": 0, "page": 1, "page_size": 50, "results": []})
