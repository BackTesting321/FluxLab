from django.test import TestCase
from rest_framework.test import APIClient
from dataset_viewer.models import Dataset, DatasetItem


class DatasetAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_datasets_list_empty(self):
        resp = self.client.get("/api/datasets/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_scan_invalid_dir(self):
        resp = self.client.post(
            "/api/datasets/scan",
            {"name": "ds", "root_dir": "/no/such/dir"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_dataset_items_empty(self):
        ds = Dataset.objects.create(name="ds1", root_dir="/tmp")
        resp = self.client.get(f"/api/datasets/{ds.id}/items")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.json(),
            {"count": 0, "next": None, "previous": None, "results": []},
        )

    def test_item_detail_and_delete(self):
        ds = Dataset.objects.create(name="ds1", root_dir="/tmp")
        item = DatasetItem.objects.create(
            dataset=ds,
            image_path="images/1.jpg",
            width=10,
            height=20,
            sha256="abcd",
        )

        # Detail
        resp = self.client.get(f"/api/datasets/{ds.id}/items/{item.id}/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["id"], item.id)
        self.assertEqual(data["image_path"], "images/1.jpg")
        self.assertIn("image_url", data)

        # Wrong dataset -> 404
        resp404 = self.client.get(f"/api/datasets/{ds.id + 1}/items/{item.id}/")
        self.assertEqual(resp404.status_code, 404)

        # Delete
        resp_del = self.client.delete(f"/api/datasets/{ds.id}/items/{item.id}/")
        self.assertIn(resp_del.status_code, (200, 204))
        self.assertEqual(DatasetItem.objects.count(), 0)
